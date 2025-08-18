# Clipboard History Manager - PowerShell Startup Script
# This script starts the clipboard history application at system startup

# Set execution policy for current session (in case it's restricted)
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Change to the script directory
Set-Location $ScriptDir

Write-Host "Starting Clipboard History Manager..." -ForegroundColor Green

try {
    # Check if Python is installed
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Python is not installed or not in PATH."
        Write-Host "Please install Python 3.8 or higher and try again." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }

    Write-Host "Python detected: $pythonVersion" -ForegroundColor Cyan

    # Check if PyQt6 is installed
    python -c "import PyQt6" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PyQt6 is not installed. Installing required packages..." -ForegroundColor Yellow

        # Install PyQt6
        python -m pip install PyQt6
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to install PyQt6."
            Write-Host "Please install manually using: pip install PyQt6" -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }

        Write-Host "PyQt6 installed successfully." -ForegroundColor Green
    }

    # Start the application
    $appPath = Join-Path $ScriptDir "clipboard_history_app.py"
    if (-not (Test-Path $appPath)) {
        Write-Error "Application file not found: $appPath"
        Read-Host "Press Enter to exit"
        exit 1
    }

    Write-Host "Starting Clipboard History Manager..." -ForegroundColor Green

    # Start the application in hidden mode
    python $appPath --hidden

    Write-Host "Clipboard History Manager has stopped." -ForegroundColor Yellow

} catch {
    Write-Error "An error occurred: $_"
    Read-Host "Press Enter to exit"
    exit 1
}

# Keep the window open if running interactively
if ([Environment]::UserInteractive -and -not [Environment]::GetCommandLineArgs().Contains('-NonInteractive')) {
    Read-Host "Press Enter to exit"
}
