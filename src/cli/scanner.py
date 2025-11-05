"""
Scanner - Quick folder inventory and analysis

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
from collections import defaultdict
import click

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cli.helpers import print_header, print_success, print_error, print_warning, print_info
from src.config import get_config


class Scanner:
    """Quick folder scanner and analyzer."""

    def __init__(self):
        """Initialize scanner."""
        self.config = get_config()

    def scan_folder(self, folder: Optional[str] = None, detailed: bool = False):
        """
        Scan folder and show inventory.

        Args:
            folder: Folder to scan (default: first watched folder)
            detailed: Show detailed breakdown
        """
        # Determine folder
        if folder is None:
            if not self.config.watched_folders:
                print_error("No watched folders configured in config.json")
                return
            folder = self.config.watched_folders[0]

        folder_path = Path(folder).expanduser().resolve()

        if not folder_path.exists():
            print_error(f"Folder not found: {folder}")
            return

        if not folder_path.is_dir():
            print_error(f"Not a directory: {folder}")
            return

        print_header(f"📊 Scanning: {folder_path}")

        # Collect file information
        print_info("Analyzing files...")

        stats = {
            'total_files': 0,
            'total_size': 0,
            'by_extension': defaultdict(lambda: {'count': 0, 'size': 0}),
            'by_size_range': defaultdict(int),
            'by_age_range': defaultdict(int),
            'largest_files': [],
        }

        import time
        current_time = time.time()

        for file_path in folder_path.rglob('*'):
            if not file_path.is_file():
                continue

            try:
                stat_info = file_path.stat()
                file_size = stat_info.st_size
                file_age_days = (current_time - stat_info.st_mtime) / (24 * 60 * 60)

                stats['total_files'] += 1
                stats['total_size'] += file_size

                # By extension
                ext = file_path.suffix.lower() or 'no extension'
                stats['by_extension'][ext]['count'] += 1
                stats['by_extension'][ext]['size'] += file_size

                # By size range
                if file_size < 1024:
                    stats['by_size_range']['< 1 KB'] += 1
                elif file_size < 1024 * 1024:
                    stats['by_size_range']['1 KB - 1 MB'] += 1
                elif file_size < 10 * 1024 * 1024:
                    stats['by_size_range']['1 MB - 10 MB'] += 1
                elif file_size < 100 * 1024 * 1024:
                    stats['by_size_range']['10 MB - 100 MB'] += 1
                elif file_size < 1024 * 1024 * 1024:
                    stats['by_size_range']['100 MB - 1 GB'] += 1
                else:
                    stats['by_size_range']['> 1 GB'] += 1

                # By age
                if file_age_days < 7:
                    stats['by_age_range']['< 1 week'] += 1
                elif file_age_days < 30:
                    stats['by_age_range']['1 week - 1 month'] += 1
                elif file_age_days < 180:
                    stats['by_age_range']['1 month - 6 months'] += 1
                elif file_age_days < 365:
                    stats['by_age_range']['6 months - 1 year'] += 1
                else:
                    stats['by_age_range']['> 1 year'] += 1

                # Track largest files
                stats['largest_files'].append({
                    'path': str(file_path),
                    'size': file_size,
                    'age_days': file_age_days
                })

            except Exception:
                continue

        # Sort largest files
        stats['largest_files'].sort(key=lambda x: x['size'], reverse=True)
        stats['largest_files'] = stats['largest_files'][:20]

        # Display results
        self._display_stats(stats, detailed)

    def _display_stats(self, stats: Dict[str, Any], detailed: bool):
        """Display scan statistics."""

        total_files = stats['total_files']
        total_size = stats['total_size']

        if total_files == 0:
            print_success("\n✅ Folder is empty")
            return

        # Overview
        click.echo(f"\n{'='*70}")
        click.echo("FOLDER OVERVIEW")
        click.echo(f"{'='*70}")
        click.echo(f"Total files: {total_files:,}")
        click.echo(f"Total size: {total_size / (1024*1024):.2f} MB ({total_size / (1024*1024*1024):.2f} GB)")

        # By extension
        click.echo(f"\n{'-'*70}")
        click.echo("TOP FILE TYPES")
        click.echo(f"{'-'*70}")
        click.echo(f"{'Extension':<20} {'Count':<12} {'Size':<15} {'% of Total'}")
        click.echo('-' * 70)

        sorted_ext = sorted(
            stats['by_extension'].items(),
            key=lambda x: x[1]['size'],
            reverse=True
        )

        for ext, info in sorted_ext[:15]:
            count = info['count']
            size_mb = info['size'] / (1024*1024)
            percentage = (info['size'] / total_size * 100) if total_size > 0 else 0
            click.echo(f"{ext:<20} {count:<12} {size_mb:>10.2f} MB {percentage:>8.1f}%")

        if len(sorted_ext) > 15:
            click.echo(f"\n... and {len(sorted_ext) - 15} more file types")

        # Size distribution
        if detailed:
            click.echo(f"\n{'-'*70}")
            click.echo("FILE SIZE DISTRIBUTION")
            click.echo(f"{'-'*70}")

            size_order = ['< 1 KB', '1 KB - 1 MB', '1 MB - 10 MB', '10 MB - 100 MB', '100 MB - 1 GB', '> 1 GB']
            for size_range in size_order:
                count = stats['by_size_range'].get(size_range, 0)
                percentage = (count / total_files * 100) if total_files > 0 else 0
                bar = '█' * int(percentage / 2)
                click.echo(f"{size_range:<20} {count:>6} files {bar} {percentage:>5.1f}%")

            # Age distribution
            click.echo(f"\n{'-'*70}")
            click.echo("FILE AGE DISTRIBUTION")
            click.echo(f"{'-'*70}")

            age_order = ['< 1 week', '1 week - 1 month', '1 month - 6 months', '6 months - 1 year', '> 1 year']
            for age_range in age_order:
                count = stats['by_age_range'].get(age_range, 0)
                percentage = (count / total_files * 100) if total_files > 0 else 0
                bar = '█' * int(percentage / 2)
                click.echo(f"{age_range:<20} {count:>6} files {bar} {percentage:>5.1f}%")

        # Largest files
        click.echo(f"\n{'-'*70}")
        click.echo("LARGEST FILES")
        click.echo(f"{'-'*70}")

        for i, file_info in enumerate(stats['largest_files'][:10], 1):
            size_mb = file_info['size'] / (1024*1024)
            age = file_info['age_days']
            click.echo(f"{i}. {size_mb:.1f} MB | {age:.0f} days old")
            click.echo(f"   {file_info['path']}")

        # Recommendations
        click.echo(f"\n{'-'*70}")
        click.echo("💡 RECOMMENDATIONS")
        click.echo(f"{'-'*70}")

        # Check for duplicates potential
        if total_files > 100:
            print_info("✓ Run 'aifo find' to check for duplicate files")

        # Check for large old files
        large_old_count = sum(
            1 for f in stats['largest_files']
            if f['size'] > 100 * 1024 * 1024 and f['age_days'] > 30
        )
        if large_old_count > 0:
            print_info(f"✓ Found {large_old_count} large old files (>100MB, >30 days)")
            print_info("  Run 'aifo space --large-old' to review them")

        # Check for organization potential
        if total_files > 50:
            print_info("✓ Run 'aifo organize' to organize these files")

        click.echo()
