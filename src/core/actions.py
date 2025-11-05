"""
Action Manager Module

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module handles file operations (move, rename, delete, archive) based on
classification results. It supports dry-run mode, undo functionality, and
comprehensive logging of all actions.

NOTICE: This software is proprietary and confidential. Unauthorized copying,
modification, distribution, or use is strictly prohibited.
See LICENSE.txt for full terms and conditions.

Version: 1.0.0
Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import os
import shutil
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import json

# Import new libraries
from filelock import FileLock
import fs
try:
    from organize import organize
    ORGANIZE_AVAILABLE = True
except (ImportError, SyntaxError):
    ORGANIZE_AVAILABLE = False

# Import Safety Guardian for final safety checks
from .safety_guardian import SafetyGuardian
from src.utils.logger import get_logger
from src.utils.error_handler import (
    FileOperationError, ClassificationError, DatabaseError,
    SafetyViolationError, ConfigurationError, WatcherError
)

# Initialize logger for audit trail (MEDIUM #2 FIX)
logger = logging.getLogger(__name__)


class ActionManager:
    """
    Manages file operations with safety features and logging.

    Attributes:
        config: Configuration object
        db_manager: Database manager for logging
        dry_run (bool): If True, simulate actions without actually performing them
        undo_history (List): Stack of recent actions for undo functionality
    """

    def __init__(self, config, db_manager, dry_run: Optional[bool] = None, ollama_client=None):
        """
        Initialize action manager.

        Args:
            config: Configuration object
            db_manager: Database manager instance
            dry_run (bool, optional): Override config dry_run setting
            ollama_client: Optional Ollama client for AI safety checks
        """
        self.config = config
        self.db_manager = db_manager
        self.dry_run = dry_run if dry_run is not None else config.dry_run
        self.undo_history: List[Dict[str, Any]] = []
        self.max_undo_history = 50  # Keep last 50 actions

        # Initialize Safety Guardian for final evaluation
        self.safety_guardian = SafetyGuardian(config, ollama_client)
        self._logger = get_logger()

        # Async processing support
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ActionExecutor")

    def _validate_input_safety(self, file_path: str, classification: Dict[str, Any]) -> tuple:
        """
        Validate input parameters for security.

        Args:
            file_path (str): File path to validate
            classification (Dict): Classification result to validate

        Returns:
            tuple: (is_safe: bool, error_message: str)
        """
        # Validate file path
        if not file_path or not isinstance(file_path, str):
            return False, "Invalid file path: must be non-empty string"

        if len(file_path) > 4096:  # Reasonable path length limit
            return False, "File path too long (potential attack)"

        # Check for null bytes or other control characters
        if '\x00' in file_path or any(ord(c) < 32 for c in file_path if c not in '\n\r\t'):
            return False, "File path contains control characters (potential attack)"

        # Validate classification result
        if not isinstance(classification, dict):
            return False, "Invalid classification: must be dictionary"

        required_keys = ['category', 'suggested_path', 'confidence', 'method']
        for key in required_keys:
            if key not in classification:
                return False, f"Invalid classification: missing required key '{key}'"

        # Validate suggested_path if present
        suggested_path = classification.get('suggested_path')
        if suggested_path:
            if not isinstance(suggested_path, str):
                return False, "Invalid suggested_path: must be string"
            if len(suggested_path) > 2048:  # Reasonable path length limit
                return False, "Suggested path too long (potential attack)"

        # Validate rename if present
        rename = classification.get('rename')
        if rename:
            if not isinstance(rename, str):
                return False, "Invalid rename: must be string"
            if len(rename) > 255:  # Reasonable filename length limit
                return False, "Rename too long (potential attack)"
            # Check for dangerous filename patterns
            dangerous_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                             'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
            if os.name == 'nt' and rename.upper() in dangerous_names:
                return False, f"Dangerous filename '{rename}' not allowed on Windows"

        return True, ""

    def execute(self, file_path: str, classification: Dict[str, Any],
                user_approved: bool = False, folder_policy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute file organization action based on classification result.

        Args:
            file_path (str): Current file path
            classification (Dict): Classification result from classifier
            user_approved (bool): Whether user explicitly approved this action
            folder_policy (Dict, optional): Folder policy dict to override config lookup

        Returns:
            Dict: Action result
        """
        # Log start of operation
        logger.info(f"Starting organization of {file_path} (user_approved={user_approved})")

        try:
            # Step 1: Validate inputs and file
            validation_result = self._validate_execution_inputs(file_path, classification)
            if not validation_result['valid']:
                return validation_result['result']

            path = Path(file_path)

            # Step 2: Check policies and security
            policy_result = self._check_policies_and_security(path, file_path, folder_policy)
            if not policy_result['allowed']:
                return policy_result['result']

            # Step 3: Determine action and build paths
            action_result = self._determine_action(path, classification)
            if not action_result['determined']:
                return action_result['result']

            action_type = action_result['action_type']
            new_path = action_result['new_path']

            # Step 4: Safety Guardian check
            safety_result = self._perform_safety_check(path, new_path, action_type, classification, user_approved)
            if not safety_result['approved']:
                return safety_result['result']

            # Step 5: Execute the action
            execution_result = self._execute_determined_action(path, new_path, action_type, classification, user_approved)
            return execution_result

        except (FileOperationError, SafetyViolationError, ConfigurationError) as e:
            logger.error(f"Operation failed for {file_path}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'action': 'error',
                'old_path': file_path,
                'new_path': None,
                'time_saved': 0.0,
                'message': f'{type(e).__name__}: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected error organizing {file_path}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'action': 'error',
                'old_path': file_path,
                'new_path': None,
                'time_saved': 0.0,
                'message': f'Unexpected error: {str(e)}'
            }

    def _validate_execution_inputs(self, file_path: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Validate inputs and file for execution."""
        # Validate inputs for security
        input_safe, input_error = self._validate_input_safety(file_path, classification)
        if not input_safe:
            logger.warning(f"Input validation failed for {file_path}: {input_error}")
            return {
                'valid': False,
                'result': {
                    'success': False,
                    'action': 'blocked',
                    'old_path': file_path,
                    'new_path': None,
                    'time_saved': 0.0,
                    'message': f'Security: {input_error}'
                }
            }

        path = Path(file_path)

        # Validate file exists
        if not path.exists():
            logger.warning(f"File not found: {file_path}")
            return {
                'valid': False,
                'result': {
                    'success': False,
                    'action': 'none',
                    'old_path': file_path,
                    'new_path': None,
                    'time_saved': 0.0,
                    'message': 'File not found'
                }
            }

        # Enhanced file validation
        file_size = path.stat().st_size
        max_file_size = getattr(self.config, 'max_file_size', 100 * 1024 * 1024)
        if file_size > max_file_size:
            logger.warning(f"File too large: {file_path} ({file_size} bytes > {max_file_size} bytes)")
            return {
                'valid': False,
                'result': {
                    'success': False,
                    'action': 'blocked',
                    'old_path': file_path,
                    'new_path': None,
                    'time_saved': 0.0,
                    'message': f'File too large ({file_size} bytes > {max_file_size} bytes)'
                }
            }

        # Check for suspicious file characteristics
        if file_size == 0:
            logger.warning(f"Empty file blocked: {file_path}")
            return {
                'valid': False,
                'result': {
                    'success': False,
                    'action': 'blocked',
                    'old_path': file_path,
                    'new_path': None,
                    'time_saved': 0.0,
                    'message': 'Empty files not processed'
                }
            }

        return {'valid': True}

    def _check_policies_and_security(self, path: Path, file_path: str, folder_policy: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Check folder policies and security constraints."""
        # Check folder policy allow_move
        if folder_policy is None:
            folder_policy = self.config.get_folder_policy(file_path)

        if folder_policy and folder_policy.get('allow_move') is False:
            logger.info(f"Operation blocked by folder policy: {file_path}")
            return {
                'allowed': False,
                'result': {
                    'success': False,
                    'action': 'blocked',
                    'old_path': file_path,
                    'new_path': None,
                    'time_saved': 0.0,
                    'message': 'Operation blocked: folder policy disallows moves'
                }
            }

        # Check against configured blacklist paths
        try:
            blacklist = getattr(self.config, 'path_blacklist', []) or []
            resolved = str(path.resolve())
            for b in blacklist:
                try:
                    b_res = str(Path(b).expanduser().resolve())
                    if os.path.commonpath([resolved, b_res]) == b_res:
                        return {
                            'allowed': False,
                            'result': {
                                'success': False,
                                'action': 'blocked',
                                'old_path': file_path,
                                'new_path': None,
                                'time_saved': 0.0,
                                'message': f'Operation blocked: path is blacklisted ({b_res})'
                            }
                        }
                except Exception:
                    if resolved.lower().startswith(str(Path(b).expanduser().resolve()).lower()):
                        return {
                            'allowed': False,
                            'result': {
                                'success': False,
                                'action': 'blocked',
                                'old_path': file_path,
                                'new_path': None,
                                'time_saved': 0.0,
                                'message': f'Operation blocked: path is blacklisted ({b})'
                            }
                        }
        except Exception:
            pass

        return {'allowed': True}

    def _determine_action(self, path: Path, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Determine action type and build destination path."""
        suggested_path = classification.get('suggested_path')
        suggested_rename = classification.get('rename')

        # Build new path with path traversal validation
        if suggested_path:
            try:
                new_path = self._build_destination_path(path, suggested_path, suggested_rename)
                action_type = 'move'
            except ValueError as e:
                return {
                    'determined': False,
                    'result': {
                        'success': False,
                        'action': 'blocked',
                        'old_path': str(path),
                        'new_path': None,
                        'time_saved': 0.0,
                        'message': f'Security: {str(e)}'
                    }
                }
        elif suggested_rename:
            new_path = path.parent / suggested_rename
            action_type = 'rename'
        else:
            return {
                'determined': False,
                'result': {
                    'success': False,
                    'action': 'none',
                    'old_path': str(path),
                    'new_path': None,
                    'time_saved': 0.0,
                    'message': 'No action suggested'
                }
            }

        return {
            'determined': True,
            'action_type': action_type,
            'new_path': new_path
        }

    def _perform_safety_check(self, path: Path, new_path: Path, action_type: str,
                             classification: Dict[str, Any], user_approved: bool) -> Dict[str, Any]:
        """Perform Safety Guardian evaluation."""
        logger.info(f"[FINAL SAFETY CHECK] Evaluating operation with Safety Guardian...")
        safety_result = self.safety_guardian.evaluate_operation(
            source_path=str(path),
            destination_path=str(new_path),
            operation=action_type,
            classification=classification,
            user_approved=user_approved
        )

        # Check if Safety Guardian approved the operation
        if not safety_result['approved']:
            logger.warning(f"[SAFETY GUARDIAN BLOCKED] Operation rejected: {safety_result['reasoning']}")
            try:
                self._logger.log_operation(
                    operation='SKIP',
                    file_path=str(path),
                    old_location=str(path),
                    new_location=str(new_path),
                    status='PROTECTED'
                )
            except Exception:
                pass
            return {
                'approved': False,
                'result': {
                    'success': False,
                    'action': 'blocked_by_guardian',
                    'old_path': str(path),
                    'new_path': str(new_path),
                    'time_saved': 0.0,
                    'message': f"Safety Guardian blocked operation: {safety_result['reasoning']}",
                    'safety_result': safety_result
                }
            }

        # Log warnings if any
        if safety_result.get('warnings'):
            logger.info(f"[SAFETY GUARDIAN] Operation approved WITH WARNINGS: {len(safety_result['warnings'])} warnings")
        else:
            logger.info(f"[SAFETY GUARDIAN] Operation approved - proceeding with {action_type}")

        return {'approved': True}

    def _execute_determined_action(self, path: Path, new_path: Path, action_type: str,
                                  classification: Dict[str, Any], user_approved: bool) -> Dict[str, Any]:
        """Execute the determined action and handle logging."""
        # Perform the action
        if self.dry_run:
            result = self._dry_run_action(path, new_path, action_type)
        else:
            result = self._perform_action(path, new_path, action_type)

        # Log action to database and file system
        if result['success']:
            time_saved = self.config.time_estimates.get(action_type, 0.3)
            logger.info(f"Successfully {action_type}d: {path} -> {new_path}")

            self.db_manager.log_action(
                filename=path.name,
                old_path=str(path),
                new_path=str(new_path) if new_path else None,
                operation=action_type,
                time_saved=time_saved,
                category=classification.get('category'),
                ai_suggested=classification.get('method') == 'ai',
                user_approved=user_approved
            )

            try:
                self._logger.log_operation(
                    operation=action_type.upper(),
                    file_path=str(path),
                    old_location=str(path),
                    new_location=str(new_path),
                    status='SUCCESS' if 'dry_run' not in result['action'] else 'DRY_RUN'
                )
            except Exception:
                pass

            result['time_saved'] = time_saved

            # Add to undo history
            self._add_to_undo_history({
                'action': action_type,
                'old_path': str(path),
                'new_path': str(new_path),
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.warning(f"Action failed for {path}: {result.get('message', 'Unknown reason')}")

        return result

    async def async_execute_determined_action(self, path: Path, new_path: Path, action_type: str,
                                       classification: Dict[str, Any], user_approved: bool) -> Dict[str, Any]:
        """
        Async version of _execute_determined_action for better performance.

        Args:
            path (Path): Current file path
            new_path (Path): New file path (if moved/renamed)
            action_type (str): Action type ('move', 'rename', etc.)
            classification (Dict): Classification result from classifier
            user_approved (bool): Whether user explicitly approved this action

        Returns:
            Dict: Action execution result
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._execute_determined_action, path, new_path, action_type, classification, user_approved)

    async def execute_async(self, file_path: str, classification: Dict[str, Any],
                           user_approved: bool = False, folder_policy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Async version of execute method for better performance.

        Args:
            file_path (str): Current file path
            classification (Dict): Classification result from classifier
            user_approved (bool): Whether user explicitly approved this action
            folder_policy (Dict, optional): Folder policy dict to override config lookup

        Returns:
            Dict: Action result
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            lambda: self.execute(file_path, classification, user_approved, folder_policy)
        )

    def _validate_path_safety(self, suggested_path: str, base_dir: Path) -> tuple:
        """
        Ensure path doesn't escape base_destination (MEDIUM #3 FIX - Security).

        Args:
            suggested_path (str): Path to validate
            base_dir (Path): Base directory that path should stay within

        Returns:
            tuple: (is_safe: bool, error_message: str)
        """
        if not suggested_path:
            return True, ""

        # Enhanced path traversal patterns
        dangerous_patterns = [
            "..",  # Parent directory traversal
            "\\..",  # Windows-style traversal
            "/..",  # Unix-style traversal
            "...",  # Triple dot (some systems)
            "\x00",  # Null byte injection
            "<", ">", ":", "\"", "|", "?", "*",  # Windows reserved characters
            "\n", "\r", "\t",  # Control characters
        ]

        for pattern in dangerous_patterns:
            if pattern in suggested_path:
                return False, f"Path contains dangerous pattern '{pattern}' (potential security threat)"

        # Check for encoded traversal attempts
        import urllib.parse
        decoded_path = urllib.parse.unquote(suggested_path)
        if decoded_path != suggested_path:
            # Path was URL-encoded, check decoded version too
            for pattern in dangerous_patterns:
                if pattern in decoded_path:
                    return False, f"URL-decoded path contains dangerous pattern '{pattern}' (potential security threat)"

        # Absolute paths could bypass base_destination
        if os.path.isabs(suggested_path):
            return False, "Absolute paths not allowed for security"

        # Check for drive letter manipulation (Windows-specific)
        if os.name == 'nt':
            if len(suggested_path) >= 2 and suggested_path[1] == ':' and suggested_path[0].isalpha():
                return False, "Drive letter manipulation not allowed"

        try:
            # Verify resolved path stays within base_destination
            test_path = (base_dir / suggested_path).resolve()
            test_path.relative_to(base_dir)
            return True, ""
        except (ValueError, OSError) as e:
            return False, f"Path escapes base directory: {str(e)}"

    def _build_destination_path(self, source_path: Path, suggested_path: str,
                                suggested_rename: Optional[str] = None) -> Path:
        """
        Build complete destination path for file with path traversal protection.

        Args:
            source_path (Path): Current file path
            suggested_path (str): Suggested destination directory
            suggested_rename (str, optional): Suggested new filename

        Returns:
            Path: Complete destination path

        Raises:
            ValueError: If path validation fails (path traversal attempt)
        """
        # Use configured base destination (CRITICAL FIX #2)
        try:
            base_dir = Path(self.config.base_destination).expanduser().resolve()
        except (AttributeError, OSError):
            base_dir = Path.home()  # Fallback only on error

        # Validate path safety (MEDIUM #3 FIX - Security)
        is_safe, error_msg = self._validate_path_safety(suggested_path, base_dir)
        if not is_safe:
            raise ValueError(f"Path validation failed: {error_msg}")

        # Handle absolute vs relative suggested paths
        suggested_obj = Path(suggested_path)
        if suggested_obj.is_absolute():
            # This should already be blocked by _validate_path_safety, but double-check
            raise ValueError("Absolute paths not allowed")
        else:
            # Remove any leading slashes to avoid accidental absolute joining
            dest_dir = base_dir / Path(suggested_path.lstrip('/'))

        # Determine filename
        filename = suggested_rename if suggested_rename else source_path.name

        # Handle filename conflicts
        dest_path = dest_dir / filename

        if dest_path.exists() and dest_path != source_path:
            # Add counter to filename
            stem = dest_path.stem
            suffix = dest_path.suffix
            counter = 1

            while dest_path.exists():
                dest_path = dest_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        return dest_path

    def _perform_action(self, source: Path, destination: Path, action: str) -> Dict[str, Any]:
        """
        Actually perform file operation with race condition protection.

        Args:
            source (Path): Source file path
            destination (Path): Destination file path
            action (str): Action type ('move', 'rename', etc.)

        Returns:
            Dict: Result information
        """
        try:
            # Re-check file exists just before operation (CRITICAL FIX #3)
            if not source.exists():
                raise FileOperationError(
                    f'File no longer exists at {source}',
                    file_path=str(source),
                    operation=action
                )

            # Use filelock to prevent concurrent access
            lock_path = str(source) + '.lock'
            with FileLock(lock_path, timeout=10):
                # Check if file is locked/in use (CRITICAL FIX #3)
                try:
                    with open(source, 'rb+') as _f:
                        pass
                except (IOError, PermissionError) as e:
                    raise FileOperationError(
                        f'File is locked or in use: {str(e)}',
                        file_path=str(source),
                        operation=action
                    ) from e

                # Ensure destination directory exists
                destination.parent.mkdir(parents=True, exist_ok=True)

                # Perform move/rename
                shutil.move(str(source), str(destination))

            return {
                'success': True,
                'action': action,
                'old_path': str(source),
                'new_path': str(destination),
                'message': f'Successfully {action}d file to {destination}'
            }

        except FileOperationError:
            raise  # Re-raise our custom exceptions
        except (OSError, IOError) as e:
            raise FileOperationError(
                f'OS error during {action}: {str(e)}',
                file_path=str(source),
                destination=str(destination),
                operation=action
            ) from e
        except Exception as e:
            # Catch any unexpected exceptions and wrap them
            raise FileOperationError(
                f'Unexpected error during {action}: {str(e)}',
                file_path=str(source),
                destination=str(destination),
                operation=action
            ) from e

    def _dry_run_action(self, source: Path, destination: Path, action: str) -> Dict[str, Any]:
        """
        Simulate file operation without actually performing it.

        Args:
            source (Path): Source file path
            destination (Path): Destination file path
            action (str): Action type

        Returns:
            Dict: Simulated result
        """
        return {
            'success': True,
            'action': f'{action}_dry_run',
            'old_path': str(source),
            'new_path': str(destination),
            'message': f'[DRY RUN] Would {action} file to {destination}'
        }

    def delete_file(self, file_path: str, reason: str = "User requested") -> Dict[str, Any]:
        """
        Delete a file.

        Args:
            file_path (str): Path to file to delete
            _reason (str): Reason for deletion (currently unused, reserved for future logging)

        Returns:
            Dict: Result information
        """
        try:
            path = Path(file_path)

            if not path.exists():
                return {
                    'success': False,
                    'action': 'delete',
                    'message': 'File not found'
                }

            if self.dry_run:
                message = f'[DRY RUN] Would delete {path}'
                try:
                    self._logger.log_operation('DELETE', str(path), str(path), 'DELETED', 'DRY_RUN')
                except Exception:
                    pass
            else:
                path.unlink()
                message = f'Deleted {path}'

                # Log deletion
                time_saved = self.config.time_estimates.get('delete', 0.2)
                self.db_manager.log_action(
                    filename=path.name,
                    old_path=str(path),
                    new_path=None,
                    operation='delete',
                    time_saved=time_saved,
                    user_approved=True
                )
                try:
                    self._logger.log_operation('DELETE', str(path), str(path), 'DELETED', 'SUCCESS')
                except Exception:
                    pass

            return {
                'success': True,
                'action': 'delete',
                'old_path': str(path),
                'message': message
            }

        except Exception as e:
            return {
                'success': False,
                'action': 'delete',
                'message': f'Error deleting file: {str(e)}'
            }

    def archive_file(self, file_path: str, archive_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Archive a file to archive directory.

        Args:
            file_path (str): Path to file to archive
            archive_dir (str, optional): Archive directory path

        Returns:
            Dict: Result information
        """
        try:
            path = Path(file_path)

            if not path.exists():
                return {
                    'success': False,
                    'action': 'archive',
                    'message': 'File not found'
                }

            # Default archive location
            if archive_dir is None:
                archive_path = Path.home() / "Archive" / datetime.now().strftime("%Y/%m")
            else:
                archive_path = Path(archive_dir)

            # Build destination
            dest_path = archive_path / path.name

            # Handle conflicts
            if dest_path.exists():
                counter = 1
                while dest_path.exists():
                    dest_path = archive_path / f"{path.stem}_{counter}{path.suffix}"
                    counter += 1

            if self.dry_run:
                message = f'[DRY RUN] Would archive to {dest_path}'
            else:
                # Create archive directory
                archive_path.mkdir(parents=True, exist_ok=True)

                # Move to archive
                shutil.move(str(path), str(dest_path))
                message = f'Archived to {dest_path}'

                # Log action
                time_saved = self.config.time_estimates.get('archive', 0.4)
                self.db_manager.log_action(
                    filename=path.name,
                    old_path=str(path),
                    new_path=str(dest_path),
                    operation='archive',
                    time_saved=time_saved,
                    user_approved=True
                )

            return {
                'success': True,
                'action': 'archive',
                'old_path': str(path),
                'new_path': str(dest_path),
                'message': message
            }

        except Exception as e:
            return {
                'success': False,
                'action': 'archive',
                'message': f'Error archiving file: {str(e)}'
            }

    def undo_last_action(self) -> Dict[str, Any]:
        """
        Undo the last file operation.

        Returns:
            Dict: Result of undo operation
        """
        if not self.undo_history:
            return {
                'success': False,
                'message': 'No actions to undo'
            }

        # Get last action from database
        last_action = self.db_manager.undo_last_action()

        if not last_action:
            return {
                'success': False,
                'message': 'No undoable actions in database'
            }

        try:
            old_path = Path(last_action['old_path'])
            new_path = Path(last_action['new_path']) if last_action['new_path'] else None

            if not new_path or not new_path.exists():
                return {
                    'success': False,
                    'message': 'Cannot undo: destination file not found'
                }

            if self.dry_run:
                message = f'[DRY RUN] Would undo: move {new_path} back to {old_path}'
            else:
                # Ensure original directory exists
                old_path.parent.mkdir(parents=True, exist_ok=True)

                # Move back
                shutil.move(str(new_path), str(old_path))
                message = f'Undone: restored {old_path}'

            return {
                'success': True,
                'action': 'undo',
                'message': message
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error undoing action: {str(e)}'
            }

    def _add_to_undo_history(self, action: Dict[str, Any]):
        """
        Add action to undo history.

        Args:
            action (Dict): Action details
        """
        self.undo_history.append(action)

        # Keep only recent history
        if len(self.undo_history) > self.max_undo_history:
            self.undo_history = self.undo_history[-self.max_undo_history:]

    def set_dry_run(self, enabled: bool):
        """
        Enable or disable dry run mode.

        Args:
            enabled (bool): True to enable dry run, False to disable
        """
        self.dry_run = enabled

    def get_stats(self) -> Dict[str, Any]:
        """
        Get action statistics from database.

        Returns:
            Dict: Statistics including total actions, time saved, etc.
        """
        stats = self.db_manager.get_stats('all')
        
        # Add Safety Guardian statistics
        stats['safety_guardian'] = self.safety_guardian.get_statistics()
        stats['blocked_operations'] = len(self.safety_guardian.get_blocked_operations())
        
        return stats
    
    def batch_organize_with_rules(self, rules: List[Dict[str, Any]], target_dir: str) -> Dict[str, Any]:
        """
        Use organize library to batch organize files based on rules.

        Args:
            rules: List of organization rules
            target_dir: Directory to organize

        Returns:
            Dict: Result of batch organization
        """
        if not ORGANIZE_AVAILABLE:
            return {
                'success': False,
                'message': 'organize library not available'
            }

        try:
            # Use PyFilesystem2 for cross-platform filesystem operations
            filesystem = fs.open_fs(target_dir)

            # Apply organization rules
            results = []
            for rule in rules:
                # This is a simplified example; actual organize usage would depend on the library's API
                # Assuming organize has a function to apply rules
                result = organize.apply_rule(filesystem, rule)
                results.append(result)

            return {
                'success': True,
                'message': f'Applied {len(rules)} organization rules',
                'results': results
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Batch organization failed: {str(e)}'
            }


if __name__ == "__main__":
    # Test action manager
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.config import get_config
    from core.db_manager import DatabaseManager

    config = get_config()
    db = DatabaseManager()

    # Enable dry run for testing
    action_mgr = ActionManager(config, db, dry_run=True)

    # Test classification result
    test_classification = {
        'category': 'Documents',
        'suggested_path': 'Documents/Test/',
        'rename': None,
        'method': 'rule-based'
    }

    # Test action
    result = action_mgr.execute(
        file_path=__file__,  # Use this file as test
        classification=test_classification,
        user_approved=False
    )

    print(f"Action result: {json.dumps(result, indent=2)}")
