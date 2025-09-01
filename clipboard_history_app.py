#!/usr/bin/env python3
"""
Enhanced Clipboard History Manager
A comprehensive clipboard history application with file/image support, JSON export,
automatic backup, and improved UI features.
"""

import sys
import os
import base64
from urllib.parse import urlparse


from PyQt6.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
    QMenu,
    QMessageBox,
)
from PyQt6.QtCore import (
    Qt,
    QSettings,
    QUrl,
    QMimeData,
)
from PyQt6.QtGui import (
    QIcon,
    QPixmap,
    QAction,
    QKeySequence,
    QShortcut,
)

from clipboard_history_widget import ClipboardHistoryWidget
from clipboard_monitor import ClipboardMonitor
from database_manager import DatabaseManager


class ClipboardHistoryApp:
    """Enhanced main application class."""

    def __init__(self):
        self.show_hotkey = None
        self.recent_items_actions = None
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Initialize database
        self.db_manager = DatabaseManager()

        # Perform startup backup
        self.perform_startup_backup()

        # Initialize clipboard monitor
        self.clipboard_monitor = ClipboardMonitor()
        self.clipboard_monitor.clipboard_changed.connect(
            self.on_clipboard_changed
        )

        # Initialize main widget
        self.main_widget = ClipboardHistoryWidget(self.db_manager)

        # Setup system tray
        self.setup_system_tray()

        # Setup global hotkeys
        self.setup_hotkeys()

        # Settings
        self.settings = QSettings("ClipboardHistory", "ClipboardHistoryApp")
        self.load_settings()

        # Start clipboard monitoring
        self.clipboard_monitor.start()

    def perform_startup_backup(self):
        """Perform automatic backup on startup."""
        try:
            backed_up_count = self.db_manager.backup_unsynced_items()
            if backed_up_count > 0:
                print(f"Backed up {backed_up_count} new items to JSON export")
        except Exception as e:
            print(f"Startup backup failed: {e}")

    def setup_system_tray(self):
        """Setup enhanced system tray."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(
                None,
                "System Tray",
                "System tray not available on this system.",
            )
            sys.exit(1)

        self.tray_icon = QSystemTrayIcon()

        # Create icon
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.blue)
        icon = QIcon(pixmap)
        self.tray_icon.setIcon(icon)

        # Create tray menu
        tray_menu = QMenu()

        show_action = QAction("Show Clipboard History", self.app)
        show_action.triggered.connect(self.show_main_window)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        # Recent items (enhanced with type indicators)
        self.recent_items_actions = []
        for i in range(5):
            action = QAction("", self.app)
            action.setVisible(False)
            tray_menu.addAction(action)
            self.recent_items_actions.append(action)

        tray_menu.addSeparator()

        # Export action
        export_action = QAction("Export History...", self.app)
        export_action.triggered.connect(self.quick_export)
        tray_menu.addAction(export_action)

        quit_action = QAction("Quit", self.app)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

        self.update_tray_menu()

    def quick_export(self):
        """Quick export from tray menu."""
        try:
            export_path = self.db_manager.backup_path
            item_count = self.db_manager.export_to_json(
                export_path, favorites_only=False
            )
            self.tray_icon.showMessage(
                "Export Complete",
                f"Exported {item_count} items to {export_path.name}",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )
        except Exception as e:
            self.tray_icon.showMessage(
                "Export Error",
                f"Failed to export: {str(e)}",
                QSystemTrayIcon.MessageIcon.Critical,
                3000,
            )

    def setup_hotkeys(self):
        """Setup global hotkeys."""
        self.show_hotkey = QShortcut(
            QKeySequence("Ctrl+Shift+V"), self.main_widget
        )
        self.show_hotkey.activated.connect(self.show_main_window)

    def update_tray_menu(self):
        """Update tray menu with type-aware recent items."""
        recent_items = self.db_manager.get_clipboard_history(limit=5)

        for i, action in enumerate(self.recent_items_actions):
            if i < len(recent_items):
                item = recent_items[i]
                content = item[1]
                content_type = item[2]
                file_path = item[3]

                # Create preview based on type
                if content_type == "file":
                    preview = f"📁 {os.path.basename(file_path) if file_path else 'File'}"
                elif content_type == "image":
                    preview = "🖼️ Image"
                else:
                    preview = (
                        content[:50].replace("\n", " ").replace("\r", " ")
                    )
                    if len(content) > 50:
                        preview += "..."
                    if self.is_url(content.strip()):
                        preview = f"🔗 {preview}"

                action.setText(preview)
                action.setVisible(True)
                action.triggered.disconnect()
                action.triggered.connect(
                    lambda checked, item=item: self.copy_from_tray(item)
                )
            else:
                action.setVisible(False)

    def is_url(self, text):
        """Check if text is a URL."""
        try:
            result = urlparse(text)
            return all([result.scheme, result.netloc])
        except:  # noqa E722
            return False

    def copy_from_tray(self, item):
        """Copy item to clipboard from tray menu with type handling."""
        content = item[1]
        content_type = item[2]
        file_path = item[3]

        clipboard = QApplication.clipboard()

        try:
            if content_type == "text":
                clipboard.setText(content)
            elif content_type == "file" and file_path:
                if os.path.exists(file_path):
                    mime_data = QMimeData()
                    mime_data.setUrls([QUrl.fromLocalFile(file_path)])
                    clipboard.setMimeData(mime_data)
                else:
                    clipboard.setText(content)
            elif content_type == "image":
                image_data = base64.b64decode(content)
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                clipboard.setPixmap(pixmap)

            # Show notification
            self.tray_icon.showMessage(
                "Clipboard Updated",
                f"Copied {content_type} to clipboard",
                QSystemTrayIcon.MessageIcon.Information,
                1500,
            )
        except Exception as e:
            print(f"Error copying from tray: {e}")

    def on_tray_activated(self, reason):
        """Handle tray icon activation - single click now shows window."""
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_main_window()

    def show_main_window(self):
        """Show main window with enhanced focus handling."""
        if self.main_widget.isVisible():
            # If already visible, hide it
            self.main_widget.hide()
        else:
            # Show from tray with auto-hide on focus loss
            self.main_widget.show_from_tray()
            self.main_widget.load_history()  # Refresh

    def on_clipboard_changed(self, content, content_type, metadata):
        """Handle clipboard changes with enhanced metadata."""
        success = self.db_manager.add_clipboard_item(
            content=content,
            content_type=content_type,
            file_path=metadata.get("file_path"),
            file_size=metadata.get("file_size"),
            mime_type=metadata.get("mime_type"),
            thumbnail=metadata.get("thumbnail"),
        )

        if success:
            self.update_tray_menu()

            # Update main window if visible
            if self.main_widget.isVisible():
                self.main_widget.load_history()

    def load_settings(self):
        """Load application settings."""
        if self.settings.contains("geometry"):
            self.main_widget.restoreGeometry(self.settings.value("geometry"))

    def save_settings(self):
        """Save application settings."""
        self.settings.setValue("geometry", self.main_widget.saveGeometry())

    def quit_application(self):
        """Clean shutdown with final backup."""
        try:
            # Perform final backup
            self.db_manager.backup_unsynced_items()
            self.save_settings()
            self.clipboard_monitor.stop()
            self.tray_icon.hide()
            self.app.quit()
        except Exception as e:
            print(f"Shutdown error: {e}")
            self.app.quit()

    def run(self):
        """Run the application."""
        self.tray_icon.showMessage(
            "Clipboard History Manager",
            "Enhanced clipboard manager started with file and image support.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

        return self.app.exec()


def main():
    """Main entry point."""
    app = ClipboardHistoryApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
