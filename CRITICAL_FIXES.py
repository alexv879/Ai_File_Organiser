"""
CRITICAL FIXES - Apply These Immediately

This file contains ready-to-apply fixes for the 5 CRITICAL issues found.
Copy the code sections into their respective files.

Author: Code Analysis System
Date: October 31, 2025
"""

# ==============================================================================
# FIX #1: RESTORE Policy Enforcement in ActionManager
# File: src/core/actions.py
# Replace execute() method (lines 46-141)
# ==============================================================================

ACTIONS_PY_EXECUTE_METHOD = '''
    def execute(self, file_path: str, classification: Dict[str, Any],
                user_approved: bool = False, folder_policy: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute file organization action based on classification result.

        Args:
            file_path (str): Current file path
            classification (Dict): Classification result from classifier
            user_approved (bool): Whether user explicitly approved this action
            folder_policy (Dict, optional): Folder policy dict to override config lookup

        Returns:
            Dict: Action result with keys:
                - success (bool): Whether action succeeded
                - action (str): Action type performed
                - old_path (str): Original file path
                - new_path (str): New file path (if moved/renamed)
                - time_saved (float): Estimated time saved in minutes
                - message (str): Human-readable result message
        """
        try:
            path = Path(file_path)

            # Validate file exists
            if not path.exists():
                return {
                    'success': False,
                    'action': 'none',
                    'old_path': file_path,
                    'new_path': None,
                    'time_saved': 0.0,
                    'message': 'File not found'
                }

            # Check folder policy allow_move (RESTORED)
            if folder_policy is None:
                folder_policy = self.config.get_folder_policy(file_path)

            if folder_policy and folder_policy.get('allow_move') is False:
                return {
                    'success': False,
                    'action': 'blocked',
                    'old_path': file_path,
                    'new_path': None,
                    'time_saved': 0.0,
                    'message': 'Operation blocked: folder policy disallows moves'
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
                                'success': False,
                                'action': 'blocked',
                                'old_path': file_path,
                                'new_path': None,
                                'time_saved': 0.0,
                                'message': f'Operation blocked: path is blacklisted ({b_res})'
                            }
                    except Exception:
                        if resolved.lower().startswith(str(Path(b).expanduser().resolve()).lower()):
                            return {
                                'success': False,
                                'action': 'blocked',
                                'old_path': file_path,
                                'new_path': None,
                                'time_saved': 0.0,
                                'message': f'Operation blocked: path is blacklisted ({b})'
                            }
            except Exception:
                pass

            # Determine action based on classification
            suggested_path = classification.get('suggested_path')
            suggested_rename = classification.get('rename')

            # Build new path
            if suggested_path:
                new_path = self._build_destination_path(path, suggested_path, suggested_rename)
                action_type = 'move'
            elif suggested_rename:
                new_path = path.parent / suggested_rename
                action_type = 'rename'
            else:
                return {
                    'success': False,
                    'action': 'none',
                    'old_path': file_path,
                    'new_path': None,
                    'time_saved': 0.0,
                    'message': 'No action suggested'
                }

            # Perform the action
            if self.dry_run:
                result = self._dry_run_action(path, new_path, action_type)
            else:
                result = self._perform_action(path, new_path, action_type)

            # Log action to database
            if result['success']:
                time_saved = self.config.time_estimates.get(action_type, 0.3)

                self.db_manager.log_action(
                    filename=path.name,
                    old_path=str(path),
                    new_path=str(new_path) if new_path else None,
                    operation=action_type,
                    time_saved=time_saved,
                    category=classification.get('category'),
                    ai_suggested=classification.get('method') in ['ai', 'agent'],
                    user_approved=user_approved
                )

                result['time_saved'] = time_saved

                # Add to undo history
                self._add_to_undo_history({
                    'action': action_type,
                    'old_path': str(path),
                    'new_path': str(new_path),
                    'timestamp': datetime.now().isoformat()
                })

            return result

        except Exception as e:
            return {
                'success': False,
                'action': 'error',
                'old_path': file_path,
                'new_path': None,
                'time_saved': 0.0,
                'message': f'Error: {str(e)}'
            }
'''

# ==============================================================================
# FIX #2: Use config.base_destination in ActionManager
# File: src/core/actions.py
# Replace _build_destination_path() method (lines 143-178)
# ==============================================================================

ACTIONS_PY_BUILD_DESTINATION_METHOD = '''
    def _build_destination_path(self, source_path: Path, suggested_path: str,
                                suggested_rename: Optional[str] = None) -> Path:
        """
        Build complete destination path for file.

        Args:
            source_path (Path): Current file path
            suggested_path (str): Suggested destination directory
            suggested_rename (str, optional): Suggested new filename

        Returns:
            Path: Complete destination path
        """
        # Use configured base destination (FIXED)
        try:
            base_dir = Path(self.config.base_destination).expanduser().resolve()
        except (AttributeError, OSError):
            base_dir = Path.home()  # Fallback only on error

        # Handle absolute vs relative suggested paths
        suggested_obj = Path(suggested_path)
        if suggested_obj.is_absolute():
            dest_dir = suggested_obj
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
'''

# ==============================================================================
# FIX #3: Add Race Condition Protection
# File: src/core/actions.py
# Replace _perform_action() method (lines 180-214)
# ==============================================================================

ACTIONS_PY_PERFORM_ACTION_METHOD = '''
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
            # Re-check file exists just before operation (ADDED)
            if not source.exists():
                return {
                    'success': False,
                    'action': action,
                    'old_path': str(source),
                    'new_path': str(destination),
                    'message': f'File no longer exists at {source}'
                }

            # Check if file is locked/in use (ADDED)
            try:
                with open(source, 'rb+') as f:
                    pass
            except (IOError, PermissionError) as e:
                return {
                    'success': False,
                    'action': action,
                    'old_path': str(source),
                    'new_path': str(destination),
                    'message': f'File is locked or in use: {str(e)}'
                }

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

        except Exception as e:
            return {
                'success': False,
                'action': action,
                'old_path': str(source),
                'new_path': str(destination),
                'message': f'Failed to {action} file: {str(e)}'
            }
'''

# ==============================================================================
# FIX #4: Add Source Blacklist Check in Agent
# File: src/agent/agent_analyzer.py
# Add this method at line ~360, then call it from _apply_safety_checks at line ~363
# ==============================================================================

AGENT_ANALYZER_SOURCE_BLACKLIST_CHECK = '''
    def _check_source_blacklist(self, file_path: str) -> tuple[bool, str]:
        """
        Check if source file is in blacklist.

        Args:
            file_path: Path to check

        Returns:
            Tuple of (is_blacklisted, reason)
        """
        try:
            source_resolved = str(Path(file_path).resolve())
            blacklist = getattr(self.config, 'path_blacklist', []) or []

            for blacklisted in blacklist:
                try:
                    blacklisted_resolved = str(Path(blacklisted).expanduser().resolve())
                    if os.path.commonpath([source_resolved, blacklisted_resolved]) == blacklisted_resolved:
                        return True, f'source file is blacklisted: {blacklisted}'
                except (ValueError, OSError):
                    # Different drives on Windows - check prefix
                    if source_resolved.lower().startswith(blacklisted_resolved.lower()):
                        return True, f'source file is blacklisted: {blacklisted}'
        except Exception:
            pass

        return False, ''

    def _apply_safety_checks(self, plan: Dict[str, Any], file_path: str,
                            policy: dict = None) -> Dict[str, Any]:
        """
        Apply safety checks to the agent plan.

        Validates:
        1. Source file not in blacklist (NEW)
        2. Suggested paths are not in blacklist
        3. Folder policy allow_move is respected
        4. Paths don't target system/program directories
        """
        # Check if SOURCE file is in blacklist (NEW - ADD THIS FIRST)
        is_blacklisted, reason = self._check_source_blacklist(file_path)
        if is_blacklisted:
            plan['action'] = 'none'
            plan['block_reason'] = reason
            return plan

        # Check folder policy allow_move
        if policy and policy.get('allow_move') is False:
            plan['action'] = 'none'
            plan['block_reason'] = 'folder policy disallows moves'
            return plan

        # ... rest of existing destination checks ...
'''

# ==============================================================================
# FIX #5: Add Timeout Handling in Ollama Calls
# File: src/agent/agent_analyzer.py
# Replace _call_ollama() method (lines 278-309)
# ==============================================================================

AGENT_ANALYZER_CALL_OLLAMA_METHOD = '''
    def _call_ollama(self, prompt: str) -> str:
        """
        Call Ollama generate API with the prompt and proper timeout handling.

        Args:
            prompt: Full prompt text

        Returns:
            str: Response text from Ollama
        """
        import requests

        # Ensure timeout is set (ADDED)
        timeout = getattr(self.ollama_client, 'timeout', 30)
        if timeout is None or timeout <= 0:
            timeout = 30  # Default 30 seconds

        try:
            response = requests.post(
                f"{self.ollama_client.base_url}/api/generate",
                json={
                    "model": self.ollama_client.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=timeout
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API returned status {response.status_code}")

            result = response.json()
            return result.get("response", "")

        except requests.exceptions.Timeout:
            # Specific timeout exception (ADDED)
            raise Exception(f"Ollama request timed out after {timeout} seconds. Try increasing timeout or using a faster model.")
        except requests.exceptions.ConnectionError as e:
            # Specific connection exception (ADDED)
            raise Exception(f"Cannot connect to Ollama at {self.ollama_client.base_url}. Is Ollama running?")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ollama request failed: {str(e)}")
'''

# ==============================================================================
# INSTRUCTIONS
# ==============================================================================

INSTRUCTIONS = """
HOW TO APPLY THESE FIXES:

1. FIX #1 & #2 & #3 - ActionManager (src/core/actions.py):
   - Replace the entire execute() method with ACTIONS_PY_EXECUTE_METHOD
   - Replace the _build_destination_path() method with ACTIONS_PY_BUILD_DESTINATION_METHOD
   - Replace the _perform_action() method with ACTIONS_PY_PERFORM_ACTION_METHOD

2. FIX #4 - AgentAnalyzer source blacklist (src/agent/agent_analyzer.py):
   - Add the _check_source_blacklist() method before _apply_safety_checks()
   - Replace _apply_safety_checks() with the updated version

3. FIX #5 - Ollama timeout (src/agent/agent_analyzer.py):
   - Replace the _call_ollama() method with AGENT_ANALYZER_CALL_OLLAMA_METHOD

4. After applying fixes, run:
   python tools/test_agent.py

5. Test manually:
   - Create folder policy with allow_move: false
   - Drop file in that folder
   - Verify ActionManager blocks the move
   - Test deep analyze on the file
   - Verify agent also reports blocked

VERIFICATION:
- All 5 critical issues should be resolved
- Test harness should pass all tests
- Dashboard should work without errors
- Files should move to correct base_destination
"""

print(__doc__)
print(INSTRUCTIONS)
