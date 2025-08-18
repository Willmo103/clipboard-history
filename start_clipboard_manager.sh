#!/bin/bash

# Clipboard History Manager - Unix/Linux/macOS Startup Script
# This script starts the clipboard history application at system startup

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

echo -e "${GREEN}Starting Clipboard History Manager...${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install packages using pip
install_python_packages() {
    echo -e "${YELLOW}Installing required Python packages...${NC}"

    # Try pip3 first, then pip
    if command_exists pip3; then
        pip3 install PyQt6
    elif command_exists pip; then
        pip install PyQt6
    else
        echo -e "${RED}Error: pip is not installed.${NC}"
        return 1
    fi

    return $?
}

# Check if Python is installed
if command_exists python3; then
    PYTHON_CMD="python3"
elif command_exists python; then
    # Check if it's Python 3
    if python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}Error: Python 3.8 or higher is required.${NC}"
        echo "Please install Python 3.8+ and try again."
        exit 1
    fi
else
    echo -e "${RED}Error: Python is not installed.${NC}"
    echo "Please install Python 3.8 or higher and try again."
    exit 1
fi

# Display Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo -e "${CYAN}Python detected: $PYTHON_VERSION${NC}"

# Check if PyQt6 is installed
$PYTHON_CMD -c "import PyQt6" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}PyQt6 is not installed. Installing required packages...${NC}"

    # Install required packages
    if ! install_python_packages; then
        echo -e "${RED}Failed to install PyQt6.${NC}"
        echo "Please install manually using: pip install PyQt6"
        exit 1
    fi

    echo -e "${GREEN}PyQt6 installed successfully.${NC}"
fi

# Check if the main application file exists
APP_PATH="$SCRIPT_DIR/clipboard_history_app.py"
if [ ! -f "$APP_PATH" ]; then
    echo -e "${RED}Error: Application file not found: $APP_PATH${NC}"
    exit 1
fi

# Make sure the application file is executable
chmod +x "$APP_PATH"

# Start the application
echo -e "${GREEN}Starting Clipboard History Manager...${NC}"

# Check if we're running in a desktop environment
if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ] || [[ "$OSTYPE" == "darwin"* ]]; then
    # Start the application in hidden mode
    $PYTHON_CMD "$APP_PATH" --hidden &
    APP_PID=$!

    echo -e "${GREEN}Clipboard History Manager started with PID: $APP_PID${NC}"
    echo -e "${CYAN}Use Ctrl+Shift+V to open the clipboard history window.${NC}"

    # Wait for the application to finish
    wait $APP_PID
    echo -e "${YELLOW}Clipboard History Manager has stopped.${NC}"
else
    echo -e "${RED}Error: No desktop environment detected.${NC}"
    echo "This application requires a graphical desktop environment."
    exit 1
fi
