@echo off
REM ============================================================================
REM AI File Organiser - One-Click Installer for Windows
REM Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
REM ============================================================================

title AI File Organiser - Installation
color 0B

echo.
echo ========================================================================
echo    AI FILE ORGANISER - ONE-CLICK INSTALLER
echo    Privacy-First Local AI File Organization
echo ========================================================================
echo.
echo This installer will:
echo   1. Check Python installation
echo   2. Install Python dependencies
echo   3. Download and install Ollama (local AI)
echo   4. Pull AI model (llama2)
echo   5. Create desktop shortcuts
echo   6. Configure the application
echo.
echo Installation will take 5-10 minutes depending on your internet speed.
echo.
pause

REM Check Python
echo.
echo ========================================================================
echo STEP 1/5: Checking Python Installation
echo ========================================================================
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python not found!
    echo.
    echo Please install Python 3.8 or higher from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

python --version
echo Python found successfully!

REM Install Python dependencies
echo.
echo ========================================================================
echo STEP 2/5: Installing Python Dependencies
echo ========================================================================
echo This may take a few minutes...
echo.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install Python dependencies!
    echo Please check your internet connection and try again.
    echo.
    pause
    exit /b 1
)

echo.
echo Python dependencies installed successfully!

REM Check/Install Ollama
echo.
echo ========================================================================
echo STEP 3/5: Installing Ollama (Local AI Engine)
echo ========================================================================
echo.

REM Check if Ollama is already installed
ollama --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Ollama is already installed!
    ollama --version
    goto :PullModel
)

echo Ollama not found. Downloading installer...
echo.

REM Download Ollama installer
powershell -Command "Invoke-WebRequest -Uri 'https://ollama.ai/download/OllamaSetup.exe' -OutFile 'OllamaSetup.exe'"

if %errorlevel% neq 0 (
    echo.
    echo WARNING: Could not download Ollama automatically.
    echo.
    echo Please download and install Ollama manually from: https://ollama.ai
    echo After installing Ollama, run this installer again.
    echo.
    pause
    goto :SkipOllama
)

echo.
echo Installing Ollama...
echo This will open a separate installer window.
echo Please follow the prompts to complete Ollama installation.
echo.
pause

start /wait OllamaSetup.exe

REM Clean up installer
del OllamaSetup.exe

echo.
echo Ollama installed successfully!

:PullModel
REM Pull AI model
echo.
echo ========================================================================
echo STEP 4/5: Downloading AI Model (llama2)
echo ========================================================================
echo This may take 5-10 minutes depending on your internet speed...
echo Model size: approximately 4GB
echo.

ollama pull llama2

if %errorlevel% neq 0 (
    echo.
    echo WARNING: Could not download llama2 model.
    echo You can download it later by running: ollama pull llama2
    echo.
    goto :SkipOllama
)

echo.
echo AI model downloaded successfully!

:SkipOllama

REM Create configuration
echo.
echo ========================================================================
echo STEP 5/5: Creating Configuration
echo ========================================================================
echo.

if not exist config.json (
    echo Creating default configuration...

    REM Create default config.json
    (
        echo {
        echo   "watched_folders": [
        echo     "%USERPROFILE%\\Downloads"
        echo   ],
        echo   "base_destination": "%USERPROFILE%\\Organized",
        echo   "auto_mode": false,
        echo   "dry_run": true,
        echo   "enable_ai": true,
        echo   "classification": {
        echo     "enable_ai": true,
        echo     "ai_confidence_threshold": 0.7
        echo   },
        echo   "ollama_base_url": "http://localhost:11434",
        echo   "ollama_model": "llama2",
        echo   "safety": {
        echo     "enable_guardian": true,
        echo     "protected_folders": [
        echo       "C:\\Windows",
        echo       "C:\\Program Files",
        echo       "C:\\Program Files (x86)",
        echo       "%USERPROFILE%\\AppData"
        echo     ]
        echo   }
        echo }
    ) > config.json

    echo Configuration created successfully!
) else (
    echo Configuration file already exists, skipping...
)

REM Create desktop shortcut
echo.
echo Creating desktop shortcuts...

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\AI File Organiser.lnk'); $Shortcut.TargetPath = 'python'; $Shortcut.Arguments = '%CD%\launcher.py'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.IconLocation = 'shell32.dll,4'; $Shortcut.Save()"

if %errorlevel% equ 0 (
    echo Desktop shortcut created!
)

REM Installation complete
echo.
echo ========================================================================
echo    INSTALLATION COMPLETE!
echo ========================================================================
echo.
echo AI File Organiser is now installed and ready to use!
echo.
echo NEXT STEPS:
echo   1. Double-click "AI File Organiser" on your desktop
echo   2. Or run: python launcher.py
echo   3. Or use CLI: python -m src.cli.commands
echo.
echo QUICK START:
echo   - Dashboard:  python src\main.py dashboard
echo   - Watch mode: python src\main.py watch
echo   - Find dupes: python src\main.py duplicates
echo.
echo PRIVACY NOTICE:
echo   ✅ All processing happens on YOUR computer
echo   ✅ No data is sent to the cloud
echo   ✅ Your files stay private and secure
echo.
echo For help and documentation, see README.md
echo.
pause
