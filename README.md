# Enhanced Clipboard History Manager

A comprehensive clipboard history application with advanced features including file handling, image support, JSON export, and automatic backup functionality. Similar to Windows 11's clipboard history but with enhanced capabilities for power users.

## 🚀 Key Features

### Core Functionality

- **Infinite History**: Store unlimited clipboard entries in SQLite database
- **Multi-Content Support**: Text, files (as URIs), and images (as Base64)
- **System Tray Integration**: Runs silently with intelligent tray behavior
- **Global Hotkey**: Quick access with Ctrl+Shift+V
- **Smart Auto-Hide**: Window closes when losing focus (when opened from tray)

### Advanced Features

- **File Handling**: Capture file paths with metadata (size, type, thumbnails)
- **Image Support**: Store and preview images with thumbnails
- **JSON Export**: Export history with optional favorites-only filter
- **Automatic Backup**: Auto-sync new items to JSON export on startup
- **Rich Preview**: Tabbed interface showing text, images, and file details
- **Type Filtering**: Filter by content type (Text/Files/Images/All)

### User Experience

- **Search & Filter**: Real-time search with multiple filter options
- **Favorites System**: Star important entries for quick access
- **URL Detection**: Automatic hyperlink detection and click-to-open
- **File Integration**: Click to open files in default applications
- **Access Statistics**: Track usage frequency and timestamps

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

### Enhanced Tray Behavior

- **Single Click Tray**: Opens/closes the main window
- **Auto-Hide**: Window automatically hides when losing focus (if opened from tray)
- **Stay Open Mode**: Double-click items or use hotkey to keep window open
- **Recent Items Menu**: Right-click tray for quick access to last 5 items

### Content Types

#### 📝 Text Content

- Plain text with automatic URL detection
- Clickable links in preview
- Search through text content

#### 📁 File Content

- Stores file paths as URIs
- Shows file metadata (size, type, location)
- Thumbnail generation for image files
- Click to open files in default applications
- File existence validation

#### 🖼️ Image Content

- Images stored as Base64 strings
- Thumbnail previews in list and detail view
- Click to view full-size images
- Supports all common image formats

### Interface Features

#### Main Window

- **Tabbed Preview**: Separate tabs for text and image content
- **Type Filter Dropdown**: Filter by All/Text/Files/Images
- **Enhanced Search**: Search across content and file paths
- **Favorites Toggle**: Quick access to starred items
- **Rich Details Panel**: Metadata, timestamps, and access statistics

#### Actions Available

- **Copy to Clipboard**: Preserves original format (text/file/image)
- **Open/View**:
  - Files: Opens in default application
  - URLs: Opens in default browser
  - Images: Temporary view in system image viewer
- **Toggle Favorite**: Star/unstar for quick access
- **Delete**: Remove unwanted entries
- **Export JSON**: Export with optional favorites-only filter

#### System Tray Features

- **Type-Aware Menu**: Icons show content type (📁📝🖼️🔗)
- **Quick Copy**: Click any recent item to copy
- **Export Shortcut**: Quick export from tray menu
- **Smart Notifications**: Shows content type when copying

### Keyboard Shortcuts

- `Ctrl+Shift+V`: Toggle clipboard history window (global hotkey)
- `Double-click`: Copy item to clipboard
- `Enter`: Copy selected item
- `Delete`: Remove selected item
- `Ctrl+F`: Focus search bar
- `Esc`: Hide window (when opened from tray)

## Export & Backup

### JSON Export Format

```json
{
  "export_info": {
    "timestamp": "2024-01-01T12:00:00",
    "total_items": 150,
    "favorites_only": false,
    "version": "1.0"
  },
  "items": [
    {
      "id": 1,
      "content": "Sample text or Base64 image data",
      "content_type": "text|file|image",
      "file_path": "/path/to/file.txt",
      "file_size": 1024,
      "mime_type": "text/plain",
      "thumbnail": "base64_thumbnail_data",
      "timestamp": "2024-01-01T12:00:00",
      "is_favorite": true,
      "access_count": 5
    }
  ]
}
```

### Automatic Backup System

- **Startup Sync**: Automatically backs up new items on app start
- **Incremental Updates**: Only syncs items not previously backed up
- **Export Ready**: JSON export file always up-to-date
- **Background Operation**: No user intervention required

### Manual Export Options

- **Full Export**: All clipboard history items
- **Favorites Only**: Export only starred items
- **Custom Location**: Choose export file location
- **Progress Tracking**: Visual progress during large exports

## Enhanced Database Schema

The SQLite database now includes:

- `content`: Main clipboard content (text/Base64 image/file path)
- `content_type`: Type indicator (text/file/image)
- `file_path`: Original file location (for file type)
- `file_size`: File size in bytes
- `mime_type`: MIME type for proper handling
- `thumbnail`: Thumbnail image data (for files/images)
- `backed_up`: Flag indicating if item is in JSON backup

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

- **v1.1**: Added features
- Improved performance and stability
- Added support for image and file content

- **v1.0**: Initial release with core functionality
  - Infinite clipboard history
  - System tray integration
  - Cross-platform startup scripts
  - Search and favorites
  - Global hotkeys
