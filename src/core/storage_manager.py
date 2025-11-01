"""
Storage Manager - Multi-Drive Space Management

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module handles intelligent storage management across multiple drives,
including space checking, drive selection, and optimization recommendations.

FEATURES:
- Multi-drive support (C:, D:, E:, etc.)
- Real-time space availability checking
- Automatic drive selection based on space
- User preference management
- Storage optimization recommendations
- Archive drive suggestions

NOTICE: This software is proprietary and confidential.
See LICENSE.txt for full terms and conditions.

Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DriveType(Enum):
    """Drive type classification"""
    SYSTEM = "system"          # C: drive (system files)
    DATA = "data"              # D:, E:, etc. (user data)
    EXTERNAL = "external"      # USB, external HDDs
    NETWORK = "network"        # Network drives
    UNKNOWN = "unknown"


class StorageStrategy(Enum):
    """Storage organization strategies"""
    SAME_DRIVE = "same_drive"           # Keep on current drive
    MOST_SPACE = "most_space"           # Use drive with most space
    BALANCED = "balanced"               # Distribute across drives
    USER_CHOICE = "user_choice"         # User specifies drive
    ARCHIVE_SEPARATE = "archive_separate"  # Archives on separate drive


class StorageManager:
    """
    Manages file storage across multiple drives with intelligent selection.
    
    Features:
    - Detects all available drives
    - Checks space availability
    - Recommends optimal drive for files
    - Respects user preferences
    - Handles drive-specific organization
    """
    
    def __init__(self, config=None):
        """
        Initialize storage manager.
        
        Args:
            config: Configuration object with storage preferences
        """
        self.config = config
        self.strategy = getattr(config, 'storage_strategy', StorageStrategy.SAME_DRIVE.value)
        self.preferred_drive = getattr(config, 'preferred_drive', None)
        self.min_free_space_gb = getattr(config, 'min_free_space_gb', 10)
        self.archive_drive = getattr(config, 'archive_drive', None)
        
        # Detect available drives
        self.available_drives = self._detect_drives()
        logger.info(f"Detected {len(self.available_drives)} available drives")
    
    def _detect_drives(self) -> Dict[str, Dict[str, Any]]:
        """
        Detect all available drives on the system.
        
        Returns:
            Dict mapping drive letters to drive information
        """
        drives = {}
        
        # Windows drive detection (A-Z)
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            drive_path = f"{letter}:\\"
            if os.path.exists(drive_path):
                try:
                    usage = shutil.disk_usage(drive_path)
                    drive_type = self._classify_drive(letter, drive_path)
                    
                    drives[letter] = {
                        'path': drive_path,
                        'type': drive_type.value,
                        'total_gb': usage.total / (1024**3),
                        'used_gb': usage.used / (1024**3),
                        'free_gb': usage.free / (1024**3),
                        'used_percent': (usage.used / usage.total) * 100,
                        'available': usage.free > (self.min_free_space_gb * 1024**3)
                    }
                    
                    logger.debug(f"Drive {letter}: {drive_type.value}, "
                               f"{drives[letter]['free_gb']:.1f}GB free")
                except Exception as e:
                    logger.warning(f"Could not access drive {letter}: {e}")
        
        return drives
    
    def _classify_drive(self, letter: str, path: str) -> DriveType:
        """
        Classify drive type based on letter and characteristics.
        
        Args:
            letter: Drive letter
            path: Drive path
            
        Returns:
            DriveType enum
        """
        # C: is typically system drive
        if letter == 'C':
            return DriveType.SYSTEM
        
        # Network drives (mapped network locations)
        if os.path.ismount(path):
            return DriveType.NETWORK
        
        # Check if it's a removable drive (USB, external HDD)
        # This is Windows-specific and would need platform detection
        # For now, classify D-Z as DATA drives
        if letter in 'DEFGHIJKLMNOPQRSTUVWXYZ':
            return DriveType.DATA
        
        return DriveType.UNKNOWN
    
    def get_drive_info(self, drive_letter: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about a specific drive or all drives.
        
        Args:
            drive_letter: Specific drive letter (e.g., 'C', 'D') or None for all
            
        Returns:
            Drive information dict(s)
        """
        if drive_letter:
            drive_letter = drive_letter.upper().rstrip(':')
            return self.available_drives.get(drive_letter, {})
        else:
            return self.available_drives
    
    def select_target_drive(self, 
                           file_path: str,
                           file_size: int,
                           file_category: str,
                           is_archive: bool = False) -> Tuple[str, str]:
        """
        Select the optimal target drive for a file based on strategy.
        
        Args:
            file_path: Current file path
            file_size: File size in bytes
            file_category: Primary category (Finance, Work, Photos, etc.)
            is_archive: Whether this is an archive/old file
            
        Returns:
            Tuple of (selected_drive_letter, reasoning)
        """
        current_drive = Path(file_path).drive.rstrip(':').upper()
        file_size_gb = file_size / (1024**3)
        
        # Strategy: ARCHIVE_SEPARATE
        if is_archive and self.archive_drive and self.strategy == StorageStrategy.ARCHIVE_SEPARATE.value:
            archive_drive = self.archive_drive.upper().rstrip(':')
            if archive_drive in self.available_drives:
                drive_info = self.available_drives[archive_drive]
                if drive_info['available'] and drive_info['free_gb'] > file_size_gb:
                    return archive_drive, f"Archive drive ({archive_drive}:) configured for old files"
        
        # Strategy: USER_CHOICE
        if self.strategy == StorageStrategy.USER_CHOICE.value and self.preferred_drive:
            preferred = self.preferred_drive.upper().rstrip(':')
            if preferred in self.available_drives:
                drive_info = self.available_drives[preferred]
                if drive_info['available'] and drive_info['free_gb'] > file_size_gb:
                    return preferred, f"User preferred drive ({preferred}:)"
                else:
                    logger.warning(f"Preferred drive {preferred}: has insufficient space")
        
        # Strategy: SAME_DRIVE
        if self.strategy == StorageStrategy.SAME_DRIVE.value:
            if current_drive in self.available_drives:
                drive_info = self.available_drives[current_drive]
                if drive_info['available'] and drive_info['free_gb'] > file_size_gb:
                    return current_drive, f"Same drive ({current_drive}:) - sufficient space"
                else:
                    logger.warning(f"Current drive {current_drive}: has insufficient space, "
                                 f"falling back to most_space strategy")
        
        # Strategy: MOST_SPACE (or fallback)
        if self.strategy == StorageStrategy.MOST_SPACE.value or True:  # Fallback
            best_drive = None
            max_free_space = 0
            
            for letter, info in self.available_drives.items():
                # Skip system drive (C:) unless it's the only option
                if letter == 'C' and len(self.available_drives) > 1:
                    continue
                
                if info['available'] and info['free_gb'] > max_free_space and info['free_gb'] > file_size_gb:
                    max_free_space = info['free_gb']
                    best_drive = letter
            
            if best_drive:
                return best_drive, f"Most space available ({best_drive}:) - {max_free_space:.1f}GB free"
        
        # Strategy: BALANCED (distribute across data drives)
        if self.strategy == StorageStrategy.BALANCED.value:
            data_drives = {k: v for k, v in self.available_drives.items() 
                          if v['type'] == DriveType.DATA.value and v['available']}
            
            if data_drives:
                # Find drive with most balanced usage (closest to 50% full)
                balanced_drive = None
                best_balance = float('inf')
                
                for letter, info in data_drives.items():
                    if info['free_gb'] > file_size_gb:
                        # Calculate how far from 50% usage
                        balance_score = abs(50 - info['used_percent'])
                        if balance_score < best_balance:
                            best_balance = balance_score
                            balanced_drive = letter
                
                if balanced_drive:
                    return balanced_drive, f"Balanced distribution ({balanced_drive}:) - {self.available_drives[balanced_drive]['used_percent']:.1f}% used"
        
        # Fallback to current drive (even if low on space)
        return current_drive, f"Fallback to current drive ({current_drive}:) - no better option found"
    
    def check_space_requirements(self, 
                                 files: List[Tuple[str, int]],
                                 target_drive: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if there's enough space for a list of files.
        
        Args:
            files: List of (file_path, file_size) tuples
            target_drive: Target drive letter (None = check all)
            
        Returns:
            Dict with space check results
        """
        total_size_gb = sum(size for _, size in files) / (1024**3)
        
        if target_drive:
            target_drive = target_drive.upper().rstrip(':')
            if target_drive not in self.available_drives:
                return {
                    'success': False,
                    'error': f"Drive {target_drive}: not found"
                }
            
            drive_info = self.available_drives[target_drive]
            sufficient_space = drive_info['free_gb'] > (total_size_gb + self.min_free_space_gb)
            
            return {
                'success': sufficient_space,
                'target_drive': target_drive,
                'required_gb': total_size_gb,
                'available_gb': drive_info['free_gb'],
                'after_operation_free_gb': drive_info['free_gb'] - total_size_gb,
                'warning': None if sufficient_space else f"Insufficient space on {target_drive}:"
            }
        else:
            # Check all drives and find best option
            viable_drives = []
            for letter, info in self.available_drives.items():
                if info['free_gb'] > (total_size_gb + self.min_free_space_gb):
                    viable_drives.append({
                        'drive': letter,
                        'free_gb': info['free_gb'],
                        'after_operation_free_gb': info['free_gb'] - total_size_gb
                    })
            
            return {
                'success': len(viable_drives) > 0,
                'required_gb': total_size_gb,
                'viable_drives': viable_drives,
                'warning': None if viable_drives else "No drive has sufficient space"
            }
    
    def get_storage_recommendations(self, 
                                   file_categories: Dict[str, List[Tuple[str, int]]]) -> Dict[str, Any]:
        """
        Get intelligent recommendations for storage organization.
        
        Args:
            file_categories: Dict mapping categories to list of (file_path, file_size)
            
        Returns:
            Recommendations dict with suggested drive assignments
        """
        recommendations = {
            'strategy_used': self.strategy,
            'category_assignments': {},
            'space_savings': 0,
            'warnings': [],
            'optimizations': []
        }
        
        for category, files in file_categories.items():
            total_size = sum(size for _, size in files) / (1024**3)
            
            # Determine if this is archive content
            is_archive = 'archive' in category.lower() or 'old' in category.lower()
            
            # Get sample file for drive selection
            if files:
                sample_file, sample_size = files[0]
                target_drive, reasoning = self.select_target_drive(
                    sample_file, sample_size, category, is_archive
                )
                
                recommendations['category_assignments'][category] = {
                    'target_drive': target_drive,
                    'reasoning': reasoning,
                    'total_files': len(files),
                    'total_size_gb': total_size,
                    'is_archive': is_archive
                }
        
        # Generate optimization suggestions
        self._generate_optimizations(recommendations)
        
        return recommendations
    
    def _generate_optimizations(self, recommendations: Dict[str, Any]):
        """Generate storage optimization suggestions"""
        
        # Check if system drive (C:) is getting full
        if 'C' in self.available_drives:
            c_drive = self.available_drives['C']
            if c_drive['used_percent'] > 80:
                recommendations['warnings'].append(
                    f"System drive (C:) is {c_drive['used_percent']:.1f}% full. "
                    f"Consider moving user files to another drive."
                )
                
                # Suggest moving to data drive with most space
                data_drives = {k: v for k, v in self.available_drives.items() 
                              if v['type'] == DriveType.DATA.value}
                if data_drives:
                    best_data_drive = max(data_drives.items(), 
                                        key=lambda x: x[1]['free_gb'])
                    recommendations['optimizations'].append(
                        f"Move non-system files to {best_data_drive[0]}: drive "
                        f"({best_data_drive[1]['free_gb']:.1f}GB available)"
                    )
        
        # Check for drives with low space
        for letter, info in self.available_drives.items():
            if info['free_gb'] < 20:  # Less than 20GB free
                recommendations['warnings'].append(
                    f"Drive {letter}: is low on space ({info['free_gb']:.1f}GB free). "
                    f"Consider archiving or moving files."
                )
        
        # Suggest archive drive separation
        if not self.archive_drive and len(self.available_drives) > 1:
            recommendations['optimizations'].append(
                "Consider designating a separate drive for archives/old files "
                "to keep active data drive organized."
            )
    
    def format_storage_summary(self) -> str:
        """
        Format a human-readable storage summary.
        
        Returns:
            Formatted string with storage information
        """
        lines = ["=" * 70, "STORAGE SUMMARY", "=" * 70, ""]
        
        for letter in sorted(self.available_drives.keys()):
            info = self.available_drives[letter]
            
            bar_length = 40
            used_bars = int((info['used_percent'] / 100) * bar_length)
            free_bars = bar_length - used_bars
            
            bar = "█" * used_bars + "░" * free_bars
            
            lines.append(f"Drive {letter}: ({info['type']})")
            lines.append(f"  [{bar}] {info['used_percent']:.1f}% used")
            lines.append(f"  Total: {info['total_gb']:.1f}GB  |  "
                        f"Used: {info['used_gb']:.1f}GB  |  "
                        f"Free: {info['free_gb']:.1f}GB")
            lines.append("")
        
        lines.append("=" * 70)
        lines.append(f"Storage Strategy: {self.strategy}")
        if self.preferred_drive:
            lines.append(f"Preferred Drive: {self.preferred_drive}:")
        if self.archive_drive:
            lines.append(f"Archive Drive: {self.archive_drive}:")
        lines.append("=" * 70)
        
        return "\n".join(lines)


def create_storage_manager(config=None) -> StorageManager:
    """
    Create a StorageManager instance.
    
    Args:
        config: Configuration object
        
    Returns:
        StorageManager instance
    """
    return StorageManager(config)


if __name__ == "__main__":
    # Test storage manager
    print("Testing Storage Manager...\n")
    
    class MockConfig:
        storage_strategy = "most_space"
        preferred_drive = None
        min_free_space_gb = 10
        archive_drive = None
    
    manager = StorageManager(MockConfig())
    
    # Print storage summary
    print(manager.format_storage_summary())
    
    # Test drive selection
    print("\nTEST 1: Select drive for 5GB video file")
    drive, reason = manager.select_target_drive(
        "C:\\Users\\Test\\video.mp4",
        5 * 1024**3,  # 5GB
        "Videos",
        False
    )
    print(f"Selected: {drive}:")
    print(f"Reason: {reason}")
    
    # Test space checking
    print("\nTEST 2: Check space for multiple files")
    test_files = [
        ("C:\\file1.pdf", 100 * 1024**2),  # 100MB
        ("C:\\file2.jpg", 50 * 1024**2),   # 50MB
        ("C:\\file3.mp4", 500 * 1024**2),  # 500MB
    ]
    result = manager.check_space_requirements(test_files)
    print(f"Success: {result['success']}")
    print(f"Required: {result['required_gb']:.2f}GB")
    if 'viable_drives' in result:
        print(f"Viable drives: {[d['drive'] for d in result['viable_drives']]}")
