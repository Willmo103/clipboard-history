@echo off
REM Clipboard History Manager - Windows Startup Script
REM This script starts the clipboard history application at system startup

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Change to the script directory
cd /d "%SCRIPT_DIR%"

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher and try again.
    pause
    exit /b 1
)

REM Check if required packages are installed
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo PyQt6 is not installed. Installing required packages...
    python -m pip install PyQt6
    if errorlevel 1 (
        echo Failed to install PyQt6. Please install manually:
        echo pip install PyQt6
        pause
        exit /b 1
    )
)

REM Start the clipboard history application in hidden mode
echo Starting Clipboard History Manager...
python "%SCRIPT_DIR%clipboard_history_app.py" --hidden

REM If we get here, the application has exited
echo Clipboard History Manager has stopped.
pause
