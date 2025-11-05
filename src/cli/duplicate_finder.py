"""
Duplicate Finder - Find and manage duplicate files

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
"""

import sys
from pathlib import Path
from typing import Optional
import click

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cli.helpers import print_header, print_success, print_error, print_warning, print_info
from src.core.duplicates import DuplicateFinder as CoreDuplicateFinder
from src.core.db_manager import DatabaseManager
from src.config import get_config


class DuplicateFinder:
    """CLI wrapper for duplicate finder."""

    def __init__(self):
        """Initialize duplicate finder."""
        self.config = get_config()
        self.db = DatabaseManager()
        self.finder = CoreDuplicateFinder(self.config, self.db)

    def find_duplicates(self, folder: Optional[str] = None, delete: bool = False, min_size: str = '1MB'):
        """
        Find duplicate files in a folder.

        Args:
            folder: Folder to scan (default: watched folders)
            delete: Delete duplicates (keeps newest)
            min_size: Minimum file size (e.g., '1MB', '10MB')
        """
        # Parse min_size
        min_bytes = self._parse_size(min_size)

        # Determine folders to scan
        if folder:
            folders = [Path(folder).expanduser().resolve()]
        else:
            folders = [Path(f).expanduser().resolve() for f in self.config.watched_folders]

        print_header("🔍 Finding Duplicate Files")

        if min_bytes > 0:
            print_info(f"Minimum file size: {min_size}")

        # Scan folders
        all_duplicates = []

        for folder_path in folders:
            if not folder_path.exists():
                print_warning(f"Folder not found: {folder_path}")
                continue

            print_info(f"\nScanning: {folder_path}")

            duplicates = self.finder.find_duplicates_in_directory(
                str(folder_path),
                recursive=True
            )

            # Filter by size
            if min_bytes > 0:
                duplicates = [d for d in duplicates if d['size'] >= min_bytes]

            all_duplicates.extend(duplicates)

        if not all_duplicates:
            print_success("\n✅ No duplicates found!")
            return

        # Filter for safety
        safe_duplicates, protected_groups_count, _protected_files_count = self.finder.filter_protected_duplicates(all_duplicates)

        if protected_groups_count:
            print_warning(f"\n⚠️  Protected {protected_groups_count} groups from deletion (system/app files)")

        # Show summary
        summary = self.finder.get_duplicate_summary(safe_duplicates)

        click.echo(f"\n{'='*70}")
        click.echo("DUPLICATE FILES SUMMARY")
        click.echo(f"{'='*70}")
        click.echo(f"Duplicate groups: {summary['total_duplicate_groups']}")
        click.echo(f"Duplicate files: {summary['total_duplicate_files']}")
        click.echo(f"Wasted space: {summary['total_wasted_space_mb']:.2f} MB ({summary['total_wasted_space_gb']:.2f} GB)")

        # Show top duplicates
        click.echo(f"\n{'-'*70}")
        click.echo("TOP 15 DUPLICATE GROUPS")
        click.echo(f"{'-'*70}")

        for i, group in enumerate(safe_duplicates[:15], 1):
            size_mb = group['size'] / (1024*1024)
            wasted_mb = (group['size'] * (group['count'] - 1)) / (1024*1024)

            click.echo(f"\n{i}. {group['count']} copies ({size_mb:.2f} MB each, wasting {wasted_mb:.2f} MB)")

            # Show up to 5 paths
            for path in group['paths'][:5]:
                click.echo(f"   - {path}")

            if len(group['paths']) > 5:
                click.echo(f"   ... and {len(group['paths']) - 5} more")

        if len(safe_duplicates) > 15:
            remaining = len(safe_duplicates) - 15
            remaining_wasted = sum(
                (g['size'] * (g['count'] - 1)) for g in safe_duplicates[15:]
            ) / (1024*1024)
            click.echo(f"\n... and {remaining} more groups (wasting {remaining_wasted:.2f} MB)")

        # Delete if requested
        if delete:
            click.echo()
            if not click.confirm("Delete duplicate files? (keeps newest copy)", default=False):
                print_info("Cancelled.")
                return

            print_info("\nDeleting duplicates...")

            deleted_count = 0
            space_freed = 0
            errors = []

            for group in safe_duplicates:
                # Get file paths with modification times
                paths_with_times = []
                for path in group['paths']:
                    path_obj = Path(path)
                    if path_obj.exists():
                        try:
                            mtime = path_obj.stat().st_mtime
                            paths_with_times.append((path, mtime))
                        except Exception:
                            continue

                if len(paths_with_times) <= 1:
                    continue

                # Sort by modification time (newest first)
                paths_with_times.sort(key=lambda x: x[1], reverse=True)

                # Keep newest, delete others
                keep_file = paths_with_times[0][0]

                for file_path, _ in paths_with_times[1:]:
                    try:
                        file_obj = Path(file_path)
                        file_size = file_obj.stat().st_size
                        file_obj.unlink()

                        deleted_count += 1
                        space_freed += file_size

                        click.echo(f"✓ Deleted: {file_path}")

                    except Exception as e:
                        errors.append(f"{file_path}: {str(e)}")

            # Final summary
            click.echo(f"\n{'='*70}")
            click.echo("DELETION COMPLETE")
            click.echo(f"{'='*70}")

            print_success(f"✅ Deleted: {deleted_count} files")
            print_success(f"✅ Freed: {space_freed / (1024*1024):.2f} MB ({space_freed / (1024*1024*1024):.2f} GB)")

            if errors:
                print_error(f"\n❌ Errors: {len(errors)} files")
                for error in errors[:5]:
                    click.echo(f"   {error}")
                if len(errors) > 5:
                    click.echo(f"   ... and {len(errors) - 5} more errors")

        else:
            click.echo()
            print_info("💡 Tip: Use --delete flag to remove duplicates")

    def _parse_size(self, size_str: str) -> int:
        """
        Parse size string to bytes.

        Args:
            size_str: Size string (e.g., '1MB', '10GB', '500KB')

        Returns:
            Size in bytes
        """
        size_str = size_str.upper().strip()

        # Extract number and unit
        import re
        match = re.match(r'(\d+(?:\.\d+)?)\s*([KMGT]?B?)', size_str)

        if not match:
            return 0

        number = float(match.group(1))
        unit = match.group(2)

        multipliers = {
            '': 1,
            'B': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024,
            'TB': 1024 * 1024 * 1024 * 1024,
        }

        return int(number * multipliers.get(unit, 1))
