"""
AI File Organiser - File Safety System

CRITICAL: Protects application and game files from being deleted, moved, or organized.
This prevents breaking installed software on ANY drive (C:, D:, E:, etc.).

Copyright © 2025 Alexandru Emanuel Vasile. All Rights Reserved.
"""

import os
import json
from pathlib import Path
from typing import Tuple, List, Set, Dict, Optional
import platform


class FileSafetySystem:
    """
    Multi-layer protection system to prevent breaking applications and games
    """

    # Protected Windows system folders
    PROTECTED_SYSTEM_PATHS = {
        r'C:\Windows',
        r'C:\Program Files',
        r'C:\Program Files (x86)',
        r'C:\ProgramData',
    }

    # Gaming platform patterns (work on ANY drive)
    GAMING_PATTERNS = {
        'steam', 'steamapps', 'steamlibrary',
        'epic games', 'epicgames',
        'origin', 'origin games',
        'gog galaxy', 'gog', 'gog games',
        'ubisoft', 'uplay', 'ubisoft game launcher',
        'battle.net', 'blizzard',
        'riot games', 'riot',
        'microsoft games', 'xbox', 'xboxgames',
    }

    # Development tool patterns
    DEVELOPMENT_PATTERNS = {
        'microsoft visual studio', 'visual studio',
        'jetbrains', 'pycharm', 'intellij',
        'nodejs', 'node_modules',
        'git',
        'development', 'dev',
    }

    # Protected file extensions (system/application files)
    PROTECTED_SYSTEM_EXTENSIONS = {
        '.exe', '.dll', '.sys', '.ocx', '.drv', '.msi',
        '.bat', '.cmd', '.ps1',
    }

    # Game engine file extensions
    PROTECTED_GAME_EXTENSIONS = {
        '.pak',  # Unreal Engine
        '.assets', '.bundle',  # Unity
        '.uasset', '.umap',  # Unreal Engine
        '.wad', '.pk3', '.bsp',  # id Tech/Quake
        '.vpk',  # Source Engine
        '.esm', '.esp',  # Bethesda games
        '.forge', '.jar',  # Minecraft
    }

    # Save game patterns
    SAVE_GAME_EXTENSIONS = {
        '.sav', '.save', '.dat', '.profile', '.slot'
    }

    # Default safe user folders
    SAFE_SCAN_FOLDERS = None  # Will be initialized in __init__

    def __init__(self):
        """Initialize safety system"""
        self.home = Path.home()

        # Initialize safe scan folders
        self.SAFE_SCAN_FOLDERS = [
            self.home / "Downloads",
            self.home / "Documents",
            self.home / "Pictures",
            self.home / "Videos",
            self.home / "Desktop",
            self.home / "Music",
        ]

        # Load custom protections
        self.custom_protected_paths = []
        self.custom_protected_extensions = set()
        self._load_custom_protections()

    def _load_custom_protections(self):
        """Load custom protected paths from config"""
        config_file = Path("config/protected_paths.json")

        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)

                self.custom_protected_paths = [
                    Path(p) for p in config.get('protected_paths', [])
                ]
                self.custom_protected_extensions = set(
                    config.get('protected_extensions', [])
                )
        except Exception:
            # Create default config
            config_file.parent.mkdir(parents=True, exist_ok=True)
            default_config = {
                "protected_paths": [],
                "protected_extensions": [],
                "scan_depth_limit": 3
            }
            try:
                with open(config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
            except:
                pass

    # Layer 1: Path-Based Protection
    def is_protected_path(self, file_path: Path) -> bool:
        """
        Check if path is in a protected location

        Args:
            file_path: Path to check

        Returns:
            True if path is protected, False otherwise
        """
        path_str = str(file_path).lower()

        # Check Windows system paths
        if platform.system() == 'Windows':
            for protected in self.PROTECTED_SYSTEM_PATHS:
                if path_str.startswith(protected.lower()):
                    return True

        # Check for AppData folders
        if '\\appdata\\' in path_str or '/appdata/' in path_str:
            # Allow Temp folder
            if '\\appdata\\local\\temp' not in path_str:
                return True

        # Check gaming patterns (on ANY drive)
        for pattern in self.GAMING_PATTERNS:
            if pattern in path_str:
                return True

        # Check development patterns
        for pattern in self.DEVELOPMENT_PATTERNS:
            if pattern in path_str:
                return True

        # Check custom protected paths
        for protected_path in self.custom_protected_paths:
            try:
                file_path.relative_to(protected_path)
                return True
            except ValueError:
                continue

        return False

    # Layer 2: Application Folder Detection
    def is_application_folder(self, folder_path: Path) -> bool:
        """
        Detect if folder contains an installed application

        Args:
            folder_path: Folder to check

        Returns:
            True if folder contains an application, False otherwise
        """
        if not folder_path.is_dir():
            return False

        try:
            # Count .exe and .dll files
            exe_count = 0
            dll_count = 0

            for file in folder_path.iterdir():
                if not file.is_file():
                    continue

                ext = file.suffix.lower()
                if ext == '.exe':
                    exe_count += 1
                elif ext == '.dll':
                    dll_count += 1

                # If we find both, it's likely an application
                if exe_count > 0 and dll_count > 0:
                    return True

            # Check for game engine indicators
            for subfolder in folder_path.iterdir():
                if subfolder.is_dir():
                    name = subfolder.name.lower()
                    if name in {'unrealengine', 'ue4', 'ue5', 'unity', 'engine'}:
                        return True

            # Check for .pak files (Unreal Engine games)
            pak_files = list(folder_path.glob('*.pak'))
            if len(pak_files) > 10:
                return True

            # Check for .assets files (Unity games)
            assets_files = list(folder_path.glob('*.assets'))
            if len(assets_files) > 10:
                return True

            # Check for uninstaller
            for file in folder_path.iterdir():
                if file.is_file():
                    name = file.name.lower()
                    if 'unins' in name or 'uninstall' in name:
                        if file.suffix.lower() == '.exe':
                            return True

        except (OSError, PermissionError):
            # If we can't read the folder, treat it as protected
            return True

        return False

    # Layer 3: File Context Analysis
    def is_file_part_of_application(self, file_path: Path) -> bool:
        """
        Check if file is part of an installed application by checking parent folders

        Args:
            file_path: File to check

        Returns:
            True if file is part of an application, False otherwise
        """
        current = file_path.parent
        levels_checked = 0
        max_levels = 5

        while current != current.parent and levels_checked < max_levels:
            # Check if this level is a protected path
            if self.is_protected_path(current):
                return True

            # Check if this level is an application folder
            if self.is_application_folder(current):
                return True

            current = current.parent
            levels_checked += 1

        return False

    # Layer 4: File Type Protection
    def is_protected_file_type(self, file_path: Path) -> bool:
        """
        Check if file type should never be deleted/moved

        Args:
            file_path: File to check

        Returns:
            True if file type is protected, False otherwise
        """
        ext = file_path.suffix.lower()

        # Check system extensions
        if ext in self.PROTECTED_SYSTEM_EXTENSIONS:
            return True

        # Check game extensions
        if ext in self.PROTECTED_GAME_EXTENSIONS:
            return True

        # Check save game extensions (only if in likely game folder)
        if ext in self.SAVE_GAME_EXTENSIONS:
            # Check if parent folder suggests it's a game
            parent_str = str(file_path.parent).lower()
            if any(pattern in parent_str for pattern in self.GAMING_PATTERNS):
                return True

        # Check custom extensions
        if ext in self.custom_protected_extensions:
            return True

        return False

    # Layer 5: Sibling File Detection
    def has_application_siblings(self, file_path: Path) -> bool:
        """
        Check if file has sibling files that indicate it's part of an app

        Args:
            file_path: File to check

        Returns:
            True if file has application siblings, False otherwise
        """
        parent = file_path.parent

        if not parent.exists() or not parent.is_dir():
            return False

        try:
            has_exe = False
            has_dll = False

            for sibling in parent.iterdir():
                if not sibling.is_file():
                    continue

                ext = sibling.suffix.lower()
                if ext == '.exe':
                    has_exe = True
                elif ext == '.dll':
                    has_dll = True

                if has_exe and has_dll:
                    return True

        except (OSError, PermissionError):
            # If we can't read, assume it's protected
            return True

        return False

    # Master Safety Check
    def is_file_safe_to_modify(self, file_path: Path) -> Tuple[bool, str]:
        """
        Master safety check - combines all protection layers

        Args:
            file_path: File to check

        Returns:
            Tuple of (is_safe, reason)
            - is_safe: True if safe to modify, False if protected
            - reason: Explanation of why file is protected (or "Safe to modify")
        """
        # Convert to Path object
        file_path = Path(file_path)

        # Layer 1: Protected path check
        if self.is_protected_path(file_path):
            return (False, "Protected system/application path")

        # Layer 4: Protected file type (check early for performance)
        if self.is_protected_file_type(file_path):
            return (False, f"Protected file type ({file_path.suffix})")

        # Layer 3: Part of application check
        if self.is_file_part_of_application(file_path):
            return (False, "Part of installed application")

        # Layer 5: Application siblings check
        if self.has_application_siblings(file_path):
            return (False, "In application folder (has .exe and .dll files)")

        # All checks passed
        return (True, "Safe to modify")

    def validate_scan_folder(self, folder_path: Path) -> Tuple[bool, str]:
        """
        Validate if folder is safe to scan

        Args:
            folder_path: Folder to validate

        Returns:
            Tuple of (is_valid, message)
        """
        folder_path = Path(folder_path)

        # Check if it's a protected path
        if self.is_protected_path(folder_path):
            return (False, f"Protected system/application folder: {folder_path}")

        # Check if it's an application folder
        if self.is_application_folder(folder_path):
            app_name = self._detect_application_name(folder_path)
            return (False, f"Contains application: {app_name}")

        # Check if folder contains known app folder names
        folder_str = str(folder_path).lower()
        for pattern in self.GAMING_PATTERNS | self.DEVELOPMENT_PATTERNS:
            if pattern in folder_str:
                return (False, f"Appears to be application folder (contains '{pattern}')")

        return (True, "Safe to scan")

    def _detect_application_name(self, folder_path: Path) -> str:
        """Try to detect which application this folder belongs to"""
        folder_str = str(folder_path).lower()

        # Check gaming platforms
        if 'steam' in folder_str:
            return "Steam"
        elif 'epic' in folder_str:
            return "Epic Games"
        elif 'origin' in folder_str:
            return "Origin"
        elif 'gog' in folder_str:
            return "GOG Galaxy"
        elif 'ubisoft' in folder_str:
            return "Ubisoft Connect"
        elif 'battle.net' in folder_str or 'blizzard' in folder_str:
            return "Battle.net"
        elif 'riot' in folder_str:
            return "Riot Games"
        elif 'xbox' in folder_str:
            return "Xbox"

        # Check development tools
        elif 'visual studio' in folder_str:
            return "Visual Studio"
        elif 'jetbrains' in folder_str:
            return "JetBrains IDE"

        return "Unknown Application"

    def filter_safe_files(self, files: List[Path]) -> Tuple[List[Path], Dict[str, int]]:
        """
        Filter list of files to only safe ones

        Args:
            files: List of file paths

        Returns:
            Tuple of (safe_files, protection_summary)
            - safe_files: List of files safe to modify
            - protection_summary: Dict of {reason: count}
        """
        safe_files = []
        protection_summary = {}

        for file_path in files:
            is_safe, reason = self.is_file_safe_to_modify(file_path)

            if is_safe:
                safe_files.append(file_path)
            else:
                protection_summary[reason] = protection_summary.get(reason, 0) + 1

        return safe_files, protection_summary

    def is_safe_location_for_deletion(self, file_path: Path) -> bool:
        """
        Check if file is in a safe location for deletion

        Only allows deletion in specific user folders.

        Args:
            file_path: File to check

        Returns:
            True if in safe deletion location, False otherwise
        """
        file_path = Path(file_path)

        safe_locations = [
            self.home / "Downloads",
            self.home / "Desktop",
            Path(os.getenv('TEMP', '')),
            Path(os.getenv('TMP', '')),
        ]

        for safe_loc in safe_locations:
            if not safe_loc:
                continue
            try:
                file_path.relative_to(safe_loc)
                return True
            except ValueError:
                continue

        return False


# Global safety instance
_safety_instance = None


def get_safety_system() -> FileSafetySystem:
    """Get global safety system instance"""
    global _safety_instance
    if _safety_instance is None:
        _safety_instance = FileSafetySystem()
    return _safety_instance
