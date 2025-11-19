# Tauri Desktop Application Setup Guide

This guide will help you set up and develop the Tauri-based desktop application for AI File Organizer 2.0.

## Why Tauri?

- **97% smaller**: 3-10MB vs 150MB+ (Electron)
- **80% less RAM**: 30-40MB vs 200MB+ (Electron)
- **Memory-safe**: Rust backend prevents common vulnerabilities
- **Secure by default**: Sandboxed with fine-grained API permissions
- **Cross-platform**: Windows, macOS, Linux from single codebase

## Prerequisites

### 1. Install Rust

```bash
# Linux/macOS
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Windows
# Download and run: https://rustup.rs

# Verify installation
rustc --version
cargo --version
```

### 2. Install Node.js and npm

```bash
# Install Node.js 18+ (LTS)
# Download from: https://nodejs.org

# Verify installation
node --version  # Should be 18.0.0 or higher
npm --version
```

### 3. Install Tauri CLI

```bash
cargo install tauri-cli
# Or via npm
npm install -g @tauri-apps/cli
```

### 4. Platform-Specific Dependencies

**Linux (Debian/Ubuntu):**
```bash
sudo apt update
sudo apt install libwebkit2gtk-4.0-dev \
    build-essential \
    curl \
    wget \
    file \
    libssl-dev \
    libgtk-3-dev \
    libayatana-appindicator3-dev \
    librsvg2-dev
```

**macOS:**
```bash
# Install Xcode Command Line Tools
xcode-select --install
```

**Windows:**
```powershell
# Install Microsoft Visual Studio C++ Build Tools
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

## Project Structure

```
desktop-app/
├── src/                    # React frontend
│   ├── components/
│   │   ├── Dashboard.tsx
│   │   ├── FileList.tsx
│   │   ├── Settings.tsx
│   │   ├── OrganizeButton.tsx
│   │   └── Login.tsx
│   ├── hooks/
│   │   ├── useFiles.ts
│   │   ├── useAuth.ts
│   │   └── useSettings.ts
│   ├── lib/
│   │   ├── api.ts
│   │   └── types.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── styles.css
│
├── src-tauri/              # Rust backend
│   ├── src/
│   │   ├── main.rs        # Entry point
│   │   ├── commands.rs    # Tauri commands
│   │   ├── python_bridge.rs  # Python AI engine bridge
│   │   ├── storage.rs     # Secure storage
│   │   └── lib.rs
│   ├── Cargo.toml         # Rust dependencies
│   └── tauri.conf.json    # Tauri configuration
│
├── public/                 # Static assets
│   └── icons/
│
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## Initial Setup

### 1. Create Tauri Project

```bash
cd /home/user/Ai_File_Organiser/desktop-app

# Create new Tauri project with React + TypeScript
npm create tauri-app@latest

# When prompted:
# - Project name: ai-file-organizer
# - Package manager: npm
# - UI template: React
# - TypeScript: Yes
# - Variant: TypeScript
```

### 2. Install Dependencies

```bash
npm install

# Install additional dependencies
npm install @tanstack/react-query axios zustand
npm install -D tailwindcss postcss autoprefixer
npm install lucide-react  # Icons
npm install react-router-dom  # Routing
```

### 3. Set Up Tailwind CSS

```bash
npx tailwindcss init -p
```

Edit `tailwind.config.js`:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### 4. Configure Tauri

Edit `src-tauri/tauri.conf.json`:

```json
{
  "build": {
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build",
    "devPath": "http://localhost:5173",
    "distDir": "../dist"
  },
  "package": {
    "productName": "AI File Organizer",
    "version": "2.0.0"
  },
  "tauri": {
    "allowlist": {
      "all": false,
      "fs": {
        "all": false,
        "readFile": true,
        "writeFile": true,
        "readDir": true,
        "copyFile": true,
        "createDir": true,
        "removeDir": true,
        "removeFile": true,
        "renameFile": true,
        "exists": true,
        "scope": [
          "$HOME/**",
          "$DOCUMENT/**",
          "$DOWNLOAD/**",
          "$DESKTOP/**"
        ]
      },
      "dialog": {
        "all": true,
        "open": true,
        "save": true,
        "message": true,
        "ask": true,
        "confirm": true
      },
      "shell": {
        "all": false,
        "execute": true,
        "sidecar": true,
        "scope": [
          {
            "name": "python-engine",
            "cmd": "python3",
            "args": ["-m", "src.main"]
          }
        ]
      },
      "http": {
        "all": true,
        "request": true,
        "scope": [
          "http://localhost:8000/**",
          "http://localhost:11434/**"
        ]
      },
      "notification": {
        "all": true
      },
      "path": {
        "all": true
      },
      "os": {
        "all": true
      }
    },
    "bundle": {
      "active": true,
      "category": "Utility",
      "copyright": "Copyright © 2025",
      "deb": {
        "depends": ["python3", "python3-pip"]
      },
      "externalBin": [],
      "icon": [
        "icons/32x32.png",
        "icons/128x128.png",
        "icons/128x128@2x.png",
        "icons/icon.icns",
        "icons/icon.ico"
      ],
      "identifier": "com.aifileorganizer.app",
      "longDescription": "AI-powered file organization with local processing",
      "macOS": {
        "entitlements": null,
        "exceptionDomain": "",
        "frameworks": [],
        "providerShortName": null,
        "signingIdentity": null
      },
      "resources": ["../src/**/*.py"],
      "shortDescription": "AI File Organizer",
      "targets": "all",
      "windows": {
        "certificateThumbprint": null,
        "digestAlgorithm": "sha256",
        "timestampUrl": ""
      }
    },
    "security": {
      "csp": "default-src 'self'; connect-src 'self' http://localhost:8000 http://localhost:11434; style-src 'self' 'unsafe-inline'; script-src 'self' 'wasm-unsafe-eval'"
    },
    "updater": {
      "active": false
    },
    "windows": [
      {
        "fullscreen": false,
        "height": 800,
        "resizable": true,
        "title": "AI File Organizer",
        "width": 1200,
        "minWidth": 800,
        "minHeight": 600,
        "center": true
      }
    ],
    "systemTray": {
      "iconPath": "icons/icon.png",
      "iconAsTemplate": true,
      "menuOnLeftClick": false
    }
  }
}
```

## Rust Backend Implementation

### 1. Main Rust Code (`src-tauri/src/main.rs`)

```rust
// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod python_bridge;

use commands::*;

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            greet,
            organize_file,
            get_pending_files,
            start_python_backend,
            classify_file
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### 2. Tauri Commands (`src-tauri/src/commands.rs`)

```rust
use std::path::PathBuf;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct FileClassification {
    pub category: String,
    pub confidence: f32,
    pub suggested_path: String,
}

#[tauri::command]
pub fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to AI File Organizer 2.0", name)
}

#[tauri::command]
pub async fn classify_file(file_path: String) -> Result<FileClassification, String> {
    // Call Python backend via HTTP
    let client = reqwest::Client::new();
    let response = client
        .post("http://localhost:8000/api/classify")
        .json(&serde_json::json!({
            "file_path": file_path
        }))
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let classification = response.json::<FileClassification>()
        .await
        .map_err(|e| e.to_string())?;

    Ok(classification)
}

#[tauri::command]
pub async fn organize_file(
    file_path: String,
    destination: String
) -> Result<String, String> {
    // Move file to destination
    let source = PathBuf::from(&file_path);
    let dest = PathBuf::from(&destination);

    std::fs::rename(&source, &dest)
        .map_err(|e| e.to_string())?;

    Ok(format!("Moved {} to {}", file_path, destination))
}

#[tauri::command]
pub async fn get_pending_files() -> Result<Vec<String>, String> {
    // Get pending files from Python backend
    let client = reqwest::Client::new();
    let response = client
        .get("http://localhost:8000/api/pending-files")
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let files = response.json::<Vec<String>>()
        .await
        .map_err(|e| e.to_string())?;

    Ok(files)
}

#[tauri::command]
pub async fn start_python_backend() -> Result<String, String> {
    // Start Python backend server
    // This would use Command to spawn the Python process
    Ok("Python backend started".to_string())
}
```

## React Frontend Implementation

### 1. Main App (`src/App.tsx`)

```typescript
import { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import Dashboard from './components/Dashboard';
import Login from './components/Login';

interface User {
  username: string;
  email: string;
}

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in
    const token = localStorage.getItem('auth_token');
    if (token) {
      // Verify token and get user info
      fetchUser(token);
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUser = async (token: string) => {
    try {
      const response = await fetch('http://localhost:8000/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        localStorage.removeItem('auth_token');
      }
    } catch (error) {
      console.error('Failed to fetch user:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = (userData: User, token: string) => {
    setUser(userData);
    localStorage.setItem('auth_token', token);
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('auth_token');
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="App">
      {user ? (
        <Dashboard user={user} onLogout={handleLogout} />
      ) : (
        <Login onLogin={handleLogin} />
      )}
    </div>
  );
}

export default App;
```

## Development Commands

```bash
# Development mode (hot reload)
npm run tauri dev

# Build for production
npm run tauri build

# Test Rust backend
cd src-tauri
cargo test

# Run Rust clippy (linter)
cargo clippy

# Format Rust code
cargo fmt
```

## Building for Distribution

### Windows

```bash
npm run tauri build -- --target x86_64-pc-windows-msvc
# Output: src-tauri/target/release/bundle/msi/
```

### macOS

```bash
npm run tauri build -- --target x86_64-apple-darwin
# Output: src-tauri/target/release/bundle/macos/
```

### Linux

```bash
npm run tauri build -- --target x86_64-unknown-linux-gnu
# Output: src-tauri/target/release/bundle/deb/ or /appimage/
```

## Code Signing (Production)

### Windows

```bash
# Install signtool
# Sign the .msi installer
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com app.msi
```

### macOS

```bash
# Sign app
codesign --force --deep --sign "Developer ID Application: Your Name" app.app

# Notarize with Apple
xcrun altool --notarize-app --primary-bundle-id "com.aifileorganizer.app" \\
  --username "your@email.com" --password "@keychain:AC_PASSWORD" \\
  --file app.dmg
```

## Next Steps

1. Implement all React components
2. Add state management (Zustand)
3. Implement file drag-and-drop
4. Add system tray integration
5. Implement auto-updater
6. Add crash reporting (Sentry)
7. Write E2E tests (Playwright)

## Resources

- [Tauri Documentation](https://tauri.app/v1/guides/)
- [Tauri API Reference](https://tauri.app/v1/api/js/)
- [React Documentation](https://react.dev/)
- [Rust Book](https://doc.rust-lang.org/book/)
