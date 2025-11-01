# AI File Organiser

A Python-based intelligent file organization system powered by AI and local LLM capabilities.

## Overview

**AI File Organiser** is a comprehensive solution for automatically organizing, classifying, and managing files using artificial intelligence. It leverages local LLM models (via Ollama) to intelligently categorize files, detect duplicates, and optimize file organization without relying on cloud services.

## Features

### Core Capabilities
- **AI-Powered File Classification**: Intelligent categorization of files using machine learning
- **Duplicate Detection**: Identifies and manages duplicate files across directories
- **Text Extraction**: Extracts and processes text from various file formats
- **Real-time Monitoring**: Watches directories for changes and automatically organizes new files
- **Database Management**: Persistent storage of file metadata and organization history
- **Web Dashboard**: Interactive UI for monitoring and controlling file organization tasks
- **Agent Framework Integration**: AI agent for complex file organization workflows and analysis

### Advanced Features
- Local LLM integration via Ollama (privacy-first approach)
- Customizable classification rules and patterns
- Batch processing capabilities
- Comprehensive logging and audit trails
- License validation and security features

## Project Structure

```
src/
├── agent/                  # AI agent framework for workflow automation
│   └── agent_analyzer.py   # Agent analysis and decision-making
├── ai/                     # AI and LLM integration
│   ├── ollama_client.py    # Ollama LLM client
│   └── prompts/            # Classification and analysis prompts
├── core/                   # Core file organization logic
│   ├── actions.py          # File operation actions
│   ├── classifier.py       # AI-based file classification
│   ├── db_manager.py       # Database operations
│   ├── duplicates.py       # Duplicate detection
│   ├── text_extractor.py   # Text extraction utilities
│   └── watcher.py          # Directory watching and monitoring
├── license/                # License validation and API mocking
│   ├── api_mock.py         # Mock API for testing
│   └── validator.py        # License validation logic
├── ui/                     # User interface components
│   └── dashboard.py        # Web dashboard
├── utils/                  # Utility functions
│   └── logger.py           # Logging configuration
├── config.py               # Configuration management
└── main.py                 # Entry point
```

## Requirements

⚠️ **IMPORTANT**: This application requires **Ollama** to be installed for AI-powered file classification. Ollama is a mandatory dependency.

### System Requirements
- **Python 3.8 or later** (required)
- **Ollama** (required for AI classification)
- **4GB RAM minimum** (8GB recommended)
- **2GB free disk space** (for Ollama and AI models)
- **Internet connection** (for initial Ollama model download)

### Dependencies
All Python dependencies are listed in `requirements.txt` and will be installed automatically.

## Installation

### 🚀 Quick Install (Automated - Recommended)

**Windows:**
```cmd
git clone https://github.com/alexv879/Ai_File_Organiser.git
cd Ai_File_Organiser
install.bat
```

**Linux/macOS:**
```bash
git clone https://github.com/alexv879/Ai_File_Organiser.git
cd Ai_File_Organiser
chmod +x install.sh
./install.sh
```

The automated installer will:
1. Install Python dependencies
2. Download and install Ollama
3. Download the required AI model (`deepseek-r1:1.5b`)
4. Verify everything is working

### 📋 Manual Installation

If you prefer manual installation or the automated installer fails:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/alexv879/Ai_File_Organiser.git
   cd Ai_File_Organiser
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Ollama** (REQUIRED):
   
   **Option A - Automated Setup Script:**
   ```bash
   python setup_ollama.py
   ```
   
   **Option B - Manual Installation:**
   
   - **Windows**: Download from https://ollama.ai/download/windows
   - **macOS**: Download from https://ollama.ai/download/mac
   - **Linux**: Run `curl -fsSL https://ollama.ai/install.sh | sh`

4. **Download AI Model** (if not done by setup script):
   ```bash
   ollama pull deepseek-r1:1.5b
   ```

5. **Start Ollama Service**:
   - **Windows**: Ollama starts automatically
   - **Linux/macOS**: Run `ollama serve` in a separate terminal

6. **Verify Installation**:
   ```bash
   python -m src.main --help
   ```

## Usage

### Run the Application

```bash
python -m src.main
```

### Run the Dashboard

```bash
# On Linux/macOS
./run_dashboard.sh

# On Windows
run_dashboard.bat
```

The dashboard will be available at `http://localhost:5000` (or configured port)

### Run Tests

```bash
pytest tests/
```

## Configuration

The application can be configured via:
- Configuration files in the `config/` directory
- Environment variables
- Command-line arguments

Refer to `CONFIG.md` or configuration comments for detailed options.

## Architecture

### Classification System
The AI classification system uses local LLM models to intelligently categorize files based on:
- File content and metadata
- Directory context
- Custom classification rules
- Historical patterns

### Database Layer
Persistent storage for:
- File metadata and organization history
- Classification results
- Duplicate detection records
- User preferences and settings

### Agent Framework
Autonomous AI agents handle:
- Complex file organization workflows
- Decision-making and optimization
- Task automation and scheduling
- Real-time monitoring and alerts

## Privacy and Security

- **Local Processing**: All file processing happens locally—no data sent to cloud services
- **No Internet Required**: Works completely offline after initial setup
- **Customizable**: Full control over file organization rules and criteria
- **Secure**: License validation and security features included

## Development

### Project Status
- **Version**: 1.0
- **Status**: Active Development
- **Last Updated**: November 2025

### Contributing

This is a proprietary project. For inquiries about contributing or collaboration, please contact Alexandru Emanuel Vasile.

### License

This software is licensed under a Proprietary License. See `LICENSE` file for details.

**All rights reserved to Alexandru Emanuel Vasile.**

## Support and Contact

For issues, questions, or inquiries about licensing and commercial use:
- Contact: Alexandru Emanuel Vasile
- GitHub: https://github.com/alexv879

### Troubleshooting

**Ollama Connection Issues:**
- Verify Ollama is running: `curl http://localhost:11434/api/tags`
- Check if model is installed: `ollama list`
- Restart Ollama service

**Python Import Errors:**
- Reinstall dependencies: `pip install -r requirements.txt`
- Verify Python version: `python --version` (must be 3.8+)

**Permission Errors:**
- Run with appropriate permissions
- Check folder access rights in configuration

**Model Download Fails:**
- Check internet connection
- Try manual download: `ollama pull deepseek-r1:1.5b`
- Use alternative model in `config.json`

## Disclaimer

This software is provided "AS IS" without any warranty. The author is not responsible for any data loss, corruption, or issues arising from the use of this software. Always maintain backups of important files before using automated organization tools.

## Roadmap

Planned features and improvements:
- Advanced ML models for better classification accuracy
- Multi-language support
- Enhanced duplicate detection algorithms
- Mobile app integration
- Cloud backup integration (optional)
- Performance optimizations for large-scale file operations

---

**Copyright © 2025 Alexandru Emanuel Vasile. All rights reserved.**
