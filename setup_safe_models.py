"""
Safe Multi-Model Setup Script

This script sets up the recommended two-model system for safe file classification:
- Reasoning Model: For intelligent analysis with chain-of-thought
- Validator Model: For safety checking and error detection

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
"""

import subprocess
import sys
import platform
import requests
from typing import List


class SafeModelSetup:
    """Setup safe two-model classification system"""
    
    # Recommended model configurations
    CONFIGS = {
        "conservative": {
            "reasoning": "qwen2.5:14b",
            "validator": "deepseek-r1:14b",
            "description": "Most accurate and safe (requires ~18GB disk, 12GB RAM)",
            "disk_space": "18GB",
            "ram": "12GB"
        },
        "balanced": {
            "reasoning": "deepseek-r1:14b",
            "validator": "qwen2.5:7b",
            "description": "Good balance of safety and performance (requires ~14GB disk, 10GB RAM)",
            "disk_space": "14GB",
            "ram": "10GB"
        },
        "fast": {
            "reasoning": "qwen2.5:7b",
            "validator": "deepseek-r1:7b",
            "description": "Faster but still safe (requires ~10GB disk, 8GB RAM)",
            "disk_space": "10GB",
            "ram": "8GB"
        },
        "minimal": {
            "reasoning": "deepseek-r1:1.5b",
            "validator": "qwen2.5:3b",
            "description": "Lightweight but less accurate (requires ~3GB disk, 4GB RAM) - NOT RECOMMENDED",
            "disk_space": "3GB",
            "ram": "4GB"
        }
    }
    
    def __init__(self):
        self.system = platform.system()
        self.ollama_url = "http://localhost:11434"
    
    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{'='*70}")
        print(f"  {text}")
        print(f"{'='*70}")
    
    def check_ollama_running(self) -> bool:
        """Check if Ollama service is running"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_installed_models(self) -> List[str]:
        """Get list of installed models"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                return [m['name'] for m in response.json().get('models', [])]
        except:
            pass
        return []
    
    def pull_model(self, model_name: str) -> bool:
        """Download a model"""
        print(f"\n📥 Downloading: {model_name}")
        print("This may take several minutes...")
        
        try:
            result = subprocess.run(
                ["ollama", "pull", model_name],
                timeout=600
            )
            
            if result.returncode == 0:
                print(f"✅ {model_name} downloaded successfully!")
                return True
            else:
                print(f"❌ Failed to download {model_name}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def show_configurations(self):
        """Display available configurations"""
        self.print_header("Available Configurations")
        
        for i, (name, config) in enumerate(self.CONFIGS.items(), 1):
            print(f"\n{i}. {name.upper()}")
            print(f"   Reasoning Model: {config['reasoning']}")
            print(f"   Validator Model: {config['validator']}")
            print(f"   {config['description']}")
            print(f"   Requirements: {config['disk_space']} disk space, {config['ram']} RAM")
    
    def recommend_configuration(self) -> str:
        """Recommend configuration based on system"""
        # Simple heuristic - in practice, check actual available resources
        if self.system == "Darwin":  # macOS
            return "balanced"
        elif self.system == "Linux":
            return "balanced"
        else:  # Windows
            return "fast"
    
    def setup_models(self, config_name: str) -> bool:
        """Setup models for chosen configuration"""
        if config_name not in self.CONFIGS:
            print(f"❌ Invalid configuration: {config_name}")
            return False
        
        config = self.CONFIGS[config_name]
        reasoning_model = config['reasoning']
        validator_model = config['validator']
        
        self.print_header(f"Setting Up {config_name.upper()} Configuration")
        print(f"Reasoning Model: {reasoning_model}")
        print(f"Validator Model: {validator_model}")
        
        # Check what's already installed
        installed = self.get_installed_models()
        print(f"\nCurrently installed: {', '.join(installed) if installed else 'None'}")
        
        # Pull reasoning model if needed
        if reasoning_model not in installed:
            if not self.pull_model(reasoning_model):
                return False
        else:
            print(f"✓ {reasoning_model} already installed")
        
        # Pull validator model if needed (skip if same as reasoning)
        if validator_model != reasoning_model:
            if validator_model not in installed:
                if not self.pull_model(validator_model):
                    return False
            else:
                print(f"✓ {validator_model} already installed")
        
        return True
    
    def update_config_file(self, reasoning_model: str, validator_model: str):
        """Update config.json with chosen models"""
        import json
        from pathlib import Path
        
        config_path = Path("config.json")
        if not config_path.exists():
            print(f"⚠ Warning: config.json not found")
            return
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update model settings
            config['ollama_model'] = reasoning_model  # Keep for backward compatibility
            config['reasoning_model'] = reasoning_model
            config['validator_model'] = validator_model
            config['use_safe_classifier'] = True
            
            with open(config_path, 'w') as f:
                json.dump(config, indent=2, fp=f)
            
            print(f"\n✅ Updated config.json")
            print(f"   Reasoning Model: {reasoning_model}")
            print(f"   Validator Model: {validator_model}")
            
        except Exception as e:
            print(f"❌ Failed to update config.json: {e}")
    
    def run_interactive_setup(self):
        """Interactive setup wizard"""
        self.print_header("Safe Multi-Model Setup Wizard")
        
        print("\n⚠️  IMPORTANT: Safe File Organization")
        print("─" * 70)
        print("This setup uses TWO AI models for safety:")
        print("  1. Reasoning Model: Analyzes files with detailed chain-of-thought")
        print("  2. Validator Model: Checks decisions for safety issues")
        print("\nThis two-stage approach prevents mistakes that could cause data loss.")
        print("─" * 70)
        
        # Check Ollama
        if not self.check_ollama_running():
            print("\n❌ Ollama is not running!")
            print("Please run: ollama serve")
            print("Or run: python setup_ollama.py")
            return False
        
        print("\n✅ Ollama is running")
        
        # Show configurations
        self.show_configurations()
        
        # Get recommendation
        recommended = self.recommend_configuration()
        print(f"\n💡 Recommended for your system: {recommended.upper()}")
        
        # User choice
        print("\nChoose configuration:")
        print("1 = Conservative, 2 = Balanced, 3 = Fast, 4 = Minimal")
        print(f"[Press Enter for recommended: {recommended}]")
        
        choice = input("\nYour choice: ").strip()
        
        if not choice:
            config_name = recommended
        else:
            config_map = {"1": "conservative", "2": "balanced", "3": "fast", "4": "minimal"}
            config_name = config_map.get(choice, recommended)
        
        # Warning for minimal
        if config_name == "minimal":
            print("\n⚠️  WARNING: Minimal configuration is NOT RECOMMENDED")
            print("The models are too small for safe file organization.")
            confirm = input("Continue anyway? (yes/no): ").strip().lower()
            if confirm != "yes":
                print("Setup cancelled. Choose a different configuration.")
                return False
        
        # Setup models
        config = self.CONFIGS[config_name]
        if not self.setup_models(config_name):
            return False
        
        # Update config file
        self.update_config_file(config['reasoning'], config['validator'])
        
        # Final success message
        self.print_header("Setup Complete!")
        print("\n✅ Your AI File Organiser is now configured with safe dual-model system!")
        print(f"\nConfiguration: {config_name.upper()}")
        print(f"  Reasoning: {config['reasoning']}")
        print(f"  Validator: {config['validator']}")
        print("\n📖 How it works:")
        print("  1. Reasoning model analyzes file and suggests organization")
        print("  2. Validator model checks for safety issues and errors")
        print("  3. If both agree and it's safe → auto-approve")
        print("  4. If concerns found → requires manual review")
        print("\nYou can now run: python src/main.py")
        print("Or start the dashboard: python src/ui/dashboard.py")
        
        return True


def main():
    """Main entry point"""
    setup = SafeModelSetup()
    
    # Support command-line arguments for non-interactive use
    if len(sys.argv) > 1:
        config_name = sys.argv[1]
        if config_name in setup.CONFIGS:
            setup.setup_models(config_name)
            config = setup.CONFIGS[config_name]
            setup.update_config_file(config['reasoning'], config['validator'])
        else:
            print(f"Usage: python setup_safe_models.py [conservative|balanced|fast|minimal]")
            sys.exit(1)
    else:
        # Interactive mode
        setup.run_interactive_setup()


if __name__ == "__main__":
    main()
