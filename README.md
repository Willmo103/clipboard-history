# Clipboard History Manager

A comprehensive clipboard history application similar to Windows 11's clipboard history, featuring infinite storage using SQLite database, system tray integration, and cross-platform support.

## Features

- **Infinite History**: Store unlimited clipboard entries in SQLite database
- **System Tray Integration**: Runs silently in background with tray icon
- **Global Hotkey**: Quick access with Ctrl+Shift+V
- **Search & Filter**: Find clipboard entries quickly
- **Favorites System**: Mark important entries as favorites
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Auto-Start Scripts**: Easy startup configuration for all platforms
- **Duplicate Prevention**: Automatically handles duplicate entries
- **Rich Preview**: Full preview of clipboard content
- **Access Statistics**: Track usage frequency

## Installation

### Prerequisites

- Python 3.8 or higher
- PyQt6

### Quick Setup

1. **Download/Clone the application files**
2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   Or manually:

   ```bash
   pip install PyQt6
   ```

3. **Run the application:**

   ```bash
   python clipboard_history_app.py
   ```

## Startup Configuration

The application includes startup scripts for all major platforms:

### Windows

#### Method 1: Using CMD Script

1. Place `start_clipboard_manager.cmd` in your startup folder:
   - Press `Win + R`, type `shell:startup`, press Enter
   - Copy the `.cmd` file to this folder
2. The application will start automatically on system boot

#### Method 2: Using PowerShell Script

1. Place `start_clipboard_manager.ps1` in your startup folder
2. You may need to adjust PowerShell execution policy:

   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

### Linux

1. Make the shell script executable:

   ```bash
   chmod +x start_clipboard_manager.sh
   ```

2. **For Ubuntu/GNOME:**
   - Open "Startup Applications"
   - Add new startup program pointing to the `.sh` script

3. **For other distributions:**
   - Add the script to your desktop environment's autostart folder
   - Usually located at `~/.config/autostart/`

### macOS

1. Make the shell script executable:

   ```bash
   chmod +x start_clipboard_manager.sh
   ```

2. **Using Login Items:**
   - System Preferences → Users & Groups → Login Items
   - Add the shell script to login items

3. **Using LaunchAgent (Advanced):**
   - Create a `.plist` file in `~/Library/LaunchAgents/`

## Usage

### Basic Operations

- **Start Application**: Run any of the startup scripts or execute directly
- **Open History Window**:
  - Use global hotkey `Ctrl+Shift+V`
  - Double-click system tray icon
  - Right-click tray icon → "Show Clipboard History"

### Interface Features

#### Main Window

- **Search Bar**: Type to filter clipboard entries
- **Favorites Filter**: Toggle to show only starred items
- **History List**: All clipboard entries with timestamps
- **Preview Panel**: Full content preview of selected item

#### Actions

- **Copy to Clipboard**: Double-click item or use "Copy" button
- **Add/Remove Favorite**: Star/unstar important entries
- **Delete Item**: Remove unwanted entries
- **Clear History**: Remove all entries (keeps favorites)

#### System Tray

- **Recent Items Menu**: Quick access to last 5 clipboard entries
- **Click to Copy**: Select any recent item to copy it
- **Show/Hide Window**: Double-click tray icon

### Keyboard Shortcuts

- `Ctrl+Shift+V`: Open clipboard history window (global hotkey)
- `Double-click`: Copy item to clipboard
- `Delete`: Remove selected item
- `Ctrl+F`: Focus search bar (when window is active)

## Database

The application uses SQLite database (`clipboard_history.db`) to store:

- Clipboard content
- Timestamps
- Content type
- Favorite status
- Access count statistics
- Content hash (for duplicate detection)

### Database Location

- **Windows**: Same folder as application
- **Linux/macOS**: Same folder as application
- Customizable in the code by modifying `DatabaseManager` initialization

## Configuration

### Settings Storage

Application settings are stored using Qt's QSettings:

- **Windows**: Windows Registry
- **Linux**: `~/.config/ClipboardHistory/`
- **macOS**: `~/Library/Preferences/`

### Customization Options

You can modify the following in the source code:

```python
# Database file location
db_manager = DatabaseManager("custom_path/clipboard_history.db")

# History limit in UI (0 = unlimited)
items = self.db_manager.get_clipboard_history(limit=1000)

# Global hotkey
self.show_hotkey = QShortcut(QKeySequence("Ctrl+Alt+V"), self.main_widget)

# Monitoring interval (milliseconds)
self.msleep(100)  # Check clipboard every 100ms
```

## Troubleshooting

### Common Issues

1. **Application won't start**
   - Check Python installation: `python --version`
   - Install PyQt6: `pip install PyQt6`
   - Run with: `python clipboard_history_app.py`

2. **System tray icon not visible**
   - Ensure system tray is enabled in your OS
   - Check if application is running in task manager
   - Try restarting the application

3. **Global hotkey not working**
   - Check if another application is using the same hotkey
   - Try running the application as administrator (Windows)
   - Verify desktop environment support (Linux)

4. **Database errors**
   - Check write permissions in application directory
   - Delete `clipboard_history.db` to reset (loses history)
   - Ensure SQLite is available (usually built into Python)

### Platform-Specific Issues

#### Windows

- **PowerShell execution policy**: Run as administrator and execute:

  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

#### Linux

- **Missing dependencies**: Install system packages:

  ```bash
  # Ubuntu/Debian
  sudo apt-get install python3-pyqt6

  # Fedora
  sudo dnf install python3-qt6
  ```

- **Wayland compatibility**: May require additional configuration for global hotkeys

#### macOS

- **Security permissions**: Grant accessibility permissions in System Preferences
- **Path issues**: Ensure Python is in system PATH

## Development

### File Structure

```
clipboard-history-manager/
├── clipboard_history_app.py      # Main application
├── requirements.txt               # Python dependencies
├── start_clipboard_manager.cmd    # Windows CMD startup script
├── start_clipboard_manager.ps1    # PowerShell startup script
├── start_clipboard_manager.sh     # Linux/macOS shell script
└── README.md                      # This file
```

### Key Components

1. **DatabaseManager**: Handles SQLite operations
2. **ClipboardMonitor**: Background thread monitoring clipboard
3. **ClipboardHistoryWidget**: Main UI component
4. **ClipboardHistoryApp**: System tray and application lifecycle

### Extending the Application

To add new features:

```python
# Add new database fields
cursor.execute('''
    ALTER TABLE clipboard_history
    ADD COLUMN new_field TEXT DEFAULT ''
''')

# Add new UI components
new_button = QPushButton("New Feature")
new_button.clicked.connect(self.new_feature_handler)
layout.addWidget(new_button)

# Add new tray menu items
new_action = QAction("New Action", self.app)
new_action.triggered.connect(self.new_action_handler)
tray_menu.addAction(new_action)
```

## License

This project is open source. Feel free to modify and distribute according to your needs.

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Verify your Python and PyQt6 installation
3. Test with a fresh database file
4. Run in debug mode for detailed error messages

## Version History

- **v1.0**: Initial release with core functionality
  - Infinite clipboard history
  - System tray integration
  - Cross-platform startup scripts
  - Search and favorites
  - Global hotkeys
