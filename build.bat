@echo off
REM Build script for PSI on Windows
echo === PSI - Build Script (Windows) ===

REM Activate virtualenv if present
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [ok] Virtual environment activated.
)

REM Ensure PyInstaller is available
pip install pyinstaller --quiet
echo [ok] PyInstaller ready.

REM Clean previous artifacts
if exist "build" rmdir /s /q build
if exist "dist"  rmdir /s /q dist
echo [ok] Previous build artifacts removed.

REM Run PyInstaller
echo.
echo Building PSI executable (this may take several minutes)...
pyinstaller PSI.spec --clean --noconfirm

echo.
echo === Build complete! ===
echo Distribution: dist\PSI\
echo Executable:   dist\PSI\PSI.exe
echo.
echo To run: dist\PSI\PSI.exe
pause
