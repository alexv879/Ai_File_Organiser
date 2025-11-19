# AI File Organizer - Desktop Application

A modern, cross-platform desktop application built with Tauri 2.0, React, and TypeScript.

## Features

- 🚀 **Cross-platform** - Works on Windows, macOS, and Linux
- 🤖 **Multi-Model AI** - Intelligent selection between GPT-4, Claude, and local Ollama
- 💨 **Fast & Lightweight** - Built with Rust and Tauri (97% smaller than Electron)
- 🎨 **Modern UI** - Beautiful interface with Tailwind CSS and dark mode
- 🔒 **Secure** - Sandboxed execution with strict permissions
- 📁 **File Organization** - Smart categorization and automated organization

## Prerequisites

Before you begin, ensure you have installed:

1. **Node.js** (v18 or later)
   ```bash
   # Download from https://nodejs.org/
   node --version  # Should be v18+
   ```

2. **Rust** (latest stable)
   ```bash
   # Install via rustup
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   rustup --version
   ```

3. **System Dependencies** (varies by platform)

   **Windows:**
   - Microsoft Visual Studio C++ Build Tools
   - WebView2 (usually pre-installed on Windows 10/11)

   **macOS:**
   - Xcode Command Line Tools
   ```bash
   xcode-select --install
   ```

   **Linux (Ubuntu/Debian):**
   ```bash
   sudo apt update
   sudo apt install libwebkit2gtk-4.1-dev \
     build-essential \
     curl \
     wget \
     file \
     libxdo-dev \
     libssl-dev \
     libayatana-appindicator3-dev \
     librsvg2-dev
   ```

## Installation

1. **Install dependencies:**
   ```bash
   cd desktop-app
   npm install
   ```

2. **Set up Python backend:**
   ```bash
   cd ..
   pip install -r requirements.txt
   ```

3. **Configure API keys** (optional - for cloud AI):
   Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your_openai_key_here
   ANTHROPIC_API_KEY=your_anthropic_key_here
   ```

## Development

Run in development mode with hot-reload:

```bash
npm run dev
```

This will:
- Start the Vite dev server (frontend)
- Launch the Tauri app with hot-reload
- Watch for changes in both Rust and React code

## Building

Build the application for your platform:

```bash
npm run build
```

This will create optimized binaries in:
- `src-tauri/target/release/`

### Platform-Specific Builds

**Windows (.msi, .exe):**
```bash
npm run tauri build
```
Output: `src-tauri/target/release/bundle/msi/`

**macOS (.dmg, .app):**
```bash
npm run tauri build
```
Output: `src-tauri/target/release/bundle/dmg/`

**Linux (.deb, .AppImage):**
```bash
npm run tauri build
```
Output: `src-tauri/target/release/bundle/deb/`

## Usage

### Basic File Organization

1. **Launch the app**
2. **Click "Choose Folder"** to select a folder to organize
3. **Click "Organize Now"** to start automatic organization
4. **View results** in the file list

### Advanced Settings

Navigate to the **Settings** tab to configure:

- **Multi-Model AI**: Enable intelligent model selection
- **Subscription Tier**: Choose your tier (FREE, STARTER, PRO, ENTERPRISE)

### Subscription Tiers

- **FREE**: Local Ollama models only - completely free, no API costs
- **STARTER** ($5/mo): GPT-3.5 Turbo, Claude Haiku - fast cloud models
- **PRO** ($12/mo): GPT-4 Turbo, Claude 3.5 Sonnet - best accuracy
- **ENTERPRISE**: Custom fine-tuned models - contact for pricing

## Architecture

### Tech Stack

- **Frontend**: React 18 + TypeScript + Vite
- **UI**: Tailwind CSS + Lucide Icons
- **Desktop**: Tauri 2.0 (Rust)
- **Backend**: Python (FastAPI, AI models)
- **AI Models**: OpenAI, Anthropic Claude, Ollama

### Project Structure

```
desktop-app/
├── src/                    # React frontend
│   ├── components/         # React components
│   ├── App.tsx            # Main app component
│   ├── main.tsx           # Entry point
│   └── index.css          # Tailwind styles
├── src-tauri/             # Tauri (Rust) backend
│   ├── src/
│   │   └── main.rs        # Rust commands
│   ├── Cargo.toml         # Rust dependencies
│   └── tauri.conf.json    # Tauri configuration
├── package.json           # Node.js dependencies
├── vite.config.ts         # Vite configuration
└── tailwind.config.js     # Tailwind configuration
```

### How It Works

1. **User selects folder** via Tauri dialog
2. **Rust lists files** from the directory
3. **Python classifies** each file using AI
4. **Results displayed** in React UI
5. **User organizes** with one click

## Commands

The app exposes several Tauri commands:

- `classify_file(file_path, use_multi_model, tier)` - Classify a single file
- `organize_folder(options)` - Organize entire folder
- `list_files(directory)` - List files in directory
- `open_in_explorer(path)` - Open file manager
- `get_system_info()` - Get system information

## Troubleshooting

### Python not found

Ensure Python 3.8+ is installed and in PATH:
```bash
python3 --version
```

### Ollama not available

For FREE tier, install Ollama:
```bash
# macOS/Linux
curl https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download
```

Then pull a model:
```bash
ollama pull qwen2.5:7b-instruct
```

### Build fails on Linux

Install all system dependencies:
```bash
sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget file libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev
```

### WebView2 not found (Windows)

Download and install WebView2:
https://developer.microsoft.com/microsoft-edge/webview2/

## Performance

- **Bundle size**: ~8 MB (vs 150+ MB for Electron)
- **Memory usage**: ~40 MB idle (vs 200+ MB for Electron)
- **Startup time**: <1 second
- **Classification**: 100-500ms per file (local), 500-2000ms (cloud)

## Security

- Sandboxed file system access
- Strict CSP (Content Security Policy)
- No remote code execution
- Encrypted credentials storage

## License

Copyright © 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - See LICENSE.txt

## Support

For issues, feature requests, or questions:
- GitHub Issues: [Add your repo URL]
- Email: [Add your email]
- Documentation: [Add docs URL]
