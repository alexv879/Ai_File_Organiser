# AI File Organiser - Project Structure

**Last Updated:** November 5, 2025

This document explains the clean, organized structure of the AI File Organiser project.

---

## 📁 Root Directory

```
AI File Organiser/
│
├── 🚀 launcher.py              # Main GUI application launcher
├── 📄 config.json              # User configuration settings
├── 📄 config.yaml              # Advanced YAML configuration
├── 📦 requirements.txt         # Python dependencies
│
├── 📖 README.md               # Project overview and introduction
├── 📖 QUICK_START.md          # Quick getting started guide
├── 📖 INSTALLATION_GUIDE.md   # Detailed installation instructions
├── ⚖️ LICENSE                  # Software license
│
├── 🔧 install.bat             # Windows installer
└── 🔧 install.sh              # Linux/Mac installer
```

---

## 📂 Main Directories

### `/src/` - Core Application Source Code
```
src/
├── __init__.py
├── main.py                    # Main application entry point
├── config.py                  # Configuration management
├── config_yaml.py             # YAML configuration system
│
├── /ai/                       # AI & LLM Integration
│   ├── ollama_client.py       # Ollama LLM client
│   └── /prompts/              # AI prompt templates
│
├── /agent/                    # Agent-based file analysis
│   ├── agent_analyzer.py      # Intelligent file analyzer
│   └── README.md              # Agent documentation
│
├── /core/                     # Core functionality
│   ├── actions.py             # File operations (move, copy, etc.)
│   ├── classifier.py          # File classification engine
│   ├── db_manager.py          # Database management
│   ├── duplicates.py          # Duplicate file detection
│   ├── metadata_extractor.py # Advanced metadata extraction
│   ├── text_extractor.py     # Text content extraction
│   └── watcher.py             # File system monitoring
│
├── /license/                  # License validation system
│   ├── validator.py           # License key validation
│   └── api_mock.py            # Mock API for testing
│
├── /ui/                       # User interface
│   └── dashboard.py           # Web dashboard (FastAPI)
│
└── /utils/                    # Utility modules
    └── logger.py              # Logging utilities
```

### `/scripts/` - Utility Scripts
```
scripts/
├── cli_entry.py               # Command-line interface entry
├── cross_drive_cleaner.py     # Cross-drive duplicate cleaner
│
└── /setup/                    # Setup utilities
    ├── setup_ollama.py        # Ollama installation script
    └── setup_safe_models.py   # Safe model configuration
```

### `/tests/` - Test Suite
```
tests/
├── test_agent.py              # Agent functionality tests
├── test_agent_validation.py  # Agent validation tests
│
└── /unit/                     # Unit tests
    ├── test_actions.py        # File action tests
    ├── test_classifier.py     # Classifier tests
    └── test_ollama_client.py  # Ollama client tests
```

### `/docs/` - Documentation
```
docs/
├── agent_examples.json        # Agent usage examples
├── agent_prompt.txt           # Agent prompt template
├── AGENT_IMPROVEMENTS.md      # Agent enhancement notes
├── AGENT_QUICKSTART.md        # Agent quick start guide
└── MODEL_COMPARISON.md        # LLM model comparison
```

### `/installer/` - Installation Tools
```
installer/
├── setup_wizard.py            # Interactive setup wizard
└── auto_updater.py            # Automatic update system
```

### `/data/` - Runtime Data (Created during use)
```
data/
├── .license_key               # License key storage
├── command_history.json       # Command history
├── users.json                 # User data
├── /database/                 # SQLite database files
├── /db/                       # Alternative database location
└── /logs/                     # Application logs
```

### `/logs/` - Log Files (Created at runtime)
```
logs/
└── *.log                      # Application log files
```

---

## 🚀 How to Use

### Running the Application

**GUI Mode (Recommended):**
```bash
python launcher.py
```

**CLI Mode:**
```bash
python scripts/cli_entry.py [command] [options]
```

**Web Dashboard:**
```bash
python src/main.py
# Then open: http://localhost:8000
```

### Setup Scripts

**Install Ollama:**
```bash
python scripts/setup/setup_ollama.py
```

**Configure Safe Models:**
```bash
python scripts/setup/setup_safe_models.py
```

**Cross-Drive Duplicate Cleanup:**
```bash
python scripts/cross_drive_cleaner.py
```

---

## 🔧 Configuration Files

### `config.json` - Main Configuration
User-facing configuration for:
- Watch directories
- Destination paths
- Organization rules
- AI model settings

### `config.yaml` - Advanced Configuration
YAML-based configuration for:
- Complex filter rules
- Advanced actions
- Conditional organization
- Template-based paths

---

## 📊 Data Flow

```
User Input (GUI/CLI)
        ↓
   launcher.py / cli_entry.py
        ↓
    src/main.py
        ↓
   ┌─────────────────────────────┐
   │  File Classification System  │
   ├─────────────────────────────┤
   │ 1. core/watcher.py          │ → Monitors directories
   │ 2. core/classifier.py       │ → Analyzes files
   │ 3. agent/agent_analyzer.py  │ → AI-powered analysis
   │ 4. core/metadata_extractor  │ → Extracts metadata
   └─────────────────────────────┘
        ↓
   ┌─────────────────────────────┐
   │   Action Execution System    │
   ├─────────────────────────────┤
   │ 1. core/actions.py          │ → Move/Copy/Rename
   │ 2. core/db_manager.py       │ → Track changes
   │ 3. ui/dashboard.py          │ → Display results
   └─────────────────────────────┘
        ↓
    Organized Files!
```

---

## 🧹 Removed from Previous Versions

The following were removed during cleanup (Nov 5, 2025):

### Deleted Folders:
- `.claude/` - AI assistant cache
- `.serena/` - MCP agent memories
- `.pytest_cache/` - Python test cache
- `__pycache__/` - Python bytecode cache
- `examples/` - Empty folder with non-functional templates
- `tools/` - Consolidated into tests/
- `config/` - Contents merged into data/

### Deleted Files:
- ~20 AI-generated analysis documents
- Template/example files (mcp_workflows.py)
- Temporary output files
- Integration test files from root

---

## 📝 Development Guidelines

### Adding New Features

1. **Core Functionality** → Add to `/src/core/`
2. **AI/Agent Features** → Add to `/src/ai/` or `/src/agent/`
3. **Utility Scripts** → Add to `/scripts/`
4. **Tests** → Add to `/tests/` or `/tests/unit/`
5. **Documentation** → Add to `/docs/`

### Code Organization Principles

- ✅ **Single Responsibility** - Each module has one clear purpose
- ✅ **Separation of Concerns** - UI, business logic, and data layers separated
- ✅ **Modularity** - Components can be used independently
- ✅ **Testability** - All core functions have unit tests

---

## 🎯 Quick Access

| Task | Command |
|------|---------|
| **Start GUI** | `python launcher.py` |
| **Start CLI** | `python scripts/cli_entry.py` |
| **Run Tests** | `pytest tests/` |
| **Setup Ollama** | `python scripts/setup/setup_ollama.py` |
| **Clean Duplicates** | `python scripts/cross_drive_cleaner.py` |
| **View Dashboard** | `python src/main.py` → http://localhost:8000 |

---

## 📞 Support

- **Documentation:** See `/docs/` folder
- **Quick Start:** Read `QUICK_START.md`
- **Installation Help:** Read `INSTALLATION_GUIDE.md`
- **License:** See `LICENSE` file

---

**Project Status:** ✅ Production Ready  
**Last Cleanup:** November 5, 2025  
**Structure Version:** 2.0 (Reorganized & Optimized)
