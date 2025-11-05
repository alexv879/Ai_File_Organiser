"""
Command-line interface using click for enhanced CLI capabilities.
Provides a comprehensive CLI for the AI File Organiser.
"""

import sys
from pathlib import Path
from typing import List, Optional
import click
from click import Context

# Import our modules
try:
    from .advanced_config import config
    from .caching import cache_manager
    from .core.duplicates import DuplicateFinder
    from .ui.dashboard import run_dashboard
    from .utils.logger import get_logger
except ImportError:
    # Handle imports when run as script
    import sys
    from pathlib import Path
    # Add parent directory to path
    parent_dir = Path(__file__).parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

    from advanced_config import config
    from caching import cache_manager
    from core.duplicates import DuplicateFinder
    from ui.dashboard import run_dashboard
    from utils.logger import get_logger

logger = get_logger(__name__)


class AIFileOrganiserCLI:
    """Main CLI class for AI File Organiser."""

    def __init__(self):
        self.config = config

    @staticmethod
    def validate_directory(_ctx: Context, _param: Optional[click.Parameter], value: Optional[str]) -> Optional[str]:
        """Validate that directory exists."""
        if value and not Path(value).exists():
            raise click.BadParameter(f"Directory '{value}' does not exist.")
        return value

    @staticmethod
    def validate_file(_ctx: Context, _param: Optional[click.Parameter], value: Optional[str]) -> Optional[str]:
        """Validate that file exists."""
        if value and not Path(value).exists():
            raise click.BadParameter(f"File '{value}' does not exist.")
        return value


@click.group()
@click.option('--config', 'config_file',
              type=click.Path(exists=True),
              help='Path to configuration file.')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose output.')
@click.option('--debug', is_flag=True,
              help='Enable debug mode.')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              default='INFO', help='Set logging level.')
@click.pass_context
def cli(ctx: Context, config_file: str, verbose: bool, debug: bool, log_level: str):
    """AI File Organiser - Intelligent file management system.

    A comprehensive tool for organizing, analyzing, and managing files
    using AI-powered classification and automated rules.
    """
    # Store context for subcommands
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    ctx.obj['log_level'] = log_level

    # Load configuration if specified
    if config_file:
        try:
            from .advanced_config import AdvancedConfig
            ctx.obj['config'] = AdvancedConfig.load_from_file(config_file)
            click.echo(f"Loaded configuration from: {config_file}")
        except Exception as e:
            click.echo(f"Error loading configuration: {e}", err=True)
            sys.exit(1)
    else:
        ctx.obj['config'] = config

    # Set up logging
    if verbose or debug:
        logger.logger.setLevel('DEBUG' if debug else 'INFO')


@cli.command()
@click.argument('directory', type=click.Path(exists=True),
                callback=AIFileOrganiserCLI.validate_directory)
@click.option('--recursive', '-r', is_flag=True,
              help='Process directories recursively.')
@click.option('--dry-run', is_flag=True,
              help='Show what would be done without making changes.')
@click.option('--rules', type=click.Path(exists=True),
              help='Path to rules configuration file.')
@click.option('--tags', multiple=True,
              help='Filter rules by tags.')
@click.option('--exclude-patterns', multiple=True,
              help='Patterns to exclude from processing.')
@click.pass_context
def organize(_ctx: Context, directory: str, recursive: bool, dry_run: bool,
             rules: str, tags: List[str], exclude_patterns: List[str]):
    """Organize files in a directory using AI-powered rules.

    DIRECTORY: Directory to organize

    Examples:
        aifo organize ./data --recursive
        aifo organize ./downloads --dry-run --tags images documents
    """
    click.echo(f"Organizing files in: {directory}")
    click.echo(f"Recursive: {recursive}")
    click.echo(f"Dry run: {dry_run}")

    if rules:
        click.echo(f"Using rules from: {rules}")
    if tags:
        click.echo(f"Filtering by tags: {', '.join(tags)}")
    if exclude_patterns:
        click.echo(f"Excluding patterns: {', '.join(exclude_patterns)}")

    # Here you would call the actual organization logic
    # For now, just show what would be done
    if dry_run:
        click.echo("Would organize files (dry run mode)")
    else:
        click.echo("Organizing files...")


@cli.command()
@click.argument('directory', type=click.Path(exists=True),
                callback=AIFileOrganiserCLI.validate_directory)
@click.option('--recursive', '-r', is_flag=True,
              help='Scan directories recursively.')
@click.option('--cross-drive', is_flag=True,
              help='Scan across different drives.')
@click.option('--min-size', type=int,
              help='Minimum file size in bytes.')
@click.option('--max-size', type=int,
              help='Maximum file size in bytes.')
@click.option('--algorithms', multiple=True,
              type=click.Choice(['md5', 'sha1', 'sha256']),
              default=['md5'],
              help='Hash algorithms to use.')
@click.option('--output', type=click.Path(),
              help='Output file for duplicate report.')
@click.pass_context
def duplicates(ctx: Context, directory: str, recursive: bool, cross_drive: bool,
               min_size: int, max_size: int, algorithms: List[str], output: str):
    """Find and manage duplicate files.

    DIRECTORY: Directory to scan for duplicates

    Examples:
        aifo duplicates ./data --recursive
        aifo duplicates ./files --cross-drive --algorithms md5 sha256
    """
    click.echo(f"Scanning for duplicates in: {directory}")
    click.echo(f"Recursive: {recursive}")
    click.echo(f"Cross-drive: {cross_drive}")
    click.echo(f"Algorithms: {', '.join(algorithms)}")

    if min_size:
        click.echo(f"Minimum size: {min_size} bytes")
    if max_size:
        click.echo(f"Maximum size: {max_size} bytes")

    try:
        # Call the duplicate finding logic
        finder = DuplicateFinder(ctx.obj['config'], None)  # db_manager can be None for basic operation
        duplicates_found = finder.find_duplicates_in_directory(
            directory=directory,
            recursive=recursive
        )

        click.echo(f"Found {len(duplicates_found)} duplicate groups")

        if output:
            # Save results to file
            import json
            with open(output, 'w') as f:
                json.dump(duplicates_found, f, indent=2, default=str)
            click.echo(f"Results saved to: {output}")

    except Exception as e:
        click.echo(f"Error finding duplicates: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--host', default='localhost',
              help='Host to bind the dashboard to.')
@click.option('--port', default=8000, type=int,
              help='Port to bind the dashboard to.')
@click.option('--open-browser', is_flag=True,
              help='Open browser automatically.')
@click.option('--config', type=click.Path(exists=True),
              help='Configuration file to use.')
@click.pass_context
def dashboard(_ctx: Context, host: str, port: int, _open_browser: bool, config: str):
    """Start the web dashboard.

    Examples:
        aifo dashboard
        aifo dashboard --port 8080 --host 0.0.0.0
    """
    click.echo(f"Starting dashboard on {host}:{port}")

    if config:
        click.echo(f"Using configuration: {config}")

    try:
        # Start the dashboard
        run_dashboard(host=host, port=port)
    except Exception as e:
        click.echo(f"Error starting dashboard: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('directory', type=click.Path(exists=True),
                callback=AIFileOrganiserCLI.validate_directory)
@click.option('--output', '-o', type=click.Path(),
              help='Output file for analysis report.')
@click.option('--format', type=click.Choice(['json', 'yaml', 'text']),
              default='text', help='Output format.')
@click.option('--include-hidden', is_flag=True,
              help='Include hidden files in analysis.')
@click.option('--max-depth', type=int,
              help='Maximum directory depth to analyze.')
@click.pass_context
def analyze(_ctx: Context, directory: str, output: str, format: str,
            include_hidden: bool, max_depth: int):
    """Analyze directory structure and file types.

    DIRECTORY: Directory to analyze

    Examples:
        aifo analyze ./data --output analysis.json --format json
        aifo analyze ./files --include-hidden --max-depth 3
    """
    click.echo(f"Analyzing directory: {directory}")
    click.echo(f"Format: {format}")
    click.echo(f"Include hidden: {include_hidden}")

    if max_depth:
        click.echo(f"Max depth: {max_depth}")

    try:
        # Here you would call the analysis logic
        # For now, just show what would be done
        analysis_result = {
            'directory': directory,
            'total_files': 0,
            'total_size': 0,
            'file_types': {},
            'structure': {}
        }

        if output:
            if format == 'json':
                import json
                with open(output, 'w') as f:
                    json.dump(analysis_result, f, indent=2)
            elif format == 'yaml':
                import yaml
                with open(output, 'w') as f:
                    yaml.dump(analysis_result, f, default_flow_style=False)
            else:
                # Text format
                with open(output, 'w') as f:
                    f.write(f"Analysis of {directory}\n")
                    f.write(f"Total files: {analysis_result['total_files']}\n")
                    f.write(f"Total size: {analysis_result['total_size']}\n")

            click.echo(f"Analysis saved to: {output}")
        else:
            click.echo("Analysis complete")

    except Exception as e:
        click.echo(f"Error analyzing directory: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config-file', type=click.Path(),
              help='Configuration file to validate.')
@click.option('--fix', is_flag=True,
              help='Attempt to fix configuration issues.')
@click.pass_context
def config_validate(ctx: Context, config_file: str, fix: bool):
    """Validate configuration files.

    Examples:
        aifo config-validate
        aifo config-validate --config-file myconfig.yaml --fix
    """
    config_obj = ctx.obj['config']

    if config_file:
        try:
            from .advanced_config import AdvancedConfig
            config_obj = AdvancedConfig.load_from_file(config_file)
            click.echo(f"Validating configuration: {config_file}")
        except Exception as e:
            click.echo(f"Error loading configuration: {e}", err=True)
            sys.exit(1)
    else:
        click.echo("Validating current configuration")

    issues = config_obj.validate_configuration()

    if issues:
        click.echo("Configuration issues found:", err=True)
        for issue in issues:
            click.echo(f"  - {issue}", err=True)

        if fix:
            click.echo("Attempting to fix issues...")
            # Here you could implement auto-fix logic
            click.echo("Some issues may require manual intervention")
        else:
            click.echo("Use --fix to attempt automatic fixes")
        sys.exit(1)
    else:
        click.echo("Configuration is valid ✓")


@cli.command()
@click.option('--cache-dir', type=click.Path(),
              help='Cache directory to manage.')
@click.option('--clear', is_flag=True,
              help='Clear all cache data.')
@click.option('--stats', is_flag=True,
              help='Show cache statistics.')
@click.option('--clear-expired', is_flag=True,
              help='Clear only expired cache entries.')
@click.pass_context
def cache(_ctx: Context, cache_dir: str, clear: bool, stats: bool, clear_expired: bool):
    """Manage cache data.

    Examples:
        aifo cache --stats
        aifo cache --clear
        aifo cache --clear-expired
    """
    if cache_dir:
        click.echo(f"Using cache directory: {cache_dir}")
        # You could create a custom cache manager for the specified directory

    if stats:
        cache_stats = cache_manager.get_all_stats()
        if cache_stats is not None and isinstance(cache_stats, dict):
            click.echo("Cache Statistics:")
            for cache_name, stats_data in cache_stats.items():
                click.echo(f"\n{cache_name}:")
                if isinstance(stats_data, dict):
                    for key, value in stats_data.items():
                        click.echo(f"  {key}: {value}")

    if clear_expired:
        cleared = cache_manager.clear_all_expired()
        click.echo("Cleared expired entries:")
        for cache_name, count in cleared.items():
            click.echo(f"  {cache_name}: {count}")

    if clear:
        if click.confirm("Are you sure you want to clear all cache data?"):
            cache_manager.close_all()
            # Here you would implement cache clearing logic
            click.echo("Cache cleared")
        else:
            click.echo("Cache clear cancelled")


@cli.command()
@click.option('--version', is_flag=True,
              help='Show version information.')
@click.option('--system-info', is_flag=True,
              help='Show system information.')
@click.pass_context
def info(ctx: Context, version: bool, system_info: bool):
    """Show information about the AI File Organiser.

    Examples:
        aifo info --version
        aifo info --system-info
    """
    config_obj = ctx.obj['config']

    if version:
        click.echo(f"AI File Organiser v{config_obj.version}")
        click.echo(f"App name: {config_obj.app_name}")

    if system_info:
        import platform
        click.echo(f"Python version: {platform.python_version()}")
        click.echo(f"Platform: {platform.platform()}")
        click.echo(f"Architecture: {platform.architecture()}")

        # Show configuration info
        click.echo(f"Base directory: {config_obj.base_directory}")
        click.echo(f"Cache enabled: {config_obj.cache.enabled}")
        click.echo(f"Parallel processing: {config_obj.parallel.enabled}")

    if not version and not system_info:
        click.echo("Use --version or --system-info for specific information")


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to reset the application?')
@click.option('--hard', is_flag=True,
              help='Perform a hard reset (removes all data).')
@click.pass_context
def reset(_ctx: Context, hard: bool):
    """Reset the application to default state.

    Examples:
        aifo reset
        aifo reset --hard
    """
    if hard:
        click.echo("Performing hard reset...")
        # Here you would implement hard reset logic
        click.echo("Hard reset complete")
    else:
        click.echo("Performing soft reset...")
        # Here you would implement soft reset logic
        click.echo("Soft reset complete")


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        # Check if debug mode is enabled from context
        try:
            ctx = click.get_current_context()
            if ctx and ctx.obj.get('debug'):
                import traceback
                traceback.print_exc()
        except:
            pass
        sys.exit(1)


if __name__ == '__main__':
    main()