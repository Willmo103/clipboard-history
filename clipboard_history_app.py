#!/usr/bin/env python3
"""
Enhanced Clipboard History Manager
A comprehensive clipboard history application with file/image support, JSON export,
automatic backup, and improved UI features.
"""

import sys
import os
import sqlite3
import json
import base64
import mimetypes
from datetime import datetime
from pathlib import Path
import hashlib
from urllib.parse import urlparse


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
    QScrollArea,
    QCheckBox,
    QFileDialog,
    QProgressDialog,
    QGroupBox,
    QTabWidget,
    QComboBox,
)
from PyQt6.QtCore import (
    QTimer,
    Qt,
    QThread,
    pyqtSignal,
    QSettings,
    QUrl,
    QMimeData,
    QIODevice,
    QTimer,
    QByteArray,
    QBuffer,
)
from PyQt6.QtGui import (
    QIcon,
    QPixmap,
    QAction,
    QKeySequence,
    QShortcut,
    QDesktopServices,
    QClipboard,
    QImage,
    QGuiApplication,
)


class DatabaseManager:
    """Enhanced database manager with file and image support."""

    def __init__(self, db_path="clipboard_history.db"):
        self.db_path = db_path
        self.backup_path = Path(db_path).with_suffix(".json")
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
                file_path TEXT,
                file_size INTEGER,
                mime_type TEXT,
                thumbnail BLOB,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_favorite INTEGER DEFAULT 0,
                access_count INTEGER DEFAULT 0,
                backed_up INTEGER DEFAULT 0
            )
        """
        )

        # Create indexes for better performance
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON clipboard_history(timestamp DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_hash ON clipboard_history(content_hash)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_favorite ON clipboard_history(is_favorite)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_type ON clipboard_history(content_type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_backed_up ON clipboard_history(backed_up)"
        )

        conn.commit()
        conn.close()

    def add_clipboard_item(
        self,
        content,
        content_type="text",
        file_path=None,
        file_size=None,
        mime_type=None,
        thumbnail=None,
    ):
        """Add a new clipboard item to the database."""
        if content_type == "text" and not content.strip():
            return False

        # Create hash to avoid duplicates
        content_hash = hashlib.sha256(str(content).encode()).hexdigest()

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
                    INSERT INTO clipboard_history (content, content_hash, content_type,
                                                 file_path, file_size, mime_type, thumbnail)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        content,
                        content_hash,
                        content_type,
                        file_path,
                        file_size,
                        mime_type,
                        thumbnail,
                    ),
                )

            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()

    def get_clipboard_history(
        self,
        limit=100,
        search_term="",
        favorites_only=False,
        content_type_filter="all",
    ):
        """Retrieve clipboard history with optional filtering."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = """
            SELECT id, content, content_type, file_path, file_size, mime_type,
                   thumbnail, timestamp, is_favorite, access_count
            FROM clipboard_history
        """
        params = []
        conditions = []

        if search_term:
            conditions.append("(content LIKE ? OR file_path LIKE ?)")
            params.extend([f"%{search_term}%", f"%{search_term}%"])

        if favorites_only:
            conditions.append("is_favorite = 1")

        if content_type_filter != "all":
            conditions.append("content_type = ?")
            params.append(content_type_filter)

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

    def export_to_json(self, file_path, favorites_only=False):
        """Export clipboard history to JSON."""
        items = self.get_clipboard_history(
            limit=0, favorites_only=favorites_only
        )

        export_data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "total_items": len(items),
                "favorites_only": favorites_only,
                "version": "1.0",
            },
            "items": [],
        }

        for item in items:
            item_data = {
                "id": item[0],
                "content": item[1],
                "content_type": item[2],
                "file_path": item[3],
                "file_size": item[4],
                "mime_type": item[5],
                "thumbnail": (
                    base64.b64encode(item[6]).decode() if item[6] else None
                ),
                "timestamp": item[7],
                "is_favorite": bool(item[8]),
                "access_count": item[9],
            }
            export_data["items"].append(item_data)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        # Mark items as backed up
        if items:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            item_ids = [str(item[0]) for item in items]
            cursor.execute(
                f"""
                UPDATE clipboard_history
                SET backed_up = 1
                WHERE id IN ({",".join(item_ids)})
            """
            )
            conn.commit()
            conn.close()

        return len(items)

    def backup_unsynced_items(self):
        """Backup items that haven't been backed up yet."""
        try:
            # Get items that haven't been backed up
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, content, content_type, file_path, file_size, mime_type,
                       thumbnail, timestamp, is_favorite, access_count
                FROM clipboard_history
                WHERE backed_up = 0
                ORDER BY timestamp DESC
            """
            )
            unsynced_items = cursor.fetchall()
            conn.close()

            if not unsynced_items:
                return 0

            # Load existing backup or create new one
            backup_data = {"export_info": {}, "items": []}
            if self.backup_path.exists():
                try:
                    with open(self.backup_path, "r", encoding="utf-8") as f:
                        backup_data = json.load(f)
                except:
                    backup_data = {"export_info": {}, "items": []}

            # Add unsynced items to backup
            for item in unsynced_items:
                item_data = {
                    "id": item[0],
                    "content": item[1],
                    "content_type": item[2],
                    "file_path": item[3],
                    "file_size": item[4],
                    "mime_type": item[5],
                    "thumbnail": (
                        base64.b64encode(item[6]).decode() if item[6] else None
                    ),
                    "timestamp": item[7],
                    "is_favorite": bool(item[8]),
                    "access_count": item[9],
                }
                backup_data["items"].append(item_data)

            # Update export info
            backup_data["export_info"] = {
                "timestamp": datetime.now().isoformat(),
                "total_items": len(backup_data["items"]),
                "version": "1.0",
                "auto_backup": True,
            }

            # Save updated backup
            with open(self.backup_path, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            # Mark items as backed up
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            item_ids = [str(item[0]) for item in unsynced_items]
            cursor.execute(
                f"""
                UPDATE clipboard_history
                SET backed_up = 1
                WHERE id IN ({",".join(item_ids)})
            """
            )
            conn.commit()
            conn.close()

            return len(unsynced_items)

        except Exception as e:
            print(f"Backup error: {e}")
            return 0


class ClipboardMonitor(QThread):
    """Enhanced clipboard monitor supporting files and images."""

    clipboard_changed = pyqtSignal(str, str, dict)  # content, type, metadata

    def __init__(self):
        super().__init__()
        self.running = True
        self.last_content_hash = ""

    def run(self):
        """Main monitoring loop."""
        app: QApplication = QApplication.instance()
        clipboard: QClipboard = app.clipboard()

        while self.running:
            try:
                mime_data = clipboard.mimeData()
                content, content_type, metadata = self.process_clipboard_data(
                    mime_data
                )

                if content:
                    content_hash = hashlib.sha256(
                        str(content).encode()
                    ).hexdigest()
                    if content_hash != self.last_content_hash:
                        self.clipboard_changed.emit(
                            content, content_type, metadata
                        )
                        self.last_content_hash = content_hash

                self.msleep(200)  # Check every 200ms
            except Exception as e:
                print(f"Clipboard monitor error: {e}")
                self.msleep(1000)

    def process_clipboard_data(self, mime_data: QMimeData):
        """Process clipboard data and determine type."""
        content = ""
        content_type = "text"
        metadata = {}

        try:
            # Check for files (URLs)
            if mime_data.hasUrls():
                urls = mime_data.urls()
                if urls:
                    url = urls[0]
                    if url.isLocalFile():
                        file_path = url.toLocalFile()
                        if os.path.exists(file_path):
                            content = file_path
                            content_type = "file"

                            # Get file metadata
                            stat = os.stat(file_path)
                            metadata = {
                                "file_path": file_path,
                                "file_size": stat.st_size,
                                "mime_type": mimetypes.guess_type(file_path)[0]
                                or "application/octet-stream",
                                "thumbnail": self.create_file_thumbnail(
                                    file_path
                                ),
                            }
                            return content, content_type, metadata

            # Check for images
            if mime_data.hasImage():
                _image: QImage = mime_data.imageData()
                if _image and not _image.isNull():
                    pixmap = QPixmap.fromImage(_image)

                    # Convert image to base64
                    buffer = QBuffer()
                    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                    pixmap.save(buffer, "PNG")
                    image_data = buffer.data()
                    content = base64.b64encode(image_data).decode()
                    content_type = "image"

                    metadata = {
                        "mime_type": "image/png",
                        "file_size": len(image_data),
                        "thumbnail": image_data,  # Store raw bytes for thumbnail
                    }
                    return content, content_type, metadata

            # Check for text
            if mime_data.hasText():
                text = mime_data.text().strip()
                if text:
                    content = text
                    content_type = "text"

                    # Check if text looks like a URL
                    if self.is_url(text):
                        metadata["is_url"] = True

                    return content, content_type, metadata

        except Exception as e:
            print(f"Error processing clipboard data: {e}")

        return "", "text", {}

    def create_file_thumbnail(self, file_path):
        """Create thumbnail for file if possible."""
        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type and mime_type.startswith("image/"):
                # Create thumbnail for image files
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    thumbnail = pixmap.scaled(
                        64,
                        64,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )

                    buffer = QBuffer()
                    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                    thumbnail.save(buffer, "PNG")
                    return buffer.data()
        except Exception as e:
            print(f"Error creating thumbnail: {e}")

        return None

    def is_url(self, text):
        """Check if text looks like a URL."""
        try:
            result = urlparse(text)
            return all([result.scheme, result.netloc])
        except:
            return False

    def stop(self):
        """Stop the monitoring thread."""
        self.running = False
        self.wait()


class EnhancedPreviewWidget(QWidget):
    """Enhanced preview widget supporting images and files."""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Content type indicator
        self.type_label = QLabel()
        self.type_label.setStyleSheet("font-weight: bold; color: #555;")
        layout.addWidget(self.type_label)

        # Tabbed preview
        self.tab_widget = QTabWidget()

        # Text preview tab
        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.tab_widget.addTab(self.text_preview, "Text")

        # Image preview tab
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet(
            "border: 1px solid #ccc; background: white;"
        )

        image_scroll = QScrollArea()
        image_scroll.setWidget(self.image_label)
        image_scroll.setWidgetResizable(True)
        self.tab_widget.addTab(image_scroll, "Image")

        layout.addWidget(self.tab_widget)

        # File info panel
        self.info_panel = QGroupBox("Details")
        info_layout = QVBoxLayout()
        self.info_labels = []

        for i in range(5):  # Create labels for file info
            label = QLabel()
            label.setWordWrap(True)
            info_layout.addWidget(label)
            self.info_labels.append(label)

        self.info_panel.setLayout(info_layout)
        layout.addWidget(self.info_panel)

        self.setLayout(layout)

    def display_content(self, item_data):
        """Display content based on type."""
        if not item_data:
            self.clear_content()
            return

        content_type = item_data[2]
        content = item_data[1]
        file_path = item_data[3]
        file_size = item_data[4]
        mime_type = item_data[5]
        thumbnail = item_data[6]
        timestamp = item_data[7]
        is_favorite = item_data[8]
        access_count = item_data[9]

        # Update type label
        type_text = f"Type: {content_type.title()}"
        if mime_type:
            type_text += f" ({mime_type})"
        self.type_label.setText(type_text)

        # Show appropriate tab
        if content_type == "image":
            self.display_image(content, thumbnail)
            self.tab_widget.setCurrentIndex(1)
        else:
            self.tab_widget.setCurrentIndex(0)

        # Update text preview
        self.display_text_preview(content, content_type, file_path)

        # Update info panel
        self.update_info_panel(
            content_type,
            file_path,
            file_size,
            timestamp,
            is_favorite,
            access_count,
        )

    def display_image(self, b64_content, thumbnail_bytes):
        """Display image in preview."""
        try:
            if thumbnail_bytes:
                # Use thumbnail for preview
                pixmap = QPixmap()
                pixmap.loadFromData(thumbnail_bytes)
            else:
                # Decode base64 image
                image_data = base64.b64decode(b64_content)
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)

            if not pixmap.isNull():
                # Scale image to fit preview
                scaled_pixmap = pixmap.scaled(
                    300,
                    300,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.image_label.setPixmap(scaled_pixmap)
            else:
                self.image_label.setText("Unable to load image")

        except Exception as e:
            self.image_label.setText(f"Error loading image: {e}")

    def display_text_preview(self, content, content_type, file_path):
        """Display text preview with appropriate formatting."""
        if content_type == "file":
            preview_text = f"File: {file_path}\n\n"
            if os.path.exists(file_path):
                preview_text += f"Status: File exists\n"
                preview_text += f"Location: {os.path.dirname(file_path)}\n"
                preview_text += f"Name: {os.path.basename(file_path)}"
            else:
                preview_text += "Status: File not found"

        elif content_type == "image":
            preview_text = "Image data (Base64 encoded)\n\n"
            preview_text += f"Data length: {len(content)} characters\n"
            preview_text += f"Preview: {content[:100]}..."

        else:
            # Regular text with URL detection
            preview_text = content

        self.text_preview.setPlainText(preview_text)

        # Make URLs clickable if it's a text type
        if content_type == "text" and self.is_url(content.strip()):
            self.text_preview.setHtml(
                f'<a href="{content.strip()}">{content}</a>'
            )

    def is_url(self, text):
        """Check if text is a URL."""
        try:
            result = urlparse(text)
            return all([result.scheme, result.netloc])
        except:
            return False

    def update_info_panel(
        self,
        content_type,
        file_path,
        file_size,
        timestamp,
        is_favorite,
        access_count,
    ):
        """Update the information panel."""
        info_texts = [
            f"Content Type: {content_type.title()}",
            f"File Path: {file_path if file_path else 'N/A'}",
            f"Timestamp: {datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S')}",
            f"Favorite: {'Yes' if is_favorite else 'No'}",
            f"Access Count: {access_count}",
            "",
        ]

        if file_size:
            size_mb = file_size / (1024 * 1024)
            if size_mb < 1:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{size_mb:.1f} MB"
            info_texts[4] = f"Size: {size_str}"

        for i, text in enumerate(info_texts):
            if i < len(self.info_labels):
                self.info_labels[i].setText(text)
                self.info_labels[i].setVisible(bool(text))

    def clear_content(self):
        """Clear all preview content."""
        self.type_label.setText("")
        self.text_preview.clear()
        self.image_label.clear()
        self.image_label.setText("No preview available")
        for label in self.info_labels:
            label.clear()


class ClipboardHistoryWidget(QWidget):
    """Enhanced main widget with file/image support and export functionality."""

    def __init__(self, db_manager):
        super().__init__()
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
        self.search_input.textChanged.connect(self.on_search)
        controls_layout.addWidget(QLabel("Search:"))
        controls_layout.addWidget(self.search_input)

        # Content type filter
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All", "Text", "Files", "Images"])
        self.type_filter.currentTextChanged.connect(self.load_history)
        controls_layout.addWidget(QLabel("Type:"))
        controls_layout.addWidget(self.type_filter)

        # Favorites checkbox
        self.favorites_checkbox = QCheckBox("Favorites only")
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
        self.preview_widget = EnhancedPreviewWidget()
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
        except:
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

    def copy_to_clipboard(self):
        """Copy selected item to clipboard with type handling."""
        current_item = self.history_list.currentItem()
        if current_item:
            item_data = current_item.data(Qt.ItemDataRole.UserRole)
            if item_data:
                content = item_data[1]
                content_type = item_data[2]

                clipboard = QApplication.clipboard()

                if content_type == "text":
                    clipboard.setText(content)
                elif content_type == "file":
                    # Create file URL for clipboard
                    file_path = item_data[3]
                    if file_path and os.path.exists(file_path):
                        mime_data = QMimeData()
                        mime_data.setUrls([QUrl.fromLocalFile(file_path)])
                        clipboard.setMimeData(mime_data)
                    else:
                        clipboard.setText(content)  # Fallback to text
                elif content_type == "image":
                    # Decode base64 image and set to clipboard
                    try:
                        image_data = base64.b64decode(content)
                        pixmap = QPixmap()
                        pixmap.loadFromData(image_data)
                        clipboard.setPixmap(pixmap)
                    except:
                        clipboard.setText(content)  # Fallback to text

                # Show feedback
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


class ClipboardHistoryApp:
    """Enhanced main application class."""

    def __init__(self):
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
                    preview = f"🖼️ Image"
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
        except:
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
