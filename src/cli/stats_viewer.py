"""
Stats Viewer - Display organization statistics

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
"""

import sys
from pathlib import Path
import click

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cli.helpers import print_header, print_success, print_error, print_warning, print_info
from src.core.db_manager import DatabaseManager
from src.config import get_config


class StatsViewer:
    """Display organization statistics."""

    def __init__(self):
        """Initialize stats viewer."""
        self.config = get_config()
        self.db = DatabaseManager()

    def show_stats(self):
        """Show organization statistics."""
        print_header("📊 AI File Organiser Statistics")

        # Get all-time stats
        stats = self.db.get_stats('all')

        # Overview
        click.echo(f"\n{'='*70}")
        click.echo("ALL-TIME STATISTICS")
        click.echo(f"{'='*70}")

        files_organized = stats.get('files_organised', 0)
        time_saved_hours = stats.get('time_saved_hours', 0)
        ai_classifications = stats.get('ai_classifications', 0)
        duplicates_removed = stats.get('duplicates_removed', 0)

        click.echo(f"Files organized: {files_organized:,}")
        click.echo(f"Time saved: {time_saved_hours:.2f} hours ({time_saved_hours * 60:.0f} minutes)")
        click.echo(f"AI classifications: {ai_classifications:,}")
        click.echo(f"Duplicates removed: {duplicates_removed:,}")

        # Calculate efficiency metrics
        if files_organized > 0:
            avg_time_per_file = (time_saved_hours * 60) / files_organized
            click.echo(f"\nAverage time saved per file: {avg_time_per_file:.1f} minutes")

        # Get recent activity
        try:
            recent_logs = self.db.get_recent_logs(10)

            if recent_logs:
                click.echo(f"\n{'-'*70}")
                click.echo("RECENT ACTIVITY (Last 10 operations)")
                click.echo(f"{'-'*70}")

                for log in recent_logs:
                    filename = log.get('filename', 'Unknown')
                    operation = log.get('operation', 'Unknown')
                    category = log.get('category', 'N/A')
                    timestamp = log.get('timestamp', 'N/A')

                    # Format operation
                    op_icon = {
                        'move': '📁',
                        'rename': '✏️',
                        'delete': '🗑️',
                        'archive': '📦',
                    }.get(operation.lower(), '📄')

                    click.echo(f"\n{op_icon} {operation.upper()}: {filename}")
                    click.echo(f"   Category: {category}")
                    click.echo(f"   Time: {timestamp}")

        except Exception as e:
            print_warning(f"Could not load recent activity: {e}")

        # Category breakdown
        try:
            # Query database for category stats
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT category, COUNT(*) as count, SUM(time_saved) as total_time
                    FROM files_log
                    WHERE category IS NOT NULL
                    GROUP BY category
                    ORDER BY count DESC
                    LIMIT 10
                """)

                category_stats = cursor.fetchall()

                if category_stats:
                    click.echo(f"\n{'-'*70}")
                    click.echo("TOP CATEGORIES")
                    click.echo(f"{'-'*70}")
                    click.echo(f"{'Category':<20} {'Files':<12} {'Time Saved'}")
                    click.echo('-' * 70)

                    for category, count, total_time in category_stats:
                        time_minutes = (total_time or 0) * 60
                        click.echo(f"{category:<20} {count:<12} {time_minutes:.0f} minutes")

        except Exception as e:
            print_warning(f"Could not load category breakdown: {e}")

        # Operation breakdown
        try:
            cursor.execute("""
                SELECT operation, COUNT(*) as count
                FROM files_log
                GROUP BY operation
                ORDER BY count DESC
            """)

            operation_stats = cursor.fetchall()

            if operation_stats:
                click.echo(f"\n{'-'*70}")
                click.echo("OPERATIONS BREAKDOWN")
                click.echo(f"{'-'*70}")

                for operation, count in operation_stats:
                    percentage = (count / files_organized * 100) if files_organized > 0 else 0
                    bar = '█' * int(percentage / 2)
                    click.echo(f"{operation.upper():<15} {count:>6} {bar} {percentage:>5.1f}%")

        except Exception as e:
            print_warning(f"Could not load operation breakdown: {e}")

        # Weekly stats
        try:
            week_stats = self.db.get_stats('week')

            click.echo(f"\n{'-'*70}")
            click.echo("THIS WEEK")
            click.echo(f"{'-'*70}")

            week_files = week_stats.get('files_organised', 0)
            week_time = week_stats.get('time_saved_hours', 0)

            if week_files > 0:
                click.echo(f"Files organized: {week_files:,}")
                click.echo(f"Time saved: {week_time:.2f} hours ({week_time * 60:.0f} minutes)")
            else:
                click.echo("No activity this week")

        except Exception:
            pass

        # Daily stats
        try:
            day_stats = self.db.get_stats('day')

            click.echo(f"\n{'-'*70}")
            click.echo("TODAY")
            click.echo(f"{'-'*70}")

            day_files = day_stats.get('files_organised', 0)
            day_time = day_stats.get('time_saved_hours', 0)

            if day_files > 0:
                click.echo(f"Files organized: {day_files:,}")
                click.echo(f"Time saved: {day_time:.2f} hours ({day_time * 60:.0f} minutes)")
            else:
                click.echo("No activity today")

        except Exception:
            pass

        # Achievements/Milestones
        click.echo(f"\n{'-'*70}")
        click.echo("🏆 ACHIEVEMENTS")
        click.echo(f"{'-'*70}")

        achievements = []

        if files_organized >= 1000:
            achievements.append("🌟 Organized 1,000+ files!")
        elif files_organized >= 500:
            achievements.append("⭐ Organized 500+ files!")
        elif files_organized >= 100:
            achievements.append("✨ Organized 100+ files!")

        if time_saved_hours >= 10:
            achievements.append(f"⏰ Saved {time_saved_hours:.0f} hours of manual work!")
        elif time_saved_hours >= 5:
            achievements.append("⏱️ Saved 5+ hours of work!")

        if duplicates_removed >= 100:
            achievements.append("🗑️ Cleaned up 100+ duplicates!")
        elif duplicates_removed >= 50:
            achievements.append("🧹 Removed 50+ duplicates!")

        if ai_classifications >= 100:
            achievements.append("🤖 Used AI 100+ times!")

        if achievements:
            for achievement in achievements:
                click.echo(f"  {achievement}")
        else:
            click.echo("  Keep organizing to unlock achievements!")

        click.echo()
