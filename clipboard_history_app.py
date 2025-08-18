#!/usr/bin/env python3
"""
Clipboard History Manager
A comprehensive clipboard history application with infinite storage using SQLite.
Features system tray integration and global hotkeys.
"""

import sys
import sqlite3
from datetime import datetime
import hashlib

from PyQt6.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
    QMenu,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QTextEdit,
    QLineEdit,
    QMessageBox,
    QSplitter,
    QCheckBox,
)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import (
    QIcon,
    QPixmap,
    QAction,
    QKeySequence,
    QShortcut,
)


class DatabaseManager:
    """Handles all database operations for clipboard history."""

    def __init__(self, db_path="clipboard_history.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the SQLite database and create tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS clipboard_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                content_hash TEXT UNIQUE,
                content_type TEXT DEFAULT 'text',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_favorite INTEGER DEFAULT 0,
                access_count INTEGER DEFAULT 0
            )
        """
        )

        # Create index for faster searches
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON clipboard_history(timestamp DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_hash ON clipboard_history(content_hash)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_favorite ON clipboard_history(is_favorite)"
        )

        conn.commit()
        conn.close()

    def add_clipboard_item(self, content, content_type="text"):
        """Add a new clipboard item to the database."""
        if not content.strip():
            return False

        # Create hash to avoid duplicates
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check if item already exists
            cursor.execute(
                "SELECT id FROM clipboard_history WHERE content_hash = ?",
                (content_hash,),
            )
            existing = cursor.fetchone()

            if existing:
                # Update timestamp and access count for existing item
                cursor.execute(
                    """
                    UPDATE clipboard_history
                    SET timestamp = CURRENT_TIMESTAMP, access_count = access_count + 1
                    WHERE id = ?
                """,
                    (existing[0],),
                )
            else:
                # Insert new item
                cursor.execute(
                    """
                    INSERT INTO clipboard_history (content, content_hash, content_type)
                    VALUES (?, ?, ?)
                """,
                    (content, content_hash, content_type),
                )

            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()

    def get_clipboard_history(
        self, limit=100, search_term="", favorites_only=False
    ):
        """Retrieve clipboard history with optional filtering."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = """
            SELECT id, content, content_type, timestamp, is_favorite, access_count
            FROM clipboard_history
        """
        params = []

        conditions = []
        if search_term:
            conditions.append("content LIKE ?")
            params.append(f"%{search_term}%")

        if favorites_only:
            conditions.append("is_favorite = 1")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC"

        if limit > 0:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        return results

    def delete_item(self, item_id):
        """Delete a specific clipboard item."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM clipboard_history WHERE id = ?", (item_id,)
        )
        conn.commit()
        conn.close()

    def toggle_favorite(self, item_id):
        """Toggle favorite status of an item."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE clipboard_history
            SET is_favorite = CASE WHEN is_favorite = 0 THEN 1 ELSE 0 END
            WHERE id = ?
        """,
            (item_id,),
        )
        conn.commit()
        conn.close()

    def clear_history(self, keep_favorites=True):
        """Clear clipboard history, optionally keeping favorites."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if keep_favorites:
            cursor.execute(
                "DELETE FROM clipboard_history WHERE is_favorite = 0"
            )
        else:
            cursor.execute("DELETE FROM clipboard_history")

        conn.commit()
        conn.close()


class ClipboardMonitor(QThread):
    """Background thread to monitor clipboard changes."""

    clipboard_changed = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.last_content = ""

    def run(self):
        """Main monitoring loop."""
        app = QApplication.instance()
        clipboard = app.clipboard()

        while self.running:
            try:
                current_content = clipboard.text()
                if current_content and current_content != self.last_content:
                    self.clipboard_changed.emit(current_content, "text")
                    self.last_content = current_content

                self.msleep(100)  # Check every 100ms
            except Exception as e:
                print(f"Clipboard monitor error: {e}")
                self.msleep(1000)

    def stop(self):
        """Stop the monitoring thread."""
        self.running = False
        self.wait()


class ClipboardHistoryWidget(QWidget):
    """Main widget for displaying and managing clipboard history."""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
        self.load_history()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Clipboard History Manager")
        self.setGeometry(300, 300, 800, 600)

        # Main layout
        layout = QVBoxLayout()

        # Search and controls
        controls_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search clipboard history...")
        self.search_input.textChanged.connect(self.on_search)
        controls_layout.addWidget(QLabel("Search:"))
        controls_layout.addWidget(self.search_input)

        self.favorites_checkbox = QCheckBox("Favorites only")
        self.favorites_checkbox.toggled.connect(self.load_history)
        controls_layout.addWidget(self.favorites_checkbox)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_history)
        controls_layout.addWidget(refresh_btn)

        clear_btn = QPushButton("Clear History")
        clear_btn.clicked.connect(self.clear_history)
        controls_layout.addWidget(clear_btn)

        layout.addLayout(controls_layout)

        # Splitter for list and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # History list
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.on_item_selected)
        self.history_list.itemDoubleClicked.connect(self.copy_to_clipboard)
        splitter.addWidget(self.history_list)

        # Preview and actions panel
        preview_panel = QWidget()
        preview_layout = QVBoxLayout()

        preview_layout.addWidget(QLabel("Preview:"))
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)

        # Action buttons
        action_layout = QHBoxLayout()

        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        action_layout.addWidget(copy_btn)

        self.favorite_btn = QPushButton("Toggle Favorite")
        self.favorite_btn.clicked.connect(self.toggle_favorite)
        action_layout.addWidget(self.favorite_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_item)
        action_layout.addWidget(delete_btn)

        preview_layout.addLayout(action_layout)
        preview_panel.setLayout(preview_layout)
        splitter.addWidget(preview_panel)

        layout.addWidget(splitter)
        self.setLayout(layout)

        # Set splitter proportions
        splitter.setSizes([400, 400])

    def load_history(self):
        """Load clipboard history into the list widget."""
        search_term = self.search_input.text()
        favorites_only = self.favorites_checkbox.isChecked()

        items = self.db_manager.get_clipboard_history(
            limit=1000, search_term=search_term, favorites_only=favorites_only
        )

        self.history_list.clear()

        for item in items:
            (
                item_id,
                content,
                content_type,
                timestamp,
                is_favorite,
                access_count,
            ) = item

            # Format display text
            preview = content[:100].replace("\n", " ").replace("\r", " ")
            if len(content) > 100:
                preview += "..."

            favorite_mark = "★ " if is_favorite else ""
            timestamp_str = datetime.fromisoformat(timestamp).strftime(
                "%m/%d %H:%M"
            )

            display_text = f"{favorite_mark}[{timestamp_str}] {preview}"

            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.history_list.addItem(list_item)

    def on_search(self):
        """Handle search input changes."""
        # Debounce search to avoid too many database queries
        if hasattr(self, "search_timer"):
            self.search_timer.stop()

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.load_history)
        self.search_timer.start(300)  # 300ms delay

    def on_item_selected(self, item):
        """Handle item selection in the list."""
        if item:
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data:
                content = item_data[1]
                is_favorite = item_data[4]

                self.preview_text.setPlainText(content)
                self.favorite_btn.setText(
                    "Remove Favorite" if is_favorite else "Add Favorite"
                )

    def copy_to_clipboard(self):
        """Copy selected item to clipboard."""
        current_item = self.history_list.currentItem()
        if current_item:
            item_data = current_item.data(Qt.ItemDataRole.UserRole)
            if item_data:
                content = item_data[1]
                clipboard = QApplication.clipboard()
                clipboard.setText(content)

                # Show temporary message
                (
                    self.statusBar().showMessage("Copied to clipboard!", 2000)
                    if hasattr(self, "statusBar")
                    else None
                )

    def toggle_favorite(self):
        """Toggle favorite status of selected item."""
        current_item = self.history_list.currentItem()
        if current_item:
            item_data = current_item.data(Qt.ItemDataRole.UserRole)
            if item_data:
                item_id = item_data[0]
                self.db_manager.toggle_favorite(item_id)
                self.load_history()

    def delete_item(self):
        """Delete selected item."""
        current_item = self.history_list.currentItem()
        if current_item:
            item_data = current_item.data(Qt.ItemDataRole.UserRole)
            if item_data:
                item_id = item_data[0]

                reply = QMessageBox.question(
                    self,
                    "Confirm Delete",
                    "Are you sure you want to delete this item?",
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No,
                )

                if reply == QMessageBox.StandardButton.Yes:
                    self.db_manager.delete_item(item_id)
                    self.load_history()
                    self.preview_text.clear()

    def clear_history(self):
        """Clear clipboard history."""
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Clear all clipboard history?\n(Favorites will be kept)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.db_manager.clear_history(keep_favorites=True)
            self.load_history()
            self.preview_text.clear()


class ClipboardHistoryApp:
    """Main application class with system tray integration."""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Initialize database
        self.db_manager = DatabaseManager()

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

    def setup_system_tray(self):
        """Setup system tray icon and menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(
                None,
                "System Tray",
                "System tray not available on this system.",
            )
            sys.exit(1)

        # Create tray icon (using a simple text-based icon if no image available) # noqa
        self.tray_icon = QSystemTrayIcon()

        # Try to create a simple icon
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

        # Add recent items to menu
        self.recent_items_actions = []
        for i in range(5):  # Show last 5 items
            action = QAction("", self.app)
            action.setVisible(False)
            tray_menu.addAction(action)
            self.recent_items_actions.append(action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self.app)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

        # Update recent items in tray menu
        self.update_tray_menu()

    def setup_hotkeys(self):
        """Setup global hotkeys."""
        # Global hotkey to show clipboard history (Ctrl+Shift+V)
        self.show_hotkey = QShortcut(
            QKeySequence("Ctrl+Shift+V"), self.main_widget
        )
        self.show_hotkey.activated.connect(self.show_main_window)

    def update_tray_menu(self):
        """Update recent items in tray menu."""
        recent_items = self.db_manager.get_clipboard_history(limit=5)

        for i, action in enumerate(self.recent_items_actions):
            if i < len(recent_items):
                item = recent_items[i]
                content = item[1]
                preview = content[:50].replace("\n", " ").replace("\r", " ")
                if len(content) > 50:
                    preview += "..."

                action.setText(preview)
                action.setVisible(True)
                action.triggered.disconnect()  # Disconnect any existing connections # noqa
                action.triggered.connect(
                    lambda checked, c=content: self.copy_from_tray(c)
                )
            else:
                action.setVisible(False)

    def copy_from_tray(self, content):
        """Copy content to clipboard from tray menu."""
        clipboard = QApplication.clipboard()
        clipboard.setText(content)

    def on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_main_window()

    def show_main_window(self):
        """Show and focus the main window."""
        self.main_widget.show()
        self.main_widget.activateWindow()
        self.main_widget.raise_()
        self.main_widget.load_history()  # Refresh the list

    def on_clipboard_changed(self, content, content_type):
        """Handle clipboard content changes."""
        self.db_manager.add_clipboard_item(content, content_type)
        self.update_tray_menu()

        # Update main window if visible
        if self.main_widget.isVisible():
            self.main_widget.load_history()

    def load_settings(self):
        """Load application settings."""
        # Restore window geometry if available
        if self.settings.contains("geometry"):
            self.main_widget.restoreGeometry(self.settings.value("geometry"))

    def save_settings(self):
        """Save application settings."""
        self.settings.setValue("geometry", self.main_widget.saveGeometry())

    def quit_application(self):
        """Clean shutdown of the application."""
        self.save_settings()
        self.clipboard_monitor.stop()
        self.tray_icon.hide()
        self.app.quit()

    def run(self):
        """Run the application."""
        self.tray_icon.showMessage(
            "Clipboard History Manager",
            "Application started and monitoring clipboard.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

        return self.app.exec()


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--hidden":
        # Start in hidden mode
        pass

    app = ClipboardHistoryApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
