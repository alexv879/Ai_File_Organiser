"""
Organizer - Intelligently organize files in a folder

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import click

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cli.helpers import print_header, print_success, print_error, print_warning, print_info
from src.core.classifier import FileClassifier
from src.core.actions import ActionManager
from src.core.db_manager import DatabaseManager
from src.ai.ollama_client import OllamaClient
from src.config import get_config

# New multi-model AI support
try:
    from src.ai.ai_integration import AIOrganizer
    from src.ai.models.base import ModelTier
    AI_INTEGRATION_AVAILABLE = True
except ImportError:
    AI_INTEGRATION_AVAILABLE = False


class Organizer:
    """Intelligently organize files using AI and rules."""

    def __init__(self, use_multi_model: bool = False, user_tier: str = "FREE"):
        """Initialize organizer.

        Args:
            use_multi_model: Use new multi-model AI system (GPT-4, Claude, Ollama)
            user_tier: User subscription tier (FREE, STARTER, PRO, ENTERPRISE)
        """
        self.config = get_config()
        self.db = DatabaseManager()
        self.use_multi_model = use_multi_model and AI_INTEGRATION_AVAILABLE

        # Initialize multi-model AI if requested
        self.ai_organizer = None
        if self.use_multi_model:
            try:
                tier = ModelTier[user_tier.upper()]
                ai_config = {
                    'ollama_model': self.config.get('ollama_model', 'qwen2.5:7b-instruct'),
                    'ollama_base_url': self.config.get('ollama_base_url', 'http://localhost:11434'),
                    'openai_api_key': self.config.get('openai_api_key'),
                    'anthropic_api_key': self.config.get('anthropic_api_key')
                }
                self.ai_organizer = AIOrganizer(ai_config, user_tier=tier)
                print_info(f"🤖 Multi-model AI enabled (tier: {tier.value})")
            except Exception as e:
                print_warning(f"Could not initialize multi-model AI: {e}")
                self.use_multi_model = False

        # Fallback: Initialize traditional Ollama client
        self.ollama = None
        if not self.use_multi_model:
            try:
                self.ollama = OllamaClient(
                    base_url=self.config.ollama_base_url,
                    model=self.config.ollama_model,
                    timeout=self.config.get('ollama_timeout', 30)
                )
                if not self.ollama.is_available():
                    self.ollama = None
            except Exception:
                self.ollama = None

        # Initialize classifier (traditional system)
        self.classifier = FileClassifier(self.config, self.ollama)

        # Initialize action manager
        self.action_manager = ActionManager(self.config, self.db)

    def organize_folder(self, folder: Optional[str] = None, preview: bool = False,
                       auto: bool = False, deep: bool = False):
        """
        Organize files in a folder.

        Args:
            folder: Folder to organize (default: first watched folder)
            preview: Preview changes without applying (dry run)
            auto: Auto-approve all actions
            deep: Use deep AI analysis
        """
        # Determine folder to organize
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

        print_header(f"🗂️  Organizing: {folder_path}")

        if preview:
            print_info("PREVIEW MODE - No files will be moved\n")
            self.action_manager.set_dry_run(True)

        if deep and not self.ollama:
            print_warning("Deep AI analysis requested but Ollama not available")
            print_info("Using rule-based classification instead\n")
            deep = False

        # Find all files
        print_info("Scanning for files...")
        files = list(folder_path.rglob('*'))
        files = [f for f in files if f.is_file()]

        if not files:
            print_success("No files found to organize!")
            return

        print_info(f"Found {len(files)} files\n")

        # Classify and organize each file
        classifications = []

        click.echo("Classifying files...")
        with click.progressbar(files, label='Analyzing') as bar:
            for file_path in bar:
                try:
                    # Use new multi-model AI if available
                    if self.use_multi_model and self.ai_organizer:
                        classification = self.ai_organizer.classify_file(
                            str(file_path),
                            deep_analysis=deep,
                            prefer_local=(self.ai_organizer.user_tier == ModelTier.FREE)
                        )
                    else:
                        # Fallback to traditional classifier
                        classification = self.classifier.classify(
                            str(file_path),
                            deep_analysis=deep
                        )

                    classifications.append({
                        'file': file_path,
                        'classification': classification
                    })
                except Exception as e:
                    print_error(f"\nError classifying {file_path.name}: {e}")

        # Show summary
        categories = {}
        for item in classifications:
            cat = item['classification'].get('category', 'Unknown')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        click.echo(f"\n{'-'*60}")
        click.echo("CLASSIFICATION SUMMARY")
        click.echo(f"{'-'*60}")

        for category, items in sorted(categories.items()):
            click.echo(f"{category}: {len(items)} files")

        click.echo(f"\n{'-'*60}")

        # Ask for confirmation if not auto
        if not auto and not preview:
            if not click.confirm(f"\nOrganize {len(files)} files?", default=True):
                print_info("Cancelled.")
                return

        # Execute organization
        click.echo("\nOrganizing files...")

        success_count = 0
        error_count = 0
        skipped_count = 0

        with click.progressbar(classifications, label='Organizing') as bar:
            for item in bar:
                file_path = item['file']
                classification = item['classification']

                # Skip if no suggested path
                if not classification.get('suggested_path'):
                    skipped_count += 1
                    continue

                try:
                    result = self.action_manager.execute(
                        file_path=str(file_path),
                        classification=classification,
                        user_approved=True
                    )

                    if result['success']:
                        success_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    error_count += 1
                    click.echo(f"\nError organizing {file_path.name}: {e}")

        # Final summary
        click.echo(f"\n{'='*60}")
        click.echo("ORGANIZATION COMPLETE")
        click.echo(f"{'='*60}")

        if preview:
            print_info(f"Would organize: {success_count} files")
        else:
            print_success(f"✅ Organized: {success_count} files")

        if skipped_count > 0:
            print_warning(f"⏭️  Skipped: {skipped_count} files (no destination)")

        if error_count > 0:
            print_error(f"❌ Errors: {error_count} files")

        # Show statistics
        stats = self.action_manager.get_stats()
        time_saved = stats.get('time_saved_hours', 0)
        if time_saved > 0:
            print_success(f"\n⏱️  Total time saved: {time_saved:.2f} hours")

        # Show AI statistics if using multi-model
        if self.use_multi_model and self.ai_organizer:
            total_cost = sum(
                item['classification'].get('cost_usd', 0.0)
                for item in classifications
            )
            total_tokens = sum(
                item['classification'].get('tokens_used', 0)
                for item in classifications
            )
            avg_time = sum(
                item['classification'].get('processing_time_ms', 0)
                for item in classifications
            ) / max(len(classifications), 1)

            print_info(f"\n🤖 AI Statistics:")
            print_info(f"   Total cost: ${total_cost:.4f}")
            print_info(f"   Total tokens: {total_tokens:,}")
            print_info(f"   Avg processing time: {avg_time:.0f}ms per file")
