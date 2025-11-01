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

- Python 3.8+
- Ollama (for local LLM capabilities)
- Dependencies listed in `requirements.txt`

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/alexv879/Ai_File_Organiser.git
   cd Ai_File_Organiser
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Ollama** (optional but recommended):
   - Download and install [Ollama](https://ollama.ai)
   - Pull a model: `ollama pull llama2` (or another preferred model)
   - Start Ollama service: `ollama serve`

4. **Configure the application**:
   - Edit configuration files in the config directory as needed
   - Set up your classification rules and file organization preferences

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
