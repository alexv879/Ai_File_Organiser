#!/usr/bin/env python3
"""
Ollama Setup and Configuration Script for AI File Organiser
Copyright © 2025 Alexandru Emanuel Vasile. All rights reserved.

This script automates the installation and configuration of Ollama
for use with the AI File Organiser application.
"""

import sys
import platform
import subprocess
import time
import requests


class OllamaSetup:
    """Handles Ollama installation and setup"""
    
    def __init__(self):
        self.system = platform.system()
        self.ollama_url = "http://localhost:11434"
        self.required_model = "deepseek-r1:1.5b"
        
    def print_header(self, text):
        """Print formatted header"""
        print("\n" + "="*60)
        print(f"  {text}")
        print("="*60 + "\n")
    
    def check_ollama_installed(self):
        """Check if Ollama is already installed"""
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"✅ Ollama is installed: {result.stdout.strip()}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        print("❌ Ollama is not installed")
        return False
    
    def check_ollama_running(self):
        """Check if Ollama service is running"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                print(f"✅ Ollama service is running at {self.ollama_url}")
                return True
        except requests.exceptions.RequestException:
            pass
        
        print(f"❌ Ollama service is not running at {self.ollama_url}")
        return False
    
    def install_ollama_windows(self):
        """Install Ollama on Windows"""
        print("\n📥 Installing Ollama on Windows...")
        print("\nPlease follow these steps:")
        print("1. Visit: https://ollama.ai/download/windows")
        print("2. Download the Windows installer (OllamaSetup.exe)")
        print("3. Run the installer and follow the prompts")
        print("4. After installation, restart this script")
        
        # Open browser to download page
        try:
            import webbrowser
            webbrowser.open("https://ollama.ai/download/windows")
            print("\n✅ Opening download page in your browser...")
        except:
            pass
        
        input("\nPress Enter after you've installed Ollama...")
        return self.check_ollama_installed()
    
    def install_ollama_linux(self):
        """Install Ollama on Linux"""
        print("\n📥 Installing Ollama on Linux...")
        print("\nRunning installation command...")
        
        try:
            # Official Ollama install script
            result = subprocess.run(
                ["curl", "-fsSL", "https://ollama.ai/install.sh"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Pipe to sh
                subprocess.run(
                    ["sh"],
                    input=result.stdout,
                    text=True,
                    timeout=300
                )
                print("✅ Ollama installation completed")
                return True
            else:
                print("❌ Failed to download installation script")
                return False
        except Exception as e:
            print(f"❌ Installation failed: {e}")
            print("\nManual installation:")
            print("Run: curl -fsSL https://ollama.ai/install.sh | sh")
            return False
    
    def install_ollama_mac(self):
        """Install Ollama on macOS"""
        print("\n📥 Installing Ollama on macOS...")
        print("\nPlease follow these steps:")
        print("1. Visit: https://ollama.ai/download/mac")
        print("2. Download Ollama.app")
        print("3. Move Ollama.app to your Applications folder")
        print("4. Open Ollama.app")
        print("5. After installation, restart this script")
        
        # Open browser to download page
        try:
            import webbrowser
            webbrowser.open("https://ollama.ai/download/mac")
            print("\n✅ Opening download page in your browser...")
        except:
            pass
        
        input("\nPress Enter after you've installed Ollama...")
        return self.check_ollama_installed()
    
    def start_ollama_service(self):
        """Start Ollama service"""
        print("\n🚀 Starting Ollama service...")
        
        try:
            if self.system == "Windows":
                # On Windows, Ollama runs as a service automatically
                print("Waiting for Ollama service to start...")
                time.sleep(5)
            else:
                # On Linux/Mac, start in background
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("Waiting for service to initialize...")
                time.sleep(3)
            
            # Verify it's running
            for _attempt in range(10):
                if self.check_ollama_running():
                    return True
                time.sleep(1)
            
            print("⚠️  Service may not have started properly")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start service: {e}")
            return False
    
    def check_model_installed(self):
        """Check if required model is installed"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = [m.get('name', '') for m in data.get('models', [])]
                
                if self.required_model in models:
                    print(f"✅ Model '{self.required_model}' is installed")
                    return True
                else:
                    print(f"❌ Model '{self.required_model}' is not installed")
                    print(f"   Available models: {', '.join(models) if models else 'None'}")
                    return False
        except Exception as e:
            print(f"❌ Failed to check models: {e}")
            return False
    
    def pull_model(self):
        """Download required model"""
        print(f"\n📥 Downloading model: {self.required_model}")
        print("This may take a few minutes depending on your internet speed...")
        
        try:
            # Use subprocess to show progress
            result = subprocess.run(
                ["ollama", "pull", self.required_model],
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                print(f"\n✅ Model '{self.required_model}' downloaded successfully!")
                return True
            else:
                print(f"\n❌ Failed to download model")
                return False
                
        except subprocess.TimeoutExpired:
            print("\n❌ Download timed out. Please try again with a better internet connection.")
            return False
        except Exception as e:
            print(f"\n❌ Download failed: {e}")
            return False
    
    def run_setup(self):
        """Run complete setup process"""
        self.print_header("AI File Organiser - Ollama Setup")
        
        print("This script will set up Ollama for AI-powered file classification.")
        print(f"System detected: {self.system}")
        
        # Step 1: Check if Ollama is installed
        self.print_header("Step 1: Checking Ollama Installation")
        if not self.check_ollama_installed():
            print("\n📦 Ollama needs to be installed.")
            response = input("Install Ollama now? (y/n): ").strip().lower()
            
            if response != 'y':
                print("\n❌ Setup cancelled. Ollama is required for AI File Organiser.")
                return False
            
            # Install based on OS
            if self.system == "Windows":
                if not self.install_ollama_windows():
                    return False
            elif self.system == "Linux":
                if not self.install_ollama_linux():
                    return False
            elif self.system == "Darwin":  # macOS
                if not self.install_ollama_mac():
                    return False
            else:
                print(f"❌ Unsupported operating system: {self.system}")
                return False
        
        # Step 2: Check if service is running
        self.print_header("Step 2: Starting Ollama Service")
        if not self.check_ollama_running():
            if not self.start_ollama_service():
                print("\n⚠️  Please start Ollama manually:")
                if self.system == "Windows":
                    print("   - Ollama should start automatically")
                    print("   - Or open Ollama from the Start menu")
                else:
                    print("   - Run: ollama serve")
                
                input("\nPress Enter after starting Ollama...")
                if not self.check_ollama_running():
                    return False
        
        # Step 3: Check and download model
        self.print_header("Step 3: Installing AI Model")
        if not self.check_model_installed():
            print(f"\n📦 Model '{self.required_model}' needs to be downloaded.")
            response = input("Download model now? (y/n): ").strip().lower()
            
            if response != 'y':
                print("\n❌ Setup cancelled. Model is required for AI classification.")
                return False
            
            if not self.pull_model():
                return False
        
        # Final verification
        self.print_header("Setup Complete!")
        print("✅ Ollama is installed and running")
        print(f"✅ Model '{self.required_model}' is ready")
        print(f"✅ Service available at: {self.ollama_url}")
        print("\n🚀 You can now run AI File Organiser:")
        print("   python -m src.main dashboard")
        print("   python -m src.main scan")
        
        return True


def main():
    """Main entry point"""
    try:
        setup = OllamaSetup()
        success = setup.run_setup()
        
        if not success:
            print("\n" + "="*60)
            print("  Setup failed or was cancelled")
            print("="*60)
            print("\nFor manual setup, visit: https://ollama.ai")
            sys.exit(1)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
