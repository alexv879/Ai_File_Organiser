#!/bin/bash
# AI File Organiser - Quick Installer for Linux/macOS
# Copyright © 2025 Alexandru Emanuel Vasile. All Rights Reserved.

echo "========================================"
echo "AI File Organiser - Quick Installer"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo ""
    echo "Please install Python 3.8 or later:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  Fedora/RHEL: sudo dnf install python3 python3-pip"
    echo "  macOS: brew install python3"
    exit 1
fi

echo "Python found!"
python3 --version
echo ""

# Install dependencies
echo "Installing Python dependencies..."
echo ""
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo ""
echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""
echo "To launch: python3 launcher.py"
echo ""
