#!/usr/bin/env bash
# Build script for PSI on Linux / macOS
set -euo pipefail

PLATFORM="$(uname -s)"
echo "=== PSI — Build Script ($PLATFORM) ==="

# Activate virtualenv if present
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "[ok] Virtual environment activated."
fi

# Ensure PyInstaller is available
pip install pyinstaller --quiet
echo "[ok] PyInstaller ready."

# Clean previous artifacts
rm -rf build dist
echo "[ok] Previous build artifacts removed."

# Run PyInstaller
echo ""
echo "Building PSI executable (this may take several minutes)..."
pyinstaller PSI.spec --clean --noconfirm

echo ""
echo "=== Build complete! ==="
echo "Distribution: dist/PSI/"
echo "Executable:   dist/PSI/PSI"
echo ""
echo "To run:  ./dist/PSI/PSI"
