"""
Private AI File Organiser - Main Entry Point

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This is the main application entry point that orchestrates all components.
It provides CLI interface for running the organiser in different modes.

NOTICE: This software is proprietary and confidential. Unauthorized copying,
modification, distribution, or use is strictly prohibited.
See LICENSE.txt for full terms and conditions.

Version: 1.0.0
Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import sys
import argparse
import asyncio
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from .config import get_config
from .core.db_manager import DatabaseManager
from .core.classifier import FileClassifier
from .core.actions import ActionManager
from .core.watcher import FolderWatcher
from .core.duplicates import DuplicateFinder
from .ai.ollama_client import OllamaClient
from .license.validator import LicenseValidator
from .ui.dashboard import run_dashboard
from .core.deferred import DeferredService
from .utils.error_handler import ConfigurationError


class ServiceContainer:
    """
    Dependency injection container for managing application services.

    This reduces tight coupling by centralizing component creation and
    allowing services to be easily mocked or replaced for testing.
    """

    def __init__(self, config):
        """
        Initialize service container.

        Args:
            config: Application configuration
        """
        self.config = config
        self._services = {}
        self._singletons = {}

    def register(self, name: str, factory, singleton: bool = True):
        """
        Register a service factory.

        Args:
            name (str): Service name
            factory: Factory function or class
            singleton (bool): Whether to create as singleton
        """
        self._services[name] = {
            'factory': factory,
            'singleton': singleton
        }

    def get(self, name: str):
        """
        Get a service instance.

        Args:
            name (str): Service name

        Returns:
            Service instance
        """
        if name not in self._services:
            raise ConfigurationError(f"Service '{name}' not registered", config_key=name)

        service_config = self._services[name]

        if service_config['singleton']:
            if name not in self._singletons:
                self._singletons[name] = service_config['factory']()
            return self._singletons[name]
        else:
            return service_config['factory']()

    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services

    def clear_singletons(self):
        """Clear all singleton instances (useful for testing)."""
        self._singletons.clear()


class FileOrganiser:
    """
    Main application orchestrator.

    This class coordinates all components of the file organiser.
    Uses singleton pattern to ensure only one instance exists.

    Attributes:
        config: Configuration object
        db: Database manager
        ollama: Ollama AI client
        classifier: File classifier
        action_manager: Action manager
        watcher: Folder watcher
        duplicate_finder: Duplicate finder
        license_validator: License validator
    """

    _instance = None  # Singleton instance

    def __new__(cls):
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the file organiser."""
        print("🤖 AI File Organiser - Initializing...")

        # Load configuration
        self.config = get_config()

        # Initialize service container for dependency injection
        self.services = ServiceContainer(self.config)

        # Initialize database
        self.db = DatabaseManager()

        # Initialize license validator
        self.license_validator = LicenseValidator(self.config, self.db)

        # Check license FIRST - this is blocking
        if not self._check_license():
            print("\n❌ License validation failed.")
            self._prompt_license_activation()
            # If we reach here, license was activated successfully
            # Re-validate to ensure it worked
            if not self._check_license():
                print("\n❌ License validation still failed after activation. Exiting.")
                sys.exit(1)

        print("✅ License valid")

        # Initialize components only after license is confirmed
        self._initialize_components()

        print("✅ Initialization complete\n")

    def _initialize_components(self):
        """Initialize all application components with error handling."""
        failed_components = []

        # Register Ollama client factory
        def create_ollama_client():
            try:
                client = OllamaClient(
                    base_url=self.config.ollama_base_url,
                    model=self.config.ollama_model,
                    timeout=self.config.get('ollama_timeout', 30)
                )
                if client.is_available():
                    return client
                else:
                    print(f"⚠️  Ollama not available - AI classification disabled")
                    return None
            except Exception as e:
                print(f"❌ Failed to create Ollama client: {e}")
                return None

        self.services.register('ollama_client', create_ollama_client)

        # Register classifier factory
        def create_classifier():
            ollama_client = self.services.get('ollama_client')
            return FileClassifier(self.config, ollama_client)

        self.services.register('classifier', create_classifier)

        # Register action manager factory
        def create_action_manager():
            return ActionManager(self.config, self.db)

        self.services.register('action_manager', create_action_manager)

        # Register duplicate finder factory
        def create_duplicate_finder():
            return DuplicateFinder(self.config, self.db)

        self.services.register('duplicate_finder', create_duplicate_finder)

        # Register watcher factory
        def create_watcher():
            return FolderWatcher(
                folders=self.config.watched_folders,
                callback=self._on_file_detected,
                config=self.config
            )

        self.services.register('watcher', create_watcher)

        # Register deferred service factory
        def create_deferred_service():
            poll = int(self.config.get('deferred.poll_seconds', 60))
            enabled = bool(self.config.get('deferred.enabled', True))
            return DeferredService(self.db, self.config, poll_seconds=poll, enabled=enabled)

        self.services.register('deferred_service', create_deferred_service)

        # Initialize components with error handling
        try:
            print("Connecting to Ollama...")
            self.ollama = self.services.get('ollama_client')
            if self.ollama:
                print(f"✅ Ollama connected (model: {self.config.ollama_model})")
        except Exception as e:
            print(f"❌ Failed to initialize Ollama client: {e}")
            self.ollama = None
            failed_components.append("Ollama")

        # Initialize classifier (always try, even without Ollama)
        try:
            self.classifier = self.services.get('classifier')
            print("✅ Classifier initialized")
        except Exception as e:
            print(f"❌ Failed to initialize classifier: {e}")
            failed_components.append("Classifier")
            raise  # Classifier is critical, fail if it can't initialize

        # Initialize action manager
        try:
            self.action_manager = self.services.get('action_manager')
            print("✅ Action manager initialized")
        except Exception as e:
            print(f"❌ Failed to initialize action manager: {e}")
            failed_components.append("ActionManager")
            raise  # Action manager is critical

        # Initialize duplicate finder
        try:
            self.duplicate_finder = self.services.get('duplicate_finder')
            print("✅ Duplicate finder initialized")
        except Exception as e:
            print(f"❌ Failed to initialize duplicate finder: {e}")
            failed_components.append("DuplicateFinder")
            raise  # Duplicate finder is critical

        # Initialize watcher
        try:
            self.watcher = self.services.get('watcher')
            print("✅ Folder watcher initialized")
        except Exception as e:
            print(f"❌ Failed to initialize folder watcher: {e}")
            failed_components.append("Watcher")
            # Watcher is not critical, can continue without it
            self.watcher = None

        # Initialize deferred background service
        try:
            self.deferred = self.services.get('deferred_service')
            print("✅ Deferred service initialized")
        except Exception as e:
            print(f"❌ Failed to initialize deferred service: {e}")
            failed_components.append("DeferredService")
            self.deferred = None

        # Report any non-critical failures
        if failed_components:
            non_critical = [c for c in failed_components if c not in ["Classifier", "ActionManager", "DuplicateFinder"]]
            if non_critical:
                print(f"⚠️  Some non-critical components failed: {', '.join(non_critical)}")
                print("   The application will continue with reduced functionality.")

        # Ensure we have minimum required components
        if not hasattr(self, 'classifier') or not hasattr(self, 'action_manager'):
            raise RuntimeError("Critical components failed to initialize. Cannot continue.")

    def _check_license(self) -> bool:
        """
        Check if license is valid.

        Returns:
            bool: True if license is valid
        """
        status = self.license_validator.check_license_status()
        return status['is_valid']

    def _prompt_license_activation(self):
        """Prompt user to activate license. This method will exit if activation fails."""
        print("\n" + "="*50)
        print("LICENSE ACTIVATION REQUIRED")
        print("="*50)

        license_key = input("\nEnter your license key (XXXX-XXXX-XXXX-XXXX): ").strip()

        if license_key:
            result = self.license_validator.activate_license(license_key)
            print(f"\n{result['message']}")

            if result['success']:
                print("\n✅ License activated successfully!")
                return  # Success - continue initialization
            else:
                print("\n❌ Activation failed.")
        else:
            print("\n❌ No license key provided.")

        # If we reach here, activation failed - exit the program
        print("\nExiting due to license issues.")
        sys.exit(1)

    def _on_file_detected(self, file_path: str):
        """
        Callback when watcher detects a new file.

        Args:
            file_path (str): Path to detected file
        """
        print(f"\n📁 New file detected: {Path(file_path).name}")

        # Classify file
        classification = self.classifier.classify(file_path)

        print(f"   Category: {classification['category']}")
        print(f"   Suggested: {classification.get('suggested_path', 'N/A')}")
        print(f"   Reason: {classification['reason']}")
        print(f"   Method: {classification['method']} ({classification['confidence']} confidence)")

        # If deferred is enabled, enqueue the file for later processing
        if self.deferred and self.deferred.enabled:
            delay_hours = float(self.config.get('deferred.delay_hours', 24))
            enq_id = self.deferred.schedule_new_file(file_path, delay_hours)
            if enq_id > 0:
                print(f"   🕒 Deferred: scheduled for ~{delay_hours}h later (ID {enq_id})")
            else:
                print(f"   ⏭️  Deferred skip (protected or missing)")
            return

        # Otherwise keep legacy behavior depending on auto_mode
        if self.config.auto_mode:
            print(f"   🤖 Auto mode: executing action...")
            # Use async execution for better performance
            asyncio.create_task(self._execute_action_async(file_path, classification, False))
        else:
            print(f"   ⏸️  Waiting for approval (use dashboard or CLI)")

    async def _execute_action_async(self, file_path: str, classification: dict, user_approved: bool):
        """
        Execute action asynchronously for better performance.

        Args:
            file_path (str): Path to the file
            classification (dict): Classification result
            user_approved (bool): Whether user approved the action
        """
        try:
            result = await self.action_manager.execute_async(
                file_path=file_path,
                classification=classification,
                user_approved=user_approved
            )
            if result['success']:
                print(f"   ✅ {result['message']}")
                print(f"   ⏱️  Time saved: {result.get('time_saved', 0):.1f} minutes")
            else:
                print(f"   ❌ {result['message']}")
        except Exception as e:
            print(f"   ❌ Error in async execution: {e}")

    def start_watch_mode(self):
        """Start watching folders for new files."""
        print("👀 Starting watch mode...")
        print(f"Monitoring folders:")
        for folder in self.config.watched_folders:
            print(f"  - {folder}")

        print(f"\nAuto mode: {'ENABLED' if self.config.auto_mode else 'DISABLED'}")
        print(f"Dry run: {'ENABLED' if self.config.dry_run else 'DISABLED'}")
        print(f"AI classification: {'ENABLED' if self.config.enable_ai else 'DISABLED'}")

        print("\nPress Ctrl+C to stop\n")

        # Start deferred service first, then watcher
        if self.deferred:
            self.deferred.start()
        if self.watcher:
            self.watcher.start(background=True, async_processing=True)  # Enable async processing

        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping watcher...")
            if self.watcher:
                self.watcher.stop()
            print("Goodbye! 👋")

    def scan_existing_files(self):
        """Scan existing files in watched folders."""
        print("🔍 Scanning existing files...")

        if not self.watcher:
            print("❌ Watcher not available - cannot scan existing files")
            return

        files = self.watcher.scan_existing_files()
        print(f"Found {len(files)} candidates")
        # First-run deep planning: enqueue by age
        move_older_days = int(self.config.get('deferred.first_run_move_older_days', 7))
        default_delay = float(self.config.get('deferred.delay_hours', 24))
        if self.deferred and self.deferred.enabled:
            queued = 0
            for fp in files:
                enq_id = self.deferred.schedule_existing_file(fp, move_if_older_days=move_older_days, default_delay_hours=default_delay)
                if enq_id > 0:
                    queued += 1
            print(f"✅ Enqueued {queued} file(s) for deferred organization (older≥{move_older_days}d move sooner)")
        else:
            # Fallback: classify only (no move)
            for fp in files:
                _ = self.classifier.classify(fp)
            print("ℹ️ Deferred service disabled; performed classification only")

    def find_duplicates(self, cross_drive: bool = False):
        """Find and report duplicate files."""
        if cross_drive:
            print("🔍 Scanning for cross-drive duplicate files...")
            result = self.duplicate_finder.find_duplicates_cross_drive(dry_run=True)

            if not result['duplicates']:
                print("\n✅ No duplicates found!")
                return

            duplicates = result['duplicates']
            results = result['results']
            summary = result['summary']

            print(f"\nFound {len(duplicates)} duplicate groups\n")
            print("-" * 70)

            for i, (dup_group, cleanup_result) in enumerate(zip(duplicates, results), 1):
                keep_drive = self.duplicate_finder.get_drive_letter(cleanup_result['keep'])

                print(f"\n#{i} Duplicate Group (Size: {dup_group['size'] / (1024*1024):.1f} MB)")
                print(f"   KEEP: {cleanup_result['keep']}")
                print(f"   Date: {cleanup_result.get('keep_date', 'N/A')}")
                print(f"   Drive: {keep_drive}:\\")
                print(f"   \n   DELETE ({len(cleanup_result['delete'])} older versions):")

                for delete_path in cleanup_result['delete']:
                    delete_drive = self.duplicate_finder.get_drive_letter(delete_path)
                    print(f"      - {delete_path}")
                    print(f"        Drive: {delete_drive}:\\")

                print(f"   \n   WOULD FREE: {cleanup_result['space_freed_mb']:.1f} MB")
                print(f"   REASON: {cleanup_result['reason']}")

            print(f"\n" + "="*70)
            print("CROSS-DRIVE DUPLICATE SUMMARY")
            print("="*70)
            print(f"Total duplicate groups: {summary['total_duplicate_groups']}")
            print(f"Files that can be deleted: {summary['files_that_can_be_deleted']}")
            print(f"Total space to free: {summary['total_space_to_free_mb']:.1f} MB ({summary['total_space_to_free_gb']:.2f} GB)")
            print(f"Drives scanned: {', '.join(summary['drives_scanned'])}")
            print(f"Directories scanned: {summary['directories_scanned']}")
            print("="*70)
        else:
            # Original single-directory scanning
            print("🔍 Scanning for duplicate files...")

            all_duplicates = []

            for folder in self.config.watched_folders:
                print(f"\nScanning: {folder}")
                duplicates = self.duplicate_finder.find_duplicates_in_directory(folder, recursive=True)
                all_duplicates.extend(duplicates)

            if not all_duplicates:
                print("\n✅ No duplicates found!")
                return

            # Show summary
            summary = self.duplicate_finder.get_duplicate_summary(all_duplicates)

            print(f"\n" + "="*50)
            print("DUPLICATE FILES SUMMARY")
            print("="*50)
            print(f"Duplicate groups: {summary['total_duplicate_groups']}")
            print(f"Duplicate files: {summary['total_duplicate_files']}")
            print(f"Wasted space: {summary['total_wasted_space_mb']:.2f} MB")
            print(f"              ({summary['total_wasted_space_gb']:.2f} GB)")

            print(f"\n" + "-"*50)
            print("TOP 10 DUPLICATE GROUPS")
            print("-"*50)

            for i, group in enumerate(all_duplicates[:10], 1):
                print(f"\n{i}. {group['count']} files ({group['size']} bytes each)")
                for path in group['paths']:
                    print(f"   - {path}")

    def run_dashboard(self, host: str = "127.0.0.1", port: int = 5000):
        """
        Run the web dashboard.

        Args:
            host (str): Host to bind to
            port (int): Port to listen on
        """
        run_dashboard(host, port)

    def show_stats(self):
        """Show statistics."""
        stats = self.db.get_stats('all')

        print("\n" + "="*50)
        print("AI FILE ORGANISER - STATISTICS")
        print("="*50)
        print(f"Files organised: {stats['files_organised']}")
        print(f"Time saved: {stats['time_saved_hours']:.2f} hours")
        print(f"AI classifications: {stats['ai_classifications']}")
        print(f"Duplicates removed: {stats['duplicates_removed']}")

        # License info
        license_status = self.license_validator.check_license_status()
        print(f"\nLicense status: {license_status['status'].upper()}")
        if license_status.get('days_remaining'):
            print(f"Days remaining: {license_status['days_remaining']}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Private AI File Organiser - Your local-first file organization assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s dashboard           # Run web dashboard
  %(prog)s watch              # Watch folders for new files
  %(prog)s scan               # Scan existing files
  %(prog)s duplicates         # Find duplicate files
  %(prog)s stats              # Show statistics

For more information, visit: https://github.com/yourproject
        """
    )

    parser.add_argument(
        'command',
        choices=['dashboard', 'watch', 'scan', 'duplicates', 'stats', 'license'],
        help='Command to execute'
    )

    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Dashboard host (default: 127.0.0.1)'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Dashboard port (default: 5000)'
    )

    parser.add_argument(
        '--cross-drive',
        action='store_true',
        help='Scan for duplicates across all drives (C:, D:, etc.)'
    )

    parser.add_argument(
        '--activate',
        type=str,
        help='License key to activate (format: XXXX-XXXX-XXXX-XXXX)'
    )

    args = parser.parse_args()

    # Handle license activation (create instance only for activation)
    if args.activate:
        organiser = FileOrganiser()
        result = organiser.license_validator.activate_license(args.activate)
        print(result['message'])
        return

    # Create single instance for all other operations
    organiser = FileOrganiser()

    # Handle commands
    if args.command == 'dashboard':
        organiser.run_dashboard(args.host, args.port)

    elif args.command == 'watch':
        organiser.start_watch_mode()

    elif args.command == 'scan':
        organiser.scan_existing_files()

    elif args.command == 'duplicates':
        organiser.find_duplicates(cross_drive=args.cross_drive)

    elif args.command == 'stats':
        organiser.show_stats()

    elif args.command == 'license':
        status = organiser.license_validator.check_license_status()
        print(f"\n{status['message']}")


if __name__ == "__main__":
    main()
