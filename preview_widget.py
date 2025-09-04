import base64
import os
from datetime import datetime
from urllib.parse import urlparse

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTabWidget, QTextEdit, QScrollArea, QGroupBox


class PreviewWidget(QWidget):
    """Enhanced preview widget supporting images and files."""

    def __init__(self):
        super().__init__()
        self.info_labels = None
        self.info_panel = None
        self.image_label = None
        self.text_preview = None
        self.tab_widget = None
        self.type_label = None
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
                preview_text += "Status: File exists\n"
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
        except:  # noqa
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
