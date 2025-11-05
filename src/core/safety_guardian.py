"""
Safety Guardian Module - Final Evaluation Layer

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module implements a comprehensive multi-layered safety system that acts as
the FINAL checkpoint before any file operation. It uses reasoning AI to evaluate
the entire operation context and prevent any potentially harmful actions.

SAFETY LAYERS:
1. Path Security - Prevents path traversal, escapes, system file access
2. Business Logic - Validates classification makes sense
3. Consequence Analysis - Predicts and prevents negative outcomes
4. User Data Protection - Prevents accidental data loss
5. System Integrity - Protects OS and application files
6. Reasoning Evaluation - Final AI check with detailed reasoning

NOTICE: This software is proprietary and confidential.
See LICENSE.txt for full terms and conditions.

Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import json


logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk levels for file operations"""
    SAFE = "safe"                # Operation is safe to proceed
    CAUTION = "caution"          # Proceed with user confirmation
    HIGH_RISK = "high_risk"      # Strongly recommend against
    CRITICAL = "critical"        # Block operation immediately
    

class ThreatType(Enum):
    """Types of threats the guardian can detect"""
    PATH_TRAVERSAL = "path_traversal"
    SYSTEM_FILE = "system_file"
    APPLICATION_FILE = "application_file"
    DATA_LOSS = "data_loss"
    PERMISSION_ISSUE = "permission_issue"
    INVALID_DESTINATION = "invalid_destination"
    LOGIC_ERROR = "logic_error"
    CIRCULAR_REFERENCE = "circular_reference"
    DESTRUCTIVE_OPERATION = "destructive_operation"


class SafetyGuardian:
    """
    Final safety checkpoint - evaluates every file operation before execution.
    
    This acts as the last line of defense against any potentially harmful
    file operations. It uses multiple validation layers and AI reasoning
    to ensure no mistakes slip through.
    """
    
    # Critical system paths that should NEVER be modified
    CRITICAL_PATHS_WINDOWS = [
        "C:\\Windows",
        "C:\\Windows\\System32",
        "C:\\Windows\\SysWOW64",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\ProgramData\\Microsoft",
        "C:\\Users\\Default",
        "C:\\Users\\Public",
        "C:\\System Volume Information",
        "C:\\$Recycle.Bin",
        "C:\\Recovery",
        "C:\\Boot",
        "C:\\bootmgr",
        "C:\\hiberfil.sys",
        "C:\\pagefile.sys",
        "C:\\swapfile.sys",
    ]
    
    CRITICAL_PATHS_UNIX = [
        "/bin",
        "/sbin",
        "/usr/bin",
        "/usr/sbin",
        "/lib",
        "/lib64",
        "/usr/lib",
        "/usr/lib64",
        "/etc",
        "/boot",
        "/sys",
        "/proc",
        "/dev",
        "/root",
        "/var/log",
        "/var/lib/dpkg",
        "/var/lib/rpm",
    ]
    
    # Application-related paths to protect
    APP_PATHS_WINDOWS = [
        "AppData\\Local",
        "AppData\\Roaming",
        "AppData\\LocalLow",
        ".config",
        ".cache",
        ".local",
    ]
    
    # Extensions that should never be moved from their location
    CRITICAL_EXTENSIONS = [
        ".sys", ".dll", ".exe", ".drv", ".ocx",  # System/executable files
        ".so", ".dylib", ".a",  # Unix libraries
        ".ini", ".cfg", ".conf",  # Configuration files in wrong context
    ]
    
    # Minimum confidence threshold for auto-approval
    MIN_CONFIDENCE_THRESHOLD = 0.75
    
    def __init__(self, config, ollama_client=None):
        """
        Initialize Safety Guardian.
        
        Args:
            config: Application configuration
            ollama_client: Optional Ollama client for AI reasoning evaluation
        """
        self.config = config
        self.ollama_client = ollama_client
        self.blocked_operations = []  # Track blocked operations for audit
        # Cache for custom protections
        self._custom_protections: Optional[Dict[str, Any]] = None
        # Initialize protected patterns and known app folders
        self.PROTECTED_PATTERNS = [
            'c:\\windows',
            'c:\\program files',
            'c:\\program files (x86)',
            'c:\\programdata',
            '\\steam',
            '\\steamapps',
            '\\steamlibrary',
            '\\epic games',
            '\\epicgames',
            '\\origin',
            '\\gog galaxy',
            '\\gog games',
            '\\xboxgames',
            '\\appdata',
            '\\ubisoft',
            '\\battle.net',
            '\\riot games',
            'microsoft visual studio',
            'jetbrains',
            'nodejs',
            '\\games\\',
            '\\development\\',
        ]
        self.KNOWN_APP_FOLDERS = {
            'steam', 'steamapps', 'steamlibrary',
            'epic games', 'epicgames',
            'origin', 'origin games',
            'gog galaxy', 'gog', 'gog games',
            'ubisoft', 'uplay', 'ubisoft game launcher',
            'battle.net', 'blizzard',
            'riot games', 'riot',
            'microsoft games', 'xbox', 'xboxgames',
        }
        # Protected extensions (system/application/game)
        self.PROTECTED_EXTENSIONS = {
            # System / executables
            '.exe', '.dll', '.sys', '.ocx', '.drv', '.msi', '.bat', '.cmd',
            # Game engines and data
            '.pak', '.uasset', '.umap', '.assets', '.bundle',
            '.wad', '.pk3', '.bsp', '.vpk', '.esm', '.esp', '.forge', '.jar',
            # Shaders / graphics
            '.shader', '.hlsl', '.glsl', '.dds', '.material',
        }
        
    def evaluate_operation(self, 
                          source_path: str,
                          destination_path: str,
                          operation: str,
                          classification: Dict[str, Any],
                          user_approved: bool = False) -> Dict[str, Any]:
        """
        Comprehensive evaluation of a file operation before execution.
        
        This is the FINAL checkpoint. If this returns risk_level != SAFE,
        the operation MUST NOT proceed without explicit user override.
        
        Args:
            source_path: Original file location
            destination_path: Proposed new location
            operation: Type of operation (move, rename, delete, etc.)
            classification: Classification result from AI/rules
            user_approved: Whether user has explicitly approved
            
        Returns:
            Dict with evaluation result:
                - approved: bool (safe to proceed)
                - risk_level: RiskLevel enum
                - threats: List of detected threats
                - warnings: List of warning messages
                - reasoning: Detailed explanation
                - requires_confirmation: bool
                - recommended_action: str
        """
        logger.info(f"[SAFETY GUARDIAN] Evaluating {operation}: {source_path} -> {destination_path}")
        
        threats = []
        warnings = []
        
        # LAYER 1: Path Security Validation
        path_threats = self._check_path_security(source_path, destination_path)
        threats.extend(path_threats)
        
        # LAYER 2: System File Protection
        system_threats = self._check_system_file_protection(source_path, destination_path)
        threats.extend(system_threats)
        
        # LAYER 3: Application Integrity
        app_threats = self._check_application_integrity(source_path, destination_path)
        threats.extend(app_threats)

        # New comprehensive application/game protection check (multi-layer)
        try:
            ok, reason = self.is_file_safe_to_modify(Path(source_path))
            if not ok:
                severity = "critical" if "Protected" in reason or "application" in reason.lower() else "high"
                threats.append((
                    ThreatType.APPLICATION_FILE,
                    severity,
                    f"{reason}: {source_path}"
                ))
        except Exception:
            threats.append((
                ThreatType.APPLICATION_FILE,
                "high",
                "Safety check error while verifying application/game protections"
            ))
        
        # LAYER 4: Data Loss Prevention
        data_threats = self._check_data_loss_prevention(source_path, destination_path, operation)
        threats.extend(data_threats)
        
        # LAYER 5: Logic Validation
        logic_warnings = self._check_logic_validation(source_path, destination_path, classification)
        warnings.extend(logic_warnings)
        
        # LAYER 6: Permission & Access Checks
        permission_threats = self._check_permissions(source_path, destination_path)
        threats.extend(permission_threats)
        
        # Determine risk level based on threats
        risk_level = self._calculate_risk_level(threats, warnings)
        
        # LAYER 7: AI Reasoning Evaluation (if available, enabled in config, and needed)
        ai_evaluation = None
        try:
            ai_gate_enabled = bool(self.config.get('safety.ai_reasoning.enabled', False))
        except Exception:
            ai_gate_enabled = False

        if self.ollama_client and ai_gate_enabled and risk_level in [RiskLevel.CAUTION, RiskLevel.HIGH_RISK]:
            ai_evaluation = self._ai_reasoning_check(
                source_path, destination_path, operation,
                classification, threats, warnings
            )
            
            # AI can upgrade or downgrade risk
            if ai_evaluation and ai_evaluation.get('success'):
                ai_risk = ai_evaluation.get('final_risk_level')
                if ai_risk == 'critical':
                    risk_level = RiskLevel.CRITICAL
                elif ai_risk == 'high_risk' and risk_level == RiskLevel.CAUTION:
                    risk_level = RiskLevel.HIGH_RISK
                elif ai_risk == 'safe' and risk_level == RiskLevel.CAUTION and not threats:
                    risk_level = RiskLevel.SAFE
        
        # Build result
        result = {
            'approved': self._should_approve(risk_level, user_approved, threats),
            'risk_level': risk_level.value,
            'threats': [self._threat_to_dict(t) for t in threats],
            'warnings': warnings,
            'reasoning': self._build_reasoning(risk_level, threats, warnings, ai_evaluation),
            'requires_confirmation': risk_level in [RiskLevel.CAUTION, RiskLevel.HIGH_RISK],
            'recommended_action': self._get_recommended_action(risk_level, user_approved),
            'ai_evaluation': ai_evaluation
        }
        
        # Log blocked operations for audit
        if not result['approved']:
            self._log_blocked_operation(source_path, destination_path, operation, result)
        
        logger.info(f"[SAFETY GUARDIAN] Evaluation result: {risk_level.value} - {'APPROVED' if result['approved'] else 'BLOCKED'}")
        
        return result

    # ========================= APPLICATION/GAME PROTECTION LAYERS =========================
    def load_custom_protections(self) -> Dict[str, Any]:
        """Load or initialize custom protected paths/extensions and depth limit.

        Returns a dict with keys: protected_paths (List[Path]),
        protected_extensions (Set[str]), scan_depth_limit (int)
        """
        if self._custom_protections is not None:
            return self._custom_protections

        config_dir = Path(__file__).parent.parent.parent / 'config'
        config_dir.mkdir(exist_ok=True)
        cfg_path = config_dir / 'protected_paths.json'
        default = {
            "protected_paths": [],
            "protected_extensions": [],
            "scan_depth_limit": 3
        }
        try:
            if not cfg_path.exists():
                cfg_path.write_text(json.dumps(default, indent=2), encoding='utf-8')
                data = default
            else:
                data = json.loads(cfg_path.read_text(encoding='utf-8'))
        except Exception:
            data = default

        protected_paths = []
        for p in data.get('protected_paths', []):
            try:
                protected_paths.append(Path(p).expanduser().resolve())
            except Exception:
                continue

        protected_exts = set(e.lower() if e.startswith('.') else f".{e.lower()}" for e in data.get('protected_extensions', []))
        scan_depth_limit = int(data.get('scan_depth_limit', 3))

        self._custom_protections = {
            'protected_paths': protected_paths,
            'protected_extensions': protected_exts,
            'scan_depth_limit': scan_depth_limit,
        }
        return self._custom_protections

    def contains_app_folder_name(self, path: Path) -> Optional[str]:
        """Return matched known application/game folder name if found in path."""
        try:
            s = str(path).lower()
            for name in self.KNOWN_APP_FOLDERS:
                if name in s:
                    return name
        except Exception:
            pass
        return None

    def is_protected_path(self, file_path: Path) -> bool:
        """Layer 1: Path-based protection across all drives and patterns."""
        try:
            s = str(file_path).lower()
            # Quick prefix checks for Windows critical dirs
            for crit in self.CRITICAL_PATHS_WINDOWS:
                try:
                    if s.startswith(crit.lower()):
                        return True
                except Exception:
                    continue

            # Pattern checks
            for pat in self.PROTECTED_PATTERNS:
                if pat in s:
                    return True

            # Custom protected paths
            custom = self.load_custom_protections()
            for cp in custom['protected_paths']:
                try:
                    if file_path.resolve().as_posix().lower().startswith(cp.as_posix().lower()):
                        return True
                except Exception:
                    continue
        except Exception:
            return True  # fail-safe
        return False

    def is_application_folder(self, folder_path: Path) -> bool:
        """Layer 2: Detect if a folder likely contains an installed application/game."""
        try:
            if not folder_path.exists() or not folder_path.is_dir():
                return False

            # Check exe+dll presence
            exe_count = sum(1 for p in folder_path.glob('*.exe'))
            dll_count = sum(1 for p in folder_path.glob('*.dll'))
            if exe_count > 0 and dll_count > 0:
                return True

            # Game engine indicators
            indicators = ['UnrealEngine', 'UE4', 'UE5', 'Unity', 'Engine']
            for ind in indicators:
                if (folder_path / ind).exists():
                    return True

            # Files indicating engines
            pak_count = len(list(folder_path.glob('*.pak')))
            assets_count = len(list(folder_path.glob('*.assets')))
            if pak_count >= 20 or assets_count >= 20:
                return True

            # Installer artifacts
            if (folder_path / 'unins000.exe').exists() or (folder_path / 'uninstall.exe').exists():
                return True

            # Known app folder names in path
            if self.contains_app_folder_name(folder_path):
                return True
        except Exception:
            return True  # fail-safe
        return False

    def is_protected_file_type(self, file_path: Path) -> bool:
        """Layer 4: File type protection independent of location."""
        try:
            ext = file_path.suffix.lower()
            if ext in self.PROTECTED_EXTENSIONS:
                return True
            # Include custom protected extensions
            custom = self.load_custom_protections()
            if ext in custom['protected_extensions']:
                return True
        except Exception:
            return True
        return False

    def has_application_siblings(self, file_path: Path) -> bool:
        """Layer 5: Detect sibling indicators in the same folder."""
        try:
            parent = file_path.parent
            if not parent.exists():
                return False
            exe_count = len(list(parent.glob('*.exe')))
            dll_count = len(list(parent.glob('*.dll')))
            if exe_count > 0 and dll_count > 0:
                return True
            # Engine bulk
            if len(list(parent.glob('*.pak'))) > 10 or len(list(parent.glob('*.assets'))) > 10:
                return True
        except Exception:
            return True
        return False

    def is_file_part_of_application(self, file_path: Path) -> bool:
        """Layer 3: Context analysis by walking up to N parents."""
        try:
            custom = self.load_custom_protections()
            depth_limit = max(1, int(custom.get('scan_depth_limit', 3)))
            cur = file_path if file_path.is_dir() else file_path.parent
            steps = 0
            while True:
                if self.is_protected_path(cur):
                    return True
                if self.is_application_folder(cur):
                    return True
                if steps >= 5 or steps >= depth_limit:
                    break
                if cur.parent == cur:
                    break
                cur = cur.parent
                steps += 1
        except Exception:
            return True
        return False

    def is_file_safe_to_modify(self, file_path: Path) -> Tuple[bool, str]:
        """Master safety check combining all layers for a single file path."""
        try:
            p = Path(file_path)
            if self.is_protected_path(p):
                return False, "Protected system/application path"
            if self.is_protected_file_type(p):
                return False, "Protected file type (.exe, .dll, game data, etc.)"
            if self.is_file_part_of_application(p):
                return False, "Part of installed application"
            if self.has_application_siblings(p):
                return False, "In application folder (has .exe and .dll files)"
            return True, "Safe to modify"
        except Exception as e:
            return False, f"Safety check failed: {e}"

    # Public helpers for integration per spec
    def check_application_file(self, file_path: Path) -> Tuple[bool, str]:
        """Check if file is part of an application; returns (safe, reason)."""
        return self.is_file_safe_to_modify(file_path)

    def get_protected_locations(self) -> List[Path]:
        """Return list of protected base locations including custom ones."""
        locations: List[Path] = []
        # From constants
        for p in self.CRITICAL_PATHS_WINDOWS:
            try:
                locations.append(Path(p))
            except Exception:
                continue
        # Common app platform roots
        common = [
            'C:\\Program Files\\Steam', 'C:\\Program Files (x86)\\Steam',
            'C:\\Program Files\\Epic Games', 'C:\\Program Files (x86)\\Epic Games',
            'C:\\Program Files\\Origin', 'C:\\Program Files\\GOG Galaxy',
            'C:\\XboxGames'
        ]
        for p in common:
            locations.append(Path(p))
        # Custom
        custom = self.load_custom_protections()
        locations.extend(custom['protected_paths'])
        return locations

    def validate_scan_folder(self, folder_path: Path) -> Tuple[bool, str]:
        """Validate user-specified scan folder against protections; may prompt upstream.

        Note: Interactive prompts are not handled here; caller should act on the reason.
        """
        try:
            if self.is_protected_path(folder_path):
                return False, "Protected system/application folder"
            # .exe count (non-recursive)
            exe_count = len([p for p in folder_path.glob('*.exe') if p.is_file()])
            if exe_count > 0:
                return False, f"WARNING: {folder_path} contains {exe_count} .exe files"
            matched = self.contains_app_folder_name(folder_path)
            if matched:
                return False, f"WARNING: This appears to be an application folder (detected: {matched})"
            return True, "Safe to scan"
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def _check_path_security(self, _source: str, destination: str) -> List[Tuple[ThreatType, str, str]]:
        """
        Check for path traversal and security issues including symlink cycle detection.

        This function implements multiple layers of path security validation:
        1. Path traversal pattern detection (".." in paths)
        2. Base directory escape prevention (paths must stay within base_destination)
        3. Symlink cycle detection (prevents infinite loops)
        4. Suspicious character detection (null bytes, control characters)

        Args:
            _source: Source file path (unused but kept for API consistency)
            destination: Destination path to validate

        Returns:
            List of (ThreatType, severity, message) tuples for detected threats
        """
        threats = []

        # Check for path traversal patterns - simple but effective first line of defense
        # Why: ".." can be used to escape intended directories (e.g., "../../../etc/passwd")
        if ".." in destination:
            threats.append((
                ThreatType.PATH_TRAVERSAL,
                "critical",
                f"Destination contains '..' (path traversal attack pattern): {destination}"
            ))

        # Check for absolute paths escaping base destination
        dest_path = Path(destination)
        if dest_path.is_absolute():
            try:
                # Resolve base destination to canonical absolute path
                # Why: expanduser() handles ~, resolve() handles symlinks and relative paths
                base_dest = Path(self.config.base_destination).expanduser().resolve()

                # CRITICAL FIX: Symlink cycle detection with max depth
                # Why: Circular symlinks can cause infinite loops crashing the application
                # Reference: https://docs.python.org/3/library/pathlib.html#pathlib.Path.resolve
                try:
                    # resolve(strict=False) doesn't require path to exist, but still detects cycles
                    # Python raises RuntimeError if it encounters a symlink loop during resolution
                    dest_resolved = dest_path.resolve(strict=False)
                except RuntimeError as cycle_err:
                    threats.append((
                        ThreatType.CIRCULAR_REFERENCE,
                        "critical",
                        f"Symlink cycle detected in path: {destination} - {str(cycle_err)}"
                    ))
                    return threats  # Early return - don't process further if cycle detected

                # Verify destination is within base_destination using relative_to()
                # Why: This prevents path traversal even if paths are absolute
                # Example: /home/user/docs/../../etc/passwd would be detected here
                try:
                    dest_resolved.relative_to(base_dest)
                except ValueError:
                    threats.append((
                        ThreatType.PATH_TRAVERSAL,
                        "critical",
                        f"Destination escapes base directory: {destination} is outside {base_dest}"
                    ))
            except RuntimeError as e:
                # Catch RuntimeError separately (symlink resolution issues)
                threats.append((
                    ThreatType.CIRCULAR_REFERENCE,
                    "critical",
                    f"Symlink resolution error: {str(e)}"
                ))
            except Exception as e:
                # Catch all other exceptions (filesystem errors, permission issues, etc.)
                threats.append((
                    ThreatType.INVALID_DESTINATION,
                    "high",
                    f"Cannot validate destination path: {e}"
                ))

        # Check for suspicious characters in paths
        # Why: Control characters and null bytes can be used in injection attacks
        # Example: "file.txt\x00.pdf" might bypass extension checks in some systems
        suspicious_chars = ['\\x00', '\n', '\r', '\t']
        for char in suspicious_chars:
            if char in destination:
                threats.append((
                    ThreatType.PATH_TRAVERSAL,
                    "critical",
                    f"Destination contains suspicious character: {repr(char)}"
                ))

        return threats
    
    def _check_system_file_protection(self, source: str, _destination: str) -> List[Tuple[ThreatType, str, str]]:
        """Protect critical system files"""
        threats = []
        
        try:
            source_resolved = str(Path(source).resolve())
            
            # Check Windows system paths
            if os.name == 'nt':
                for critical_path in self.CRITICAL_PATHS_WINDOWS:
                    try:
                        if source_resolved.startswith(critical_path.lower()) or \
                           source_resolved.lower().startswith(critical_path.lower()):
                            threats.append((
                                ThreatType.SYSTEM_FILE,
                                "critical",
                                f"CRITICAL: File is in system directory {critical_path}. "
                                f"Moving system files will break Windows!"
                            ))
                            break
                    except:
                        pass
            
            # Check Unix system paths
            else:
                for critical_path in self.CRITICAL_PATHS_UNIX:
                    if source_resolved.startswith(critical_path):
                        threats.append((
                            ThreatType.SYSTEM_FILE,
                            "critical",
                            f"CRITICAL: File is in system directory {critical_path}. "
                            f"Moving system files will break the OS!"
                        ))
                        break
            
            # Check for critical file extensions in wrong context
            source_path = Path(source)
            if source_path.suffix.lower() in self.CRITICAL_EXTENSIONS:
                # Only threat if in system/program directories
                parent_str = str(source_path.parent).lower()
                if any(x in parent_str for x in ['windows', 'system32', 'program files', 'bin', 'lib', 'sbin']):
                    threats.append((
                        ThreatType.SYSTEM_FILE,
                        "critical",
                        f"CRITICAL: File {source_path.suffix} in system/application directory. "
                        f"Moving will likely break software!"
                    ))
        
        except Exception as e:
            logger.error(f"Error checking system file protection: {e}")
        
        return threats
    
    def _check_application_integrity(self, source: str, _destination: str) -> List[Tuple[ThreatType, str, str]]:
        """Protect application files and configurations"""
        threats = []
        
        try:
            source_path = Path(source)
            source_str = str(source_path).lower()
            
            # Check if file is in an application installation directory
            app_indicators = [
                'program files', 'program files (x86)', 'programdata',
                '.app/contents', '/applications/', '/opt/',
                'appdata\\local\\programs', 'appdata\\roaming'
            ]
            
            for indicator in app_indicators:
                if indicator in source_str:
                    # Check if it's an executable or library
                    if source_path.suffix.lower() in ['.exe', '.dll', '.so', '.dylib', '.app']:
                        threats.append((
                            ThreatType.APPLICATION_FILE,
                            "critical",
                            f"CRITICAL: Executable/library in application directory. "
                            f"Moving will break the application!"
                        ))
                        break
                    
                    # Check if it's a config file in app directory
                    if source_path.suffix.lower() in ['.ini', '.cfg', '.conf', '.plist']:
                        threats.append((
                            ThreatType.APPLICATION_FILE,
                            "high",
                            f"WARNING: Configuration file in application directory. "
                            f"Moving may break application settings."
                        ))
                        break
        
        except Exception as e:
            logger.error(f"Error checking application integrity: {e}")
        
        return threats
    
    def _check_data_loss_prevention(self, source: str, destination: str, operation: str) -> List[Tuple[ThreatType, str, str]]:
        """Prevent accidental data loss"""
        threats = []
        
        try:
            dest_path = Path(destination)
            
            # Check if destination already exists
            if dest_path.exists():
                source_path = Path(source)
                
                # If sizes differ significantly, could be overwriting important file
                if dest_path.is_file() and source_path.exists():
                    source_size = source_path.stat().st_size
                    dest_size = dest_path.stat().st_size
                    
                    if dest_size > source_size * 2:  # Destination is 2x+ larger
                        threats.append((
                            ThreatType.DATA_LOSS,
                            "high",
                            f"WARNING: Destination file is significantly larger ({dest_size} vs {source_size} bytes). "
                            f"Overwriting may cause data loss!"
                        ))
            
            # Check for destructive operations
            if operation == 'delete':
                source_path = Path(source)
                if source_path.is_file():
                    size = source_path.stat().st_size
                    # Flag deletion of large files
                    if size > 100 * 1024 * 1024:  # > 100MB
                        threats.append((
                            ThreatType.DESTRUCTIVE_OPERATION,
                            "high",
                            f"WARNING: Deleting large file ({size / (1024*1024):.1f} MB). "
                            f"This cannot be undone!"
                        ))
            
            # Check for moving to same location (circular reference)
            try:
                if Path(source).resolve() == Path(destination).resolve():
                    threats.append((
                        ThreatType.CIRCULAR_REFERENCE,
                        "medium",
                        "File is already at destination location (no-op)."
                    ))
            except:
                pass
        
        except Exception as e:
            logger.error(f"Error in data loss prevention check: {e}")
        
        return threats
    
    def _check_logic_validation(self, source: str, destination: str, classification: Dict[str, Any]) -> List[str]:
        """Validate the logic of the classification"""
        warnings = []
        
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            # Check confidence level
            confidence = classification.get('confidence', 'unknown')
            if confidence == 'low':
                warnings.append(
                    f"Classification confidence is LOW. Recommendation may not be accurate."
                )
            
            # Check if file extension matches destination category
            extension = source_path.suffix.lower()
            dest_str = str(dest_path).lower()
            
            # Example: moving .pdf to Pictures folder is suspicious
            suspicious_combinations = [
                (['pdf', 'doc', 'docx', 'txt'], ['pictures', 'images', 'photos']),
                (['jpg', 'png', 'gif', 'bmp'], ['documents', 'text']),
                (['exe', 'msi', 'app'], ['documents', 'pictures']),
                (['mp4', 'avi', 'mkv'], ['documents', 'pictures']),
            ]
            
            for extensions, wrong_dest in suspicious_combinations:
                if any(ext in extension for ext in extensions):
                    if any(cat in dest_str for cat in wrong_dest):
                        warnings.append(
                            f"Logic warning: {extension} file being moved to {dest_str}. "
                            f"This seems unusual - verify classification is correct."
                        )
            
            # Check if suggested path seems reasonable length
            if len(str(dest_path)) > 250:  # Windows MAX_PATH is 260
                warnings.append(
                    f"Destination path is very long ({len(str(dest_path))} chars). "
                    f"May cause issues on Windows systems."
                )
        
        except Exception as e:
            logger.error(f"Error in logic validation: {e}")
        
        return warnings
    
    def _check_permissions(self, source: str, destination: str) -> List[Tuple[ThreatType, str, str]]:
        """Check file permissions and access rights"""
        threats = []

        try:
            _source_path = Path(source)
            
            # Check if we have read access to source
            if not os.access(source, os.R_OK):
                threats.append((
                    ThreatType.PERMISSION_ISSUE,
                    "critical",
                    f"No read permission for source file: {source}"
                ))
            
            # Check if file is writable (needed for move/delete)
            if not os.access(source, os.W_OK):
                threats.append((
                    ThreatType.PERMISSION_ISSUE,
                    "high",
                    f"No write permission for source file: {source}. Cannot move/delete."
                ))
            
            # Check if destination directory exists and is writable
            dest_path = Path(destination)
            dest_dir = dest_path.parent
            
            if dest_dir.exists():
                if not os.access(dest_dir, os.W_OK):
                    threats.append((
                        ThreatType.PERMISSION_ISSUE,
                        "critical",
                        f"No write permission for destination directory: {dest_dir}"
                    ))
        
        except Exception as e:
            logger.error(f"Error checking permissions: {e}")
        
        return threats
    
    def _ai_reasoning_check(self, source: str, destination: str, operation: str,
                           classification: Dict[str, Any], threats: List, warnings: List) -> Optional[Dict]:
        """
        Final AI reasoning check - asks AI to evaluate the entire operation context.
        """
        if not self.ollama_client or not self.ollama_client.is_available():
            return None
        
        # Build comprehensive prompt for final evaluation
        prompt = f"""You are a safety evaluation AI. Your job is to perform a FINAL SAFETY CHECK
before a file operation is executed. Analyze the entire context and determine if this operation
is safe or if it could cause problems.

OPERATION DETAILS:
- Operation Type: {operation}
- Source: {source}
- Destination: {destination}

CLASSIFICATION RESULT:
{json.dumps(classification, indent=2)}

THREATS DETECTED:
{json.dumps([{'type': t[0].value, 'severity': t[1], 'message': t[2]} for t in threats], indent=2)}

WARNINGS:
{json.dumps(warnings, indent=2)}

YOUR TASK:
Carefully analyze this operation and provide a final safety evaluation.

Consider:
1. Could this operation break the operating system or applications?
2. Could this cause data loss or file corruption?
3. Is the destination logical for this file type?
4. Are there any security concerns?
5. Could this operation have unintended consequences?
6. Is the classification reasoning sound?

Provide your evaluation in JSON format:
{{
  "final_risk_level": "safe|caution|high_risk|critical",
  "should_proceed": true/false,
  "reasoning": "Your detailed analysis (3-5 sentences)",
  "concerns": ["List specific concerns if any"],
  "recommendations": ["Suggestions to make operation safer"],
  "confidence": 0.0 to 1.0
}}

IMPORTANT: Be conservative. If you have ANY doubt, recommend caution or rejection.

Your evaluation:"""
        
        try:
            import requests

            # Respect configured timeout (fallback to 30s)
            timeout_seconds = 30
            try:
                timeout_seconds = int(self.config.get('safety.ai_reasoning.timeout_seconds', 30))
            except Exception:
                timeout_seconds = 30

            # Build target URL and model
            base_url = getattr(self.ollama_client, 'base_url', None) or self.config.get('ollama_base_url')
            model = getattr(self.ollama_client, 'model', None) or self.config.get('ollama_model')

            response = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=timeout_seconds
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                
                # Parse JSON
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                
                evaluation = json.loads(response_text)
                evaluation['success'] = True
                return evaluation
        
        except Exception as e:
            logger.error(f"AI reasoning check failed: {e}")
        
        return None
    
    def _calculate_risk_level(self, threats: List, warnings: List) -> RiskLevel:
        """Calculate overall risk level from threats and warnings"""
        
        if not threats and not warnings:
            return RiskLevel.SAFE
        
        # Check for critical threats
        for threat in threats:
            severity = threat[1] if len(threat) > 1 else "unknown"
            if severity == "critical":
                return RiskLevel.CRITICAL
        
        # Check for high severity threats
        high_count = sum(1 for t in threats if len(t) > 1 and t[1] == "high")
        if high_count >= 2:
            return RiskLevel.HIGH_RISK
        elif high_count == 1:
            return RiskLevel.CAUTION
        
        # Medium severity or warnings only
        if threats or len(warnings) >= 3:
            return RiskLevel.CAUTION
        
        return RiskLevel.SAFE
    
    def _should_approve(self, risk_level: RiskLevel, user_approved: bool, threats: List) -> bool:
        """Determine if operation should be approved"""
        
        # CRITICAL threats are NEVER auto-approved
        if risk_level == RiskLevel.CRITICAL:
            return False
        
        # HIGH_RISK requires explicit user approval
        if risk_level == RiskLevel.HIGH_RISK:
            return user_approved
        
        # CAUTION can proceed with user approval or if no critical threats
        if risk_level == RiskLevel.CAUTION:
            # Check if any threats are actually critical despite risk level
            has_critical_threat = any(
                t[1] == "critical" for t in threats if len(t) > 1
            )
            if has_critical_threat:
                return False
            return user_approved or self.config.get('auto_approve_caution', False)
        
        # SAFE operations can proceed
        return True
    
    def _build_reasoning(self, risk_level: RiskLevel, threats: List, warnings: List, 
                        ai_eval: Optional[Dict]) -> str:
        """Build human-readable reasoning for the decision"""
        
        parts = [f"Risk Level: {risk_level.value.upper()}"]
        
        if threats:
            parts.append(f"\n\nThreats Detected ({len(threats)}):")
            for threat in threats[:5]:  # Show first 5
                parts.append(f"  - [{threat[1].upper()}] {threat[2]}")
        
        if warnings:
            parts.append(f"\n\nWarnings ({len(warnings)}):")
            for warning in warnings[:5]:
                parts.append(f"  - {warning}")
        
        if ai_eval and ai_eval.get('reasoning'):
            parts.append(f"\n\nAI Evaluation:\n{ai_eval['reasoning']}")
        
        if risk_level == RiskLevel.CRITICAL:
            parts.append("\n\n⛔ OPERATION BLOCKED: Critical safety concerns detected.")
        elif risk_level == RiskLevel.HIGH_RISK:
            parts.append("\n\n⚠️ HIGH RISK: Explicit user approval required.")
        elif risk_level == RiskLevel.CAUTION:
            parts.append("\n\n⚠️ CAUTION: Review recommended before proceeding.")
        else:
            parts.append("\n\n✅ Operation appears safe to proceed.")
        
        return "\n".join(parts)
    
    def _get_recommended_action(self, risk_level: RiskLevel, user_approved: bool) -> str:
        """Get recommended action based on risk level"""
        
        if risk_level == RiskLevel.CRITICAL:
            return "BLOCK_OPERATION"
        elif risk_level == RiskLevel.HIGH_RISK:
            return "REQUIRE_EXPLICIT_APPROVAL" if not user_approved else "PROCEED_WITH_CAUTION"
        elif risk_level == RiskLevel.CAUTION:
            return "REQUEST_CONFIRMATION"
        else:
            return "PROCEED"
    
    def _threat_to_dict(self, threat: Tuple) -> Dict:
        """Convert threat tuple to dictionary"""
        return {
            'type': threat[0].value if len(threat) > 0 else "unknown",
            'severity': threat[1] if len(threat) > 1 else "unknown",
            'message': threat[2] if len(threat) > 2 else "Unknown threat"
        }
    
    def _log_blocked_operation(self, source: str, destination: str, operation: str, result: Dict):
        """Log blocked operations for security audit"""
        blocked_entry = {
            'timestamp': str(Path(source).stat().st_mtime) if Path(source).exists() else "unknown",
            'operation': operation,
            'source': source,
            'destination': destination,
            'risk_level': result['risk_level'],
            'threats': result['threats']
        }
        
        self.blocked_operations.append(blocked_entry)
        
        logger.warning(f"[SECURITY AUDIT] Blocked operation: {operation} {source} -> {destination}")
        logger.warning(f"[SECURITY AUDIT] Risk: {result['risk_level']}, Threats: {len(result['threats'])}")
    
    def get_blocked_operations(self) -> List[Dict]:
        """Get history of blocked operations for security review"""
        return self.blocked_operations.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get guardian statistics"""
        return {
            'total_blocked': len(self.blocked_operations),
            'threat_types': self._count_threat_types(),
            'risk_levels': self._count_risk_levels()
        }
    
    def _count_threat_types(self) -> Dict[str, int]:
        """Count threats by type"""
        counts = {}
        for entry in self.blocked_operations:
            for threat in entry.get('threats', []):
                threat_type = threat.get('type', 'unknown')
                counts[threat_type] = counts.get(threat_type, 0) + 1
        return counts
    
    def _count_risk_levels(self) -> Dict[str, int]:
        """Count blocked operations by risk level"""
        counts = {}
        for entry in self.blocked_operations:
            risk = entry.get('risk_level', 'unknown')
            counts[risk] = counts.get(risk, 0) + 1
        return counts


# Convenience function
def evaluate_operation_safety(source: str, destination: str, operation: str,
                             classification: Dict, config, ollama_client=None,
                             user_approved: bool = False) -> Dict[str, Any]:
    """
    Evaluate safety of a file operation.
    
    This should be called before EVERY file operation to ensure safety.
    """
    guardian = SafetyGuardian(config, ollama_client)
    return guardian.evaluate_operation(
        source, destination, operation, classification, user_approved
    )


if __name__ == "__main__":
    # Test Safety Guardian
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from src.config import get_config
    
    config = get_config()
    guardian = SafetyGuardian(config)
    
    # Test Case 1: Safe operation
    print("="*70)
    print("TEST 1: Safe operation")
    print("="*70)
    result = guardian.evaluate_operation(
        source_path="C:\\Users\\alex\\Downloads\\invoice.pdf",
        destination_path="C:\\Users\\alex\\Documents\\Finance\\Invoices\\invoice.pdf",
        operation="move",
        classification={'category': 'Finance', 'confidence': 'high'},
        user_approved=False
    )
    print(json.dumps(result, indent=2))
    
    # Test Case 2: System file (CRITICAL)
    print("\n" + "="*70)
    print("TEST 2: System file (should be BLOCKED)")
    print("="*70)
    result = guardian.evaluate_operation(
        source_path="C:\\Windows\\System32\\kernel32.dll",
        destination_path="C:\\Users\\alex\\Documents\\Files\\kernel32.dll",
        operation="move",
        classification={'category': 'System', 'confidence': 'high'},
        user_approved=False
    )
    print(json.dumps(result, indent=2))
    
    # Test Case 3: Path traversal attempt (CRITICAL)
    print("\n" + "="*70)
    print("TEST 3: Path traversal (should be BLOCKED)")
    print("="*70)
    result = guardian.evaluate_operation(
        source_path="C:\\Users\\alex\\Downloads\\file.txt",
        destination_path="C:\\Users\\alex\\Documents\\../../Windows/System32/malware.exe",
        operation="move",
        classification={'category': 'Documents', 'confidence': 'high'},
        user_approved=False
    )
    print(json.dumps(result, indent=2))
    
    print("\n" + "="*70)
    print("Guardian Statistics:")
    print(json.dumps(guardian.get_statistics(), indent=2))
