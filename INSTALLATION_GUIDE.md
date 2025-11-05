# AI File Organiser - Installation Guide

**Copyright © 2025 Alexandru Emanuel Vasile. All Rights Reserved.**

## One-Click Installation (Recommended) 🚀

The easiest way to install AI File Organiser is using the graphical setup wizard.

### Windows

**Double-click `install.bat`** - That's it!

Or from command line:
```cmd
install.bat
```

### Linux/macOS

**Make executable and run:**
```bash
chmod +x install.sh
./install.sh
```

The setup wizard will guide you through:
- ✅ Installation path selection
- ✅ Feature selection (MCP, Ollama, shortcuts)
- ✅ Claude Desktop configuration
- ✅ Automatic dependency installation
- ✅ Desktop shortcut creation

---

## What Gets Installed

### Core Components
- **AI File Organiser** - Main application
- **Python Dependencies** - All required packages
- **MCP Server** (optional) - For AI assistant integration
- **Ollama** (optional) - Local LLM for AI features

### Shortcuts Created
- **Desktop Shortcut** - Quick access launcher
- **Start Menu/Applications** - System menu entry

### Configuration
- **Claude Desktop** (optional) - Auto-configured for MCP
- **Auto-Update** (optional) - Anonymous update checking

---

## Manual Installation

If you prefer manual installation or the setup wizard doesn't work:

### Step 1: Prerequisites

**Required:**
- Python 3.8 or later
- pip (Python package manager)
- 4GB RAM (8GB recommended)
- 2GB free disk space

**Check Python:**
```bash
python --version
# or
python3 --version
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Install Ollama

**Windows:**
Download from https://ollama.ai/download/windows

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Step 4: Download AI Model

```bash
ollama pull deepseek-r1:1.5b
```

### Step 5: Install MCP (Optional)

For Claude Desktop integration:
```bash
pip install mcp
```

### Step 6: Configure Claude Desktop (Optional)

1. Find your Claude Desktop config:
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. Add this configuration:
```json
{
  "mcpServers": {
    "file-organiser": {
      "command": "python",
      "args": ["-m", "src.mcp.mcp_server"],
      "env": {
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "PYTHONPATH": "."
      },
      "cwd": "/path/to/AIFILEORGANISER"
    }
  }
}
```

3. Restart Claude Desktop

---

## Launching the Application

### Using the GUI Launcher (Recommended)

**Windows:**
- Double-click the desktop shortcut "AI File Organiser"
- Or run: `python launcher.py`

**Linux/macOS:**
- Click the applications menu entry
- Or run: `python3 launcher.py`

### Direct Commands

**Dashboard:**
```bash
python -m src.ui.dashboard
```

**MCP Server:**
```bash
python -m src.mcp.mcp_server
```

**File Organization:**
```bash
python examples/mcp_workflows.py
```

---

## Verification

### Test Installation

```bash
python -m src.main --help
```

### Test Ollama

```bash
curl http://localhost:11434/api/tags
```

### Test MCP (with Claude Desktop)

Open Claude Desktop and say:
```
"Claude, scan my Downloads folder"
```

---

## Troubleshooting

### Python Not Found

**Windows:**
- Install Python from https://python.org/downloads/
- ✅ **Check "Add Python to PATH"** during installation
- Restart command prompt

**Linux:**
```bash
sudo apt install python3 python3-pip python3-tk  # Ubuntu/Debian
sudo dnf install python3 python3-pip python3-tkinter  # Fedora
```

**macOS:**
```bash
brew install python-tk
```

### Setup Wizard Doesn't Open

**Missing tkinter:**
```bash
# Ubuntu/Debian
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# macOS
brew install python-tk
```

### Ollama Not Found

Download and install from https://ollama.ai

Verify installation:
```bash
ollama --version
```

### Claude Desktop Not Detecting MCP Server

1. Check config file path is correct
2. Verify `cwd` points to project directory
3. Restart Claude Desktop completely
4. Check Claude Desktop logs for errors

### Permission Errors

**Windows:**
- Right-click installer → "Run as Administrator"

**Linux/macOS:**
```bash
chmod +x install.sh
chmod +x launcher.py
```

### Import Errors

Reinstall dependencies:
```bash
pip install -r requirements.txt --force-reinstall
```

---

## Uninstallation

### Using Uninstaller (If Available)

Windows:
- Control Panel → Programs → AI File Organiser → Uninstall

### Manual Uninstallation

1. **Delete installation folder**
   ```bash
   rm -rf /path/to/AIFILEORGANISER
   ```

2. **Remove desktop shortcut**
   - Windows: Delete from Desktop and Start Menu
   - Linux: Remove from Desktop and `~/.local/share/applications/`
   - macOS: Remove from Applications folder

3. **Remove Claude Desktop config** (optional)
   - Edit Claude config file
   - Remove `file-organiser` entry from `mcpServers`

4. **Uninstall Ollama** (optional)
   - Follow Ollama uninstallation instructions

---

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| **OS** | Windows 10+, macOS 10.14+, Linux (any modern distro) |
| **Python** | 3.8 or later |
| **RAM** | 4GB |
| **Disk** | 2GB free |
| **CPU** | Dual-core 2GHz+ |

### Recommended Requirements

| Component | Requirement |
|-----------|-------------|
| **OS** | Windows 11, macOS 13+, Ubuntu 22.04+ |
| **Python** | 3.10 or later |
| **RAM** | 8GB |
| **Disk** | 5GB free (SSD recommended) |
| **CPU** | Quad-core 3GHz+ |
| **GPU** | Optional (for faster AI processing) |

---

## Installation Paths

### Windows
- **Installation**: `C:\Program Files\AI File Organiser\` (or custom)
- **Desktop Shortcut**: `%USERPROFILE%\Desktop\AI File Organiser.bat`
- **Start Menu**: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\`
- **Config**: `%APPDATA%\AI File Organiser\`

### Linux
- **Installation**: `~/AI File Organiser/` (or custom)
- **Desktop Shortcut**: `~/Desktop/ai-file-organiser.desktop`
- **Applications**: `~/.local/share/applications/ai-file-organiser.desktop`
- **Config**: `~/.config/ai-file-organiser/`

### macOS
- **Installation**: `/Applications/AI File Organiser/` (or custom)
- **Config**: `~/Library/Application Support/AI File Organiser/`

---

## Next Steps

After installation:

1. **📖 Read the Quick Start**: [MCP_QUICKSTART.md](MCP_QUICKSTART.md)
2. **🚀 Launch the GUI**: Double-click desktop shortcut
3. **🔌 Try MCP Integration**: "Claude, organize my files"
4. **📚 Read Full Documentation**: [docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md)
5. **💡 Try Workflows**: [examples/mcp_workflows.py](examples/mcp_workflows.py)

---

## Getting Help

### Documentation
- **Quick Start**: MCP_QUICKSTART.md
- **Full Guide**: docs/MCP_INTEGRATION.md
- **Tool Reference**: docs/MCP_TOOLS.md
- **README**: README.md

### Support
- **GitHub**: https://github.com/alexv879/Ai_File_Organiser
- **Issues**: Report bugs on GitHub Issues
- **Contact**: Alexandru Emanuel Vasile

---

## Advanced Installation Options

### Custom Installation Path

Setup wizard allows custom path selection, or manually:
```bash
# Copy files to desired location
cp -r AIFILEORGANISER /custom/path/

# Update Claude Desktop config with new path
```

### Install Without GUI

For servers or headless systems:
```bash
# Install dependencies only
pip install -r requirements.txt

# Skip GUI wizard
python -m src.main --help
```

### Docker Installation (Coming Soon)

```bash
docker pull aifileorganiser/ai-file-organiser
docker run -p 5000:5000 aifileorganiser/ai-file-organiser
```

### Portable Installation

For USB stick or portable use:
1. Copy entire folder to portable drive
2. Run `python launcher.py` from any computer
3. Ollama must be installed on host machine

---

## Security Considerations

### What Gets Installed
- ✅ Local Python packages
- ✅ Local Ollama (AI runs locally)
- ✅ Desktop shortcuts (safe)
- ✅ Config files (local only)

### What Doesn't Get Installed
- ❌ No cloud services
- ❌ No tracking software
- ❌ No telemetry (except optional anonymous update checks)
- ❌ No external data collection

### Privacy
- **All AI processing happens locally** - No data sent to cloud
- **Update checks are anonymous** - No personal information
- **Claude Desktop integration** - Uses MCP protocol (local communication)

---

**Installation should take 5-10 minutes using the automated installer.**

**Need help? Check troubleshooting or contact support!**

---

**Copyright © 2025 Alexandru Emanuel Vasile. All Rights Reserved.**
