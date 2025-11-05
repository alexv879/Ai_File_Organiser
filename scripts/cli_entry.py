#!/usr/bin/env python3
"""
AI File Organiser CLI Entry Point

This script provides a command-line interface for the AI File Organiser.

Usage:
    python cli_entry.py [command] [options]

Copyright © 2025 Alexandru Emanuel Vasile. All rights reserved.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def main():
    """Main entry point."""
    try:
        # Try to import the CLI app
        try:
            from cli.aifo import app
        except ImportError:
            # Fallback to alternate import path
            from src.cli import app

        # Run the typer app
        app()
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you're running this from the project root directory.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()