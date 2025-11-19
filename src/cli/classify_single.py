#!/usr/bin/env python3
"""
Single file classification script for Tauri desktop app.
Returns JSON output for easy parsing.
"""

import sys
import json
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import get_config
from src.ai.ai_integration import AIOrganizer
from src.ai.models.base import ModelTier


def main():
    parser = argparse.ArgumentParser(description="Classify a single file")
    parser.add_argument("--file", required=True, help="File to classify")
    parser.add_argument("--multi-model", action="store_true", help="Use multi-model AI")
    parser.add_argument("--tier", default="FREE", choices=["FREE", "STARTER", "PRO", "ENTERPRISE"],
                        help="User subscription tier")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    file_path = Path(args.file)

    if not file_path.exists():
        error = {"error": f"File not found: {args.file}"}
        print(json.dumps(error))
        sys.exit(1)

    try:
        if args.multi_model:
            # Use new multi-model AI system
            config = get_config()
            tier = ModelTier[args.tier.upper()]

            ai_config = {
                'ollama_model': config.get('ollama_model', 'qwen2.5:7b-instruct'),
                'ollama_base_url': config.get('ollama_base_url', 'http://localhost:11434'),
                'openai_api_key': config.get('openai_api_key'),
                'anthropic_api_key': config.get('anthropic_api_key')
            }

            organizer = AIOrganizer(ai_config, user_tier=tier)
            result = organizer.classify_file(
                str(file_path),
                deep_analysis=True,
                prefer_local=(tier == ModelTier.FREE)
            )
        else:
            # Use traditional classifier
            from src.core.classifier import FileClassifier
            from src.ai.ollama_client import OllamaClient

            config = get_config()
            ollama = None
            try:
                ollama = OllamaClient(
                    base_url=config.ollama_base_url,
                    model=config.ollama_model,
                    timeout=config.get('ollama_timeout', 30)
                )
                if not ollama.is_available():
                    ollama = None
            except Exception:
                ollama = None

            classifier = FileClassifier(config, ollama)
            result = classifier.classify(str(file_path), deep_analysis=True)

            # Convert to expected format
            result = {
                'category': result.get('category', 'Uncategorized'),
                'subcategory': result.get('subcategory'),
                'confidence': result.get('confidence', 0.5),
                'suggested_path': result.get('suggested_path', ''),
                'suggested_name': result.get('suggested_name'),
                'tags': result.get('tags', []),
                'summary': result.get('summary'),
                'reasoning': result.get('reason'),
                'model_used': result.get('method', 'rule-based'),
                'processing_time_ms': 0,
                'tokens_used': 0,
                'cost_usd': 0.0
            }

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Category: {result['category']}")
            print(f"Confidence: {result['confidence']:.2%}")
            print(f"Suggested Path: {result['suggested_path']}")
            if result.get('reasoning'):
                print(f"Reasoning: {result['reasoning']}")
            print(f"Model: {result['model_used']}")
            if result.get('cost_usd', 0) > 0:
                print(f"Cost: ${result['cost_usd']:.6f}")

    except Exception as e:
        error = {"error": str(e)}
        if args.json:
            print(json.dumps(error))
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
