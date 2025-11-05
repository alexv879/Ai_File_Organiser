"""
Space Manager - Free up disk space by finding duplicates and large old files

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any
import click

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cli.helpers import print_header, print_success, print_error, print_warning, print_info
from src.core.duplicates import DuplicateFinder
from src.core.db_manager import DatabaseManager
from src.config import get_config


class SpaceManager:
    """Manage disk space by finding duplicates and large old files."""

    def __init__(self):
        """Initialize space manager."""
        self.config = get_config()
        self.db = DatabaseManager()
        self.duplicate_finder = DuplicateFinder(self.config, self.db)

    def interactive_menu(self, auto: bool = False):
        """Show interactive menu for space management."""
        print_header("🗂️  Disk Space Management")

        click.echo("\nWhat would you like to do?\n")
        click.echo("1. Find and remove duplicate files")
        click.echo("2. Find large old files (>100MB, older than 30 days)")
        click.echo("3. Analyze what's using space")
        click.echo("4. Exit")

        choice = click.prompt("\nEnter your choice", type=click.IntRange(1, 4), default=1)

        if choice == 1:
            self.find_duplicates(auto)
        elif choice == 2:
            self.find_large_old_files(auto)
        elif choice == 3:
            self.analyze_space()
        else:
            click.echo("Goodbye!")

    def find_duplicates(self, auto: bool = False):
        """Find and optionally remove duplicate files."""
        print_header("🔍 Finding Duplicate Files")

        # Scan watched folders
        all_duplicates = []

        for folder in self.config.watched_folders:
            print_info(f"Scanning: {folder}")
            duplicates = self.duplicate_finder.find_duplicates_in_directory(folder, recursive=True)
            all_duplicates.extend(duplicates)

        if not all_duplicates:
            print_success("\n✅ No duplicates found!")
            return

        # Show summary
        summary = self.duplicate_finder.get_duplicate_summary(all_duplicates)

        click.echo(f"\n{'='*60}")
        click.echo("DUPLICATE FILES SUMMARY")
        click.echo(f"{'='*60}")
        click.echo(f"Duplicate groups: {summary['total_duplicate_groups']}")
        click.echo(f"Duplicate files: {summary['total_duplicate_files']}")
        click.echo(f"Wasted space: {summary['total_wasted_space_mb']:.2f} MB")
        click.echo(f"              ({summary['total_wasted_space_gb']:.2f} GB)")

        # Show top duplicates
        click.echo(f"\n{'-'*60}")
        click.echo("TOP 10 DUPLICATE GROUPS")
        click.echo(f"{'-'*60}")

        for i, group in enumerate(all_duplicates[:10], 1):
            click.echo(f"\n{i}. {group['count']} copies of same file ({group['size'] / (1024*1024):.2f} MB each)")
            for path in group['paths'][:3]:  # Show first 3
                click.echo(f"   - {path}")
            if len(group['paths']) > 3:
                click.echo(f"   ... and {len(group['paths']) - 3} more")

        # Ask to delete
        if auto or click.confirm(f"\n\nDelete duplicates? (keeps newest copy)", default=False):
            deleted_count = 0
            space_freed = 0

            for group in all_duplicates:
                # Keep the newest file, delete others
                paths_with_times = [(p, Path(p).stat().st_mtime) for p in group['paths'] if Path(p).exists()]
                if len(paths_with_times) <= 1:
                    continue

                # Sort by modification time (newest first)
                paths_with_times.sort(key=lambda x: x[1], reverse=True)
                keep_file = paths_with_times[0][0]

                # Delete older copies
                for file_path, _ in paths_with_times[1:]:
                    try:
                        file_size = Path(file_path).stat().st_size
                        Path(file_path).unlink()
                        deleted_count += 1
                        space_freed += file_size
                        click.echo(f"   Deleted: {file_path}")
                    except Exception as e:
                        print_error(f"   Failed to delete {file_path}: {e}")

            print_success(f"\n✅ Deleted {deleted_count} duplicate files")
            print_success(f"✅ Freed {space_freed / (1024*1024):.2f} MB ({space_freed / (1024*1024*1024):.2f} GB)")
        else:
            print_info("No files deleted.")

    def find_large_old_files(self, auto: bool = False):
        """Find large old files that might be safe to delete."""
        print_header("📦 Finding Large Old Files")

        min_size = 100 * 1024 * 1024  # 100 MB
        min_days_old = 30

        import time
        current_time = time.time()
        days_in_seconds = min_days_old * 24 * 60 * 60

        large_old_files = []

        for folder in self.config.watched_folders:
            print_info(f"Scanning: {folder}")

            folder_path = Path(folder)
            if not folder_path.exists():
                continue

            for file_path in folder_path.rglob('*'):
                if not file_path.is_file():
                    continue

                try:
                    stat_info = file_path.stat()
                    file_size = stat_info.st_size
                    file_age = current_time - stat_info.st_mtime

                    if file_size >= min_size and file_age >= days_in_seconds:
                        large_old_files.append({
                            'path': str(file_path),
                            'size': file_size,
                            'age_days': file_age / (24 * 60 * 60)
                        })
                except Exception:
                    continue

        if not large_old_files:
            print_success(f"\n✅ No large old files found (>100MB, >{min_days_old} days)")
            return

        # Sort by size (largest first)
        large_old_files.sort(key=lambda x: x['size'], reverse=True)

        total_size = sum(f['size'] for f in large_old_files)

        click.echo(f"\nFound {len(large_old_files)} large old files")
        click.echo(f"Total size: {total_size / (1024*1024):.2f} MB ({total_size / (1024*1024*1024):.2f} GB)")

        click.echo(f"\n{'-'*80}")
        click.echo("TOP 20 LARGE OLD FILES")
        click.echo(f"{'-'*80}")

        for i, file_info in enumerate(large_old_files[:20], 1):
            size_mb = file_info['size'] / (1024*1024)
            age = file_info['age_days']
            click.echo(f"{i}. {size_mb:.1f} MB | {age:.0f} days old")
            click.echo(f"   {file_info['path']}")

        if len(large_old_files) > 20:
            click.echo(f"\n... and {len(large_old_files) - 20} more files")

        # Note: Don't auto-delete these - too dangerous
        if not auto:
            print_warning("\n⚠️  Review these files manually before deleting.")
            print_info("Large old files are not auto-deleted for safety.")

    def analyze_space(self):
        """Analyze what's using disk space."""
        print_header("📊 Disk Space Analysis")

        # Analyze each watched folder
        for folder in self.config.watched_folders:
            folder_path = Path(folder)
            if not folder_path.exists():
                continue

            print_info(f"\nAnalyzing: {folder}")

            # Count files by category
            categories = {}
            total_size = 0
            total_files = 0

            for file_path in folder_path.rglob('*'):
                if not file_path.is_file():
                    continue

                try:
                    file_size = file_path.stat().st_size
                    total_size += file_size
                    total_files += 1

                    # Categorize by extension
                    ext = file_path.suffix.lower()
                    if not ext:
                        ext = 'no extension'

                    if ext not in categories:
                        categories[ext] = {'count': 0, 'size': 0}

                    categories[ext]['count'] += 1
                    categories[ext]['size'] += file_size
                except Exception:
                    continue

            # Sort by size
            sorted_categories = sorted(categories.items(), key=lambda x: x[1]['size'], reverse=True)

            click.echo(f"\nTotal: {total_files} files, {total_size / (1024*1024):.2f} MB")
            click.echo(f"\n{'Extension':<15} {'Count':<10} {'Size':<15} {'% of Total'}")
            click.echo('-' * 60)

            for ext, info in sorted_categories[:15]:
                count = info['count']
                size_mb = info['size'] / (1024*1024)
                percentage = (info['size'] / total_size * 100) if total_size > 0 else 0
                click.echo(f"{ext:<15} {count:<10} {size_mb:>10.2f} MB {percentage:>8.1f}%")

    def migrate_to_drive(self, target_drive: str, auto: bool = False):
        """Migrate files to another drive."""
        print_header(f"🚚 Migrate Files to {target_drive}")

        target_path = Path(target_drive)

        if not target_path.exists():
            print_error(f"Target drive {target_drive} not found or not accessible")
            return

        print_warning("Migration feature is coming soon!")
        print_info("For now, use the organize feature to move files to a different drive.")
