@echo off
REM AI File Organiser - Windows Setup Script
REM Copyright (C) 2025 Alexandru Emanuel Vasile. All rights reserved.

echo ============================================================
echo   AI File Organiser - Automated Setup
echo   Copyright (C) 2025 Alexandru Emanuel Vasile
echo ============================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8 or later from https://www.python.org
    pause
    exit /b 1
)

echo [1/3] Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies
    pause
    exit /b 1
)
echo [SUCCESS] Python dependencies installed
echo.

echo [2/3] Setting up Ollama...
python setup_ollama.py
if %errorlevel% neq 0 (
    echo [ERROR] Ollama setup failed
    pause
    exit /b 1
)
echo.

echo [3/3] Verifying installation...
python -m src.main --help >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Application verification failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo You can now run AI File Organiser:
echo   - Dashboard: run_dashboard.bat
echo   - Or: python -m src.main dashboard
echo.
pause
