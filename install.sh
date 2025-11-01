#!/bin/bash
# AI File Organiser - Linux/macOS Setup Script
# Copyright © 2025 Alexandru Emanuel Vasile. All rights reserved.

set -e  # Exit on error

echo "============================================================"
echo "  AI File Organiser - Automated Setup"
echo "  Copyright © 2025 Alexandru Emanuel Vasile"
echo "============================================================"
echo ""

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    echo "Please install Python 3.8 or later"
    exit 1
fi

echo "[1/3] Installing Python dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
echo "[SUCCESS] Python dependencies installed"
echo ""

echo "[2/3] Setting up Ollama..."
python3 setup_ollama.py
echo ""

echo "[3/3] Verifying installation..."
python3 -m src.main --help > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "[ERROR] Application verification failed"
    exit 1
fi

echo ""
echo "============================================================"
echo "  Setup Complete!"
echo "============================================================"
echo ""
echo "You can now run AI File Organiser:"
echo "  - Dashboard: ./run_dashboard.sh"
echo "  - Or: python3 -m src.main dashboard"
echo ""

# Make scripts executable
chmod +x run_dashboard.sh setup_ollama.py
