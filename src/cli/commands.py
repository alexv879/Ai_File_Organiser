"""
AI File Organiser - Main CLI Commands

Intent-driven CLI with 6 core commands.

Copyright © 2025 Alexandru Emanuel Vasile. All Rights Reserved.
"""

import click
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.cli.helpers import (
    print_header, print_success, print_error, print_warning, print_info
)
from src.cli.intent_detector import IntentDetector


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """
    AI File Organiser - Intelligent file organization powered by local AI

    Common Commands:
      aifo space      - Free up disk space (duplicates, large old files)
      aifo organize   - Organize files intelligently
      aifo find       - Find duplicate files
      aifo scan       - Quick folder inventory
      aifo stats      - Show organization statistics
      aifo ask        - Ask what you want in natural language

    Examples:
      aifo space --duplicates    # Find and remove duplicates
      aifo organize              # Organize Downloads folder
      aifo find --delete         # Find and delete duplicates
      aifo ask "free up space"   # Natural language query

    For help on specific command:
      aifo COMMAND --help
    """
    pass


@cli.command()
@click.option('--analyze', '-a', is_flag=True, help='Analyze what\'s using space')
@click.option('--duplicates', '-d', is_flag=True, help='Find and remove duplicates')
@click.option('--large-old', '-l', is_flag=True, help='Find large old files')
@click.option('--migrate', '-m', type=click.Path(), help='Migrate to drive (e.g., D:)')
@click.option('--auto', is_flag=True, help='Auto-approve safe actions')
def space(analyze, duplicates, large_old, migrate, auto):
    """
    Free up disk space on C: drive

    Examples:
      aifo space                  # Interactive menu
      aifo space --duplicates     # Find and remove duplicates
      aifo space --large-old      # Find large old files
      aifo space --analyze        # Full space analysis
      aifo space --migrate D:     # Move files to D:
    """
    from src.cli.space_manager import SpaceManager

    manager = SpaceManager()

    # If no options specified, show interactive menu
    if not any([analyze, duplicates, large_old, migrate]):
        manager.interactive_menu(auto)
        return

    # Execute specific actions
    if analyze:
        manager.analyze_space()

    if duplicates:
        manager.find_duplicates(auto)

    if large_old:
        manager.find_large_old_files(auto)

    if migrate:
        manager.migrate_to_drive(migrate, auto)


@cli.command()
@click.argument('folder', type=click.Path(exists=True), required=False)
@click.option('--preview', '-p', is_flag=True, help='Preview changes (dry run)')
@click.option('--auto', '-a', is_flag=True, help='Auto-approve (skip confirmation)')
@click.option('--deep', '-d', is_flag=True, help='Deep AI analysis (slower, better)')
def organize(folder, preview, auto, deep):
    """
    Organize files intelligently

    Examples:
      aifo organize                # Organize Downloads
      aifo organize ~/Documents    # Organize specific folder
      aifo organize -p             # Preview first
      aifo organize -a             # Auto-approve
      aifo organize -d ~/Pictures  # Deep AI for photos
    """
    from src.cli.organizer import Organizer

    org = Organizer()
    org.organize_folder(folder, preview, auto, deep)


@cli.command()
@click.argument('folder', type=click.Path(exists=True), required=False)
@click.option('--delete', '-d', is_flag=True, help='Delete duplicates (keeps newest)')
@click.option('--min-size', '-s', default='1MB', help='Minimum file size')
def find(folder, delete, min_size):
    """
    Find duplicate files

    Examples:
      aifo find                 # Find in Downloads
      aifo find ~/Pictures      # Find in Pictures
      aifo find -d              # Find and delete
      aifo find -s 10MB         # Only files >10MB
    """
    from src.cli.duplicate_finder import DuplicateFinder

    finder = DuplicateFinder()
    finder.find_duplicates(folder, delete, min_size)


@cli.command()
@click.argument('folder', type=click.Path(exists=True), required=False)
@click.option('--detailed', '-d', is_flag=True, help='Detailed breakdown')
def scan(folder, detailed):
    """
    Quick folder inventory

    Examples:
      aifo scan              # Scan Downloads
      aifo scan ~/Documents  # Scan Documents
      aifo scan -d           # Detailed breakdown
    """
    from src.cli.scanner import Scanner

    scanner = Scanner()
    scanner.scan_folder(folder, detailed)


@cli.command()
def stats():
    """
    Show organization statistics

    Example:
      aifo stats    # Show all-time stats
    """
    from src.cli.stats_viewer import StatsViewer

    viewer = StatsViewer()
    viewer.show_stats()


@cli.command()
@click.argument('query', nargs=-1)
def ask(query):
    """
    Ask what you want in natural language

    Examples:
      aifo ask "I need to free up space on C drive"
      aifo ask "organize my photos"
      aifo ask "find duplicate files"
    """
    detector = IntentDetector()

    # Join query arguments
    query_str = ' '.join(query)

    # If no query provided, prompt user
    if not query_str:
        query_str = click.prompt("What would you like to do?")

    # Detect intent
    result = detector.detect_and_suggest(query_str)

    print_header(f"🤔 {detector.format_intent_name(result['intent'])}")

    click.echo(f"\nYour query: \"{result['query']}\"")
    click.echo(f"Confidence: {result['confidence']*100:.0f}%\n")

    suggestions = result['suggestions']

    if not suggestions:
        print_warning("I'm not sure what you want to do.")
        click.echo("\nTry one of these commands:")
        click.echo("  aifo space      - Free up disk space")
        click.echo("  aifo organize   - Organize files")
        click.echo("  aifo find       - Find duplicates")
        click.echo("  aifo scan       - Quick inventory")
        click.echo("  aifo stats      - Show statistics")
        return

    click.echo("Here's what I can do:\n")

    for i, suggestion in enumerate(suggestions, 1):
        click.echo(f"{i}. {suggestion['description']}")
        click.echo(f"   Command: {suggestion['command']}")
        click.echo(f"   Impact: {suggestion['impact']}\n")

    # Ask user to choose
    if click.confirm("\nWould you like to run one of these?", default=True):
        choice = click.prompt(
            "Enter number",
            type=click.IntRange(1, len(suggestions)),
            default=1
        )

        selected = suggestions[choice - 1]
        command = selected['command']

        click.echo(f"\nRunning: {command}")
        click.echo("─" * 60)

        # Parse and execute command
        # Remove 'aifo ' prefix if present
        if command.startswith('aifo '):
            command = command[5:]

        # Re-invoke CLI with parsed command
        try:
            cli(command.split(), standalone_mode=False)
        except Exception as e:
            print_error(f"Error executing command: {str(e)}")


if __name__ == '__main__':
    cli()
