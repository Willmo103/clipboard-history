import base64
import hashlib
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from PyQt6.QtCore import Qt, QTimer, QMimeData, QUrl
from PyQt6.QtGui import QPixmap, QDesktopServices
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QComboBox, QCheckBox, QPushButton, \
    QSplitter, QListWidget, QListWidgetItem, QApplication, QMessageBox, QFileDialog, QProgressDialog

from preview_widget import PreviewWidget


class ClipboardHistoryWidget(QWidget):
    """Enhanced main widget with file/image support and export functionality."""

    def __init__(self, db_manager):
        super().__init__()
        self.favorites_checkbox = None
        self.type_filter = None
        self.search_input = None
        self.db_manager = db_manager
        self.opened_from_tray = False
        self.init_ui()
        self.load_history()

        # Install event filter for focus tracking
        self.installEventFilter(self)

    def init_ui(self):
        """Initialize the enhanced user interface."""
        self.setWindowTitle("Clipboard History Manager")
        self.setGeometry(300, 300, 1000, 700)

        # Main layout
        layout = QVBoxLayout()

        # Controls row
        controls_layout = QHBoxLayout()

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search clipboard history...")
        # noinspection PyUnresolvedReferences
        self.search_input.textChanged.connect(self.on_search)
        controls_layout.addWidget(QLabel("Search:"))
        controls_layout.addWidget(self.search_input)

        # Content type filter
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All", "Text", "Files", "Images"])
        # noinspection PyUnresolvedReferences
        self.type_filter.currentTextChanged.connect(self.load_history)
        controls_layout.addWidget(QLabel("Type:"))
        controls_layout.addWidget(self.type_filter)

        # Favorites checkbox
        self.favorites_checkbox = QCheckBox("Favorites only")
        # noinspection PyUnresolvedReferences
        self.favorites_checkbox.toggled.connect(self.load_history)
        controls_layout.addWidget(self.favorites_checkbox)

        # Buttons
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_history)
        controls_layout.addWidget(refresh_btn)

        export_btn = QPushButton("Export JSON")
        export_btn.clicked.connect(self.export_history)
        controls_layout.addWidget(export_btn)

        clear_btn = QPushButton("Clear History")
        clear_btn.clicked.connect(self.clear_history)
        controls_layout.addWidget(clear_btn)

        layout.addLayout(controls_layout)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # History list
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.on_item_selected)
        self.history_list.itemDoubleClicked.connect(self.copy_to_clipboard)
        splitter.addWidget(self.history_list)

        # Enhanced preview panel
        preview_panel = QWidget()
        preview_layout = QVBoxLayout()

        # Preview widget
        self.preview_widget = PreviewWidget()
        preview_layout.addWidget(self.preview_widget)

        # Action buttons
        action_layout = QHBoxLayout()

        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        action_layout.addWidget(copy_btn)

        open_btn = QPushButton("Open/View")
        open_btn.clicked.connect(self.open_item)
        action_layout.addWidget(open_btn)

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
        splitter.setSizes([400, 600])

    def eventFilter(self, obj, event):
        """Handle focus events for auto-hide functionality."""
        if obj == self and event.type() == event.Type.WindowDeactivate:
            if self.opened_from_tray and self.isVisible():
                # Auto-hide when losing focus if opened from tray
                QTimer.singleShot(100, self.hide_to_tray)
        return super().eventFilter(obj, event)

    def hide_to_tray(self):
        """Hide window to tray."""
        self.hide()
        self.opened_from_tray = False

    def show_from_tray(self):
        """Show window from tray with focus tracking."""
        self.opened_from_tray = True
        self.show()
        self.raise_()
        self.activateWindow()

    def load_history(self):
        """Load clipboard history with enhanced filtering."""
        search_term = self.search_input.text()
        favorites_only = self.favorites_checkbox.isChecked()

        # Map UI filter to database values
        type_mapping = {
            "All": "all",
            "Text": "text",
            "Files": "file",
            "Images": "image",
        }
        content_type_filter = type_mapping.get(
            self.type_filter.currentText(), "all"
        )

        items = self.db_manager.get_clipboard_history(
            limit=1000,
            search_term=search_term,
            favorites_only=favorites_only,
            content_type_filter=content_type_filter,
        )

        self.history_list.clear()

        for item in items:
            item_id, content, content_type, file_path = item[:4]
            file_size, mime_type, thumbnail, timestamp = item[4:8]
            is_favorite, access_count = item[8:10]

            # Create display text based on content type
            if content_type == "file":
                display_name = (
                    os.path.basename(file_path) if file_path else "File"
                )
                preview = f"📁 {display_name}"
                if file_size:
                    size_mb = file_size / (1024 * 1024)
                    size_str = (
                        f"{size_mb:.1f}MB"
                        if size_mb >= 1
                        else f"{file_size//1024}KB"
                    )
                    preview += f" ({size_str})"
            elif content_type == "image":
                preview = f"🖼️ Image ({len(content)} chars)"
                if file_size:
                    size_mb = file_size / (1024 * 1024)
                    size_str = (
                        f"{size_mb:.1f}MB"
                        if size_mb >= 1
                        else f"{file_size//1024}KB"
                    )
                    preview += f" ({size_str})"
            else:
                preview = content[:100].replace("\n", " ").replace("\r", " ")
                if len(content) > 100:
                    preview += "..."
                # Add URL indicator
                if self.is_url(content.strip()):
                    preview = f"🔗 {preview}"

            favorite_mark = "★ " if is_favorite else ""
            timestamp_str = datetime.fromisoformat(timestamp).strftime(
                "%m/%d %H:%M"
            )

            display_text = f"{favorite_mark}[{timestamp_str}] {preview}"

            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.history_list.addItem(list_item)

    def is_url(self, text):
        """Check if text is a URL."""
        try:
            result = urlparse(text)
            return all([result.scheme, result.netloc])
        except:  # noqa
            return False

    def on_search(self):
        """Handle search with debouncing."""
        if hasattr(self, "search_timer"):
            self.search_timer.stop()

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.load_history)
        self.search_timer.start(300)

    def on_item_selected(self, item):
        """Handle item selection with enhanced preview."""
        if item:
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data:
                self.preview_widget.display_content(item_data)
                is_favorite = item_data[8]
                self.favorite_btn.setText(
                    "Remove Favorite" if is_favorite else "Add Favorite"
                )

    # def copy_to_clipboard(self):
    #     """Copy selected item to clipboard with type handling."""
    #     current_item = self.history_list.currentItem()
    #     if current_item:
    #         item_data = current_item.data(Qt.ItemDataRole.UserRole)
    #         if item_data:
    #             content = item_data[1]
    #             content_type = item_data[2]

    #             clipboard = QApplication.clipboard()

    #             if content_type == "text":
    #                 clipboard.setText(content)
    #             elif content_type == "file":
    #                 # Create file URL for clipboard
    #                 file_path = item_data[3]
    #                 if file_path and os.path.exists(file_path):
    #                     mime_data = QMimeData()
    #                     mime_data.setUrls([QUrl.fromLocalFile(file_path)])
    #                     clipboard.setMimeData(mime_data)
    #                 else:
    #                     clipboard.setText(content)  # Fallback to text
    #             elif content_type == "image":
    #                 # Decode base64 image and set to clipboard
    #                 try:
    #                     image_data = base64.b64decode(content)
    #                     pixmap = QPixmap()
    #                     pixmap.loadFromData(image_data)
    #                     clipboard.setPixmap(pixmap)
    #                 except:
    #                     clipboard.setText(content)  # Fallback to text

    #             # Show feedback
    #             self.show_status_message("Copied to clipboard!")

    def copy_to_clipboard(self):
        """Copy selected item to clipboard with type handling."""
        current_item = self.history_list.currentItem()
        if current_item:
            item_data = current_item.data(Qt.ItemDataRole.UserRole)
            if item_data:
                content = item_data[1]
                content_type = item_data[2]

                # Mark the next clipboard change as self-initiated so the monitor ignores it once
                app = QApplication.instance()
                content_hash = hashlib.sha256(
                    str(content).encode("utf-8", errors="ignore")
                ).hexdigest()
                app.setProperty("clip_skip_once", True)
                app.setProperty("clip_skip_hash", content_hash)

                clipboard = QApplication.clipboard()

                if content_type == "text":
                    clipboard.setText(content)
                elif content_type == "file":
                    file_path = item_data[3]
                    if file_path and os.path.exists(file_path):
                        mime_data = QMimeData()
                        mime_data.setUrls([QUrl.fromLocalFile(file_path)])
                        clipboard.setMimeData(mime_data)
                    else:
                        clipboard.setText(content)  # Fallback to text
                elif content_type == "image":
                    try:
                        image_data = base64.b64decode(content)
                        pixmap = QPixmap()
                        pixmap.loadFromData(image_data)
                        clipboard.setPixmap(pixmap)
                    except Exception:
                        clipboard.setText(content)  # Fallback to text

                self.show_status_message("Copied to clipboard!")

    def open_item(self):
        """Open/view the selected item."""
        current_item = self.history_list.currentItem()
        if current_item:
            item_data = current_item.data(Qt.ItemDataRole.UserRole)
            if item_data:
                content = item_data[1]
                content_type = item_data[2]
                file_path = item_data[3]

                if content_type == "file" and file_path:
                    # Open file with default application
                    if os.path.exists(file_path):
                        QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
                    else:
                        QMessageBox.warning(
                            self,
                            "File Not Found",
                            f"The file {file_path} no longer exists.",
                        )
                elif content_type == "text" and self.is_url(content.strip()):
                    # Open URL in browser
                    QDesktopServices.openUrl(QUrl(content.strip()))
                elif content_type == "image":
                    # Save and open image temporarily
                    try:
                        image_data = base64.b64decode(content)
                        temp_path = Path.home() / "temp_clipboard_image.png"
                        with open(temp_path, "wb") as f:
                            f.write(image_data)
                        QDesktopServices.openUrl(
                            QUrl.fromLocalFile(str(temp_path))
                        )
                    except Exception as e:
                        QMessageBox.warning(
                            self, "Error", f"Cannot open image: {e}"
                        )
                else:
                    QMessageBox.information(
                        self,
                        "Info",
                        "No appropriate viewer for this content type.",
                    )

    def show_status_message(self, message):
        """Show a temporary status message."""
        # You could implement a status bar or tooltip here
        print(message)  # For now, just print

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
                    self.preview_widget.clear_content()

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
            self.preview_widget.clear_content()

    def export_history(self):
        """Export clipboard history to JSON."""
        # Ask user for export options
        favorites_only = (
            QMessageBox.question(
                self,
                "Export Options",
                "Export only favorites?\n\nYes = Favorites only\nNo = All items",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )
            == QMessageBox.StandardButton.Yes
        )

        if favorites_only == QMessageBox.StandardButton.Cancel:
            return

        # Get file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Clipboard History",
            f"clipboard_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json);;All Files (*)",
        )

        if file_path:
            try:
                # Show progress dialog
                progress = QProgressDialog(
                    "Exporting clipboard history...", "Cancel", 0, 100, self
                )
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.show()

                QApplication.processEvents()
                progress.setValue(50)

                # Export data
                item_count = self.db_manager.export_to_json(
                    file_path, favorites_only
                )

                progress.setValue(100)
                progress.close()

                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Successfully exported {item_count} items to:\n{file_path}",
                )

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Error",
                    f"Failed to export clipboard history:\n{str(e)}",
                )
