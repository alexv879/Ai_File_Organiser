"""
AI File Organiser - CLI Helper Functions

Utility functions for formatting, parsing, and common CLI operations.

Copyright © 2025 Alexandru Emanuel Vasile. All Rights Reserved.
"""

import shutil
from pathlib import Path
from typing import Tuple, Dict, List, Union
import click


def parse_size(size_str: str) -> int:
    """
    Parse '1MB', '100KB', '1GB' to bytes

    Args:
        size_str: Size string like '1MB', '100KB', '1GB'

    Returns:
        Size in bytes

    Examples:
        >>> parse_size('1MB')
        1048576
        >>> parse_size('100KB')
        102400
    """
    size_str = size_str.upper().strip()

    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4
    }

    for unit, multiplier in units.items():
        if size_str.endswith(unit):
            try:
                value = float(size_str[:-len(unit)])
                return int(value * multiplier)
            except ValueError:
                raise ValueError(f"Invalid size format: {size_str}")

    # Try parsing as plain number (bytes)
    try:
        return int(size_str)
    except ValueError:
        raise ValueError(f"Invalid size format: {size_str}")


def format_size(bytes_val: Union[int, float]) -> str:
    """
    Format bytes to human readable

    Args:
        bytes_val: Size in bytes

    Returns:
        Human-readable size string

    Examples:
        >>> format_size(1048576)
        '1.0 MB'
        >>> format_size(1500)
        '1.5 KB'
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"


def calculate_folder_size(path: Path) -> int:
    """
    Calculate total size of all files in folder

    Args:
        path: Path to folder

    Returns:
        Total size in bytes
    """
    total = 0
    try:
        for file_path in path.rglob('*'):
            if file_path.is_file():
                try:
                    total += file_path.stat().st_size
                except (OSError, PermissionError):
                    continue
    except (OSError, PermissionError):
        pass

    return total


def get_disk_usage(drive: str) -> Tuple[int, int, int]:
    """
    Get total, used, free space for drive

    Args:
        drive: Drive path (e.g., 'C:\\' or '/home')

    Returns:
        Tuple of (total, used, free) in bytes
    """
    try:
        usage = shutil.disk_usage(drive)
        return usage.total, usage.used, usage.free
    except Exception:
        return 0, 0, 0


def get_user_folders() -> Dict[str, Path]:
    """
    Get standard user folders

    Returns:
        Dict mapping folder name to Path
    """
    home = Path.home()

    folders = {
        'Downloads': home / 'Downloads',
        'Documents': home / 'Documents',
        'Pictures': home / 'Pictures',
        'Videos': home / 'Videos',
        'Desktop': home / 'Desktop',
        'Music': home / 'Music'
    }

    # Filter to only existing folders
    return {name: path for name, path in folders.items() if path.exists()}


def format_file_list(files: List[Dict], limit: int = 10) -> str:
    """
    Format file list for display

    Args:
        files: List of file dicts with 'path' and 'size' keys
        limit: Maximum files to show

    Returns:
        Formatted string
    """
    lines = []

    for i, file_info in enumerate(files[:limit]):
        path = file_info.get('path', 'Unknown')
        size = file_info.get('size', 0)

        lines.append(f"  {i+1}. {path} ({format_size(size)})")

    if len(files) > limit:
        remaining = len(files) - limit
        lines.append(f"  ... and {remaining} more files")

    return '\n'.join(lines)


def print_header(text: str):
    """Print a formatted header"""
    click.echo(f"\n{text}")
    click.echo("=" * 60)


def print_success(text: str):
    """Print success message"""
    click.echo(f"✅ {text}")


def print_warning(text: str):
    """Print warning message"""
    click.echo(f"⚠️  {text}")


def print_error(text: str):
    """Print error message"""
    click.echo(f"❌ {text}")


def print_info(text: str):
    """Print info message"""
    click.echo(f"ℹ️  {text}")


def confirm_action(message: str, default: bool = True) -> bool:
    """
    Ask for user confirmation

    Args:
        message: Confirmation message
        default: Default response

    Returns:
        True if user confirms, False otherwise
    """
    return click.confirm(message, default=default)


def get_default_folder() -> Path:
    """Get default folder (Downloads)"""
    downloads = Path.home() / 'Downloads'
    if downloads.exists():
        return downloads

    # Fallback to home directory
    return Path.home()


def validate_folder(folder_path: str) -> Path:
    """
    Validate and return folder path

    Args:
        folder_path: Path string

    Returns:
        Path object

    Raises:
        click.ClickException: If folder doesn't exist
    """
    path = Path(folder_path).expanduser()

    if not path.exists():
        raise click.ClickException(f"Folder does not exist: {folder_path}")

    if not path.is_dir():
        raise click.ClickException(f"Path is not a directory: {folder_path}")

    return path


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human readable

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def get_file_count(path: Path) -> int:
    """
    Count files in directory

    Args:
        path: Directory path

    Returns:
        Number of files
    """
    count = 0
    try:
        for _ in path.rglob('*'):
            if _.is_file():
                count += 1
    except (OSError, PermissionError):
        pass

    return count


def format_percentage(value: float, total: float) -> str:
    """
    Format percentage

    Args:
        value: Part value
        total: Total value

    Returns:
        Formatted percentage string
    """
    if total == 0:
        return "0%"

    percentage = (value / total) * 100
    return f"{percentage:.1f}%"
