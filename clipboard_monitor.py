import base64
import hashlib
import mimetypes
import os
from collections import deque
from time import monotonic
from urllib.parse import urlparse

from PyQt6.QtCore import QThread, pyqtSignal, QMimeData, QBuffer, QIODevice, Qt
from PyQt6.QtGui import QClipboard, QImage, QPixmap
from PyQt6.QtWidgets import QApplication


class ClipboardMonitor(QThread):
    """Enhanced clipboard monitor supporting files and images with self-copy suppression and debouncing."""

    clipboard_changed = pyqtSignal(str, str, dict)  # content, type, metadata

    def __init__(self, dedupe_window_seconds: float = 1.0):
        super().__init__()
        self.running = True
        self.last_content_hash = ""
        self._recent = deque(maxlen=16)  # (hash, t)
        self._dedupe_window = float(dedupe_window_seconds)

    # ---------- Helpers ----------

    @staticmethod
    def _hash_content(content: str) -> str:
        try:
            return hashlib.sha256(
                content.encode("utf-8", errors="ignore")
            ).hexdigest()
        except Exception:
            # Extremely defensive; ensures we never blow up hashing
            return ""

    def _is_recent(self, h: str) -> bool:
        now = monotonic()
        # prune old
        while (
            self._recent and (now - self._recent[0][1]) > self._dedupe_window
        ):
            self._recent.popleft()
        # check
        return any(h == rh for rh, _ in self._recent)

    def _remember(self, h: str) -> None:
        if h:
            self._recent.append((h, monotonic()))

    def _should_skip_for_self_copy(self, app: QApplication, h: str) -> bool:
        """
        UI will set:
          app.setProperty("clip_skip_once", True)
          app.setProperty("clip_skip_hash", "<sha256>")
        We skip exactly once if True and (hash matches OR property has no hash).
        """
        try:
            skip_once = bool(app.property("clip_skip_once") or False)
            if not skip_once:
                return False

            marked_hash = app.property("clip_skip_hash")
            # If UI provided a hash, require a match; otherwise skip regardless one time.
            if isinstance(marked_hash, str) and marked_hash:
                if h == marked_hash:
                    # clear the flags
                    app.setProperty("clip_skip_once", False)
                    app.setProperty("clip_skip_hash", "")
                    return True
                else:
                    # Not our marked hash; don't consume the skip flag yet.
                    return False
            else:
                # No hash provided, consume the skip-once regardless.
                app.setProperty("clip_skip_once", False)
                return True
        except Exception:
            # Never allow this path to crash the thread
            app.setProperty("clip_skip_once", False)
            app.setProperty("clip_skip_hash", "")
            return False

    # ---------- Main loop ----------

    def run(self):
        """Main monitoring loop."""
        app: QApplication = QApplication.instance()
        if app is None:
            # Very defensive: without an app, monitoring can't proceed
            return

        clipboard: QClipboard = app.clipboard()

        while self.running:
            try:
                mime_data = clipboard.mimeData()
                if mime_data is None:
                    self.msleep(200)
                    continue

                content, content_type, metadata = self.process_clipboard_data(
                    mime_data
                )

                if content:
                    content_hash = self._hash_content(str(content))

                    # 1) Do we need to skip because our own UI just set this?
                    if self._should_skip_for_self_copy(app, content_hash):
                        self.last_content_hash = content_hash
                        self._remember(content_hash)
                        self.msleep(200)
                        continue

                    # 2) Debounce rapid repeats
                    if self._is_recent(content_hash):
                        self.msleep(200)
                        continue

                    if content_hash != self.last_content_hash:
                        self.clipboard_changed.emit(
                            content, content_type, metadata
                        )
                        self.last_content_hash = content_hash
                        self._remember(content_hash)

                self.msleep(200)  # Check every 200ms

            except Exception as e:
                # Don't loop-spin on errors; slow down and keep going
                print(f"Clipboard monitor error: {e}")
                self.msleep(750)

    def process_clipboard_data(self, mime_data: QMimeData):
        """Process clipboard data and determine type."""
        content = ""
        content_type = "text"
        metadata = {}

        try:
            # Files (URLs)
            if mime_data.hasUrls():
                urls = mime_data.urls()
                if urls:
                    url = urls[0]
                    if url.isLocalFile():
                        file_path = url.toLocalFile()
                        if file_path and os.path.exists(file_path):
                            content = file_path
                            content_type = "file"

                            # Get file metadata
                            try:
                                stat = os.stat(file_path)
                                metadata = {
                                    "file_path": file_path,
                                    "file_size": stat.st_size,
                                    "mime_type": mimetypes.guess_type(
                                        file_path
                                    )[0]
                                    or "application/octet-stream",
                                    "thumbnail": self.create_file_thumbnail(
                                        file_path
                                    ),
                                }
                            except Exception:
                                metadata = {"file_path": file_path}
                            return content, content_type, metadata

            # Images
            if mime_data.hasImage():
                _image = mime_data.imageData()
                if isinstance(_image, QImage) and (not _image.isNull()):
                    pixmap = QPixmap.fromImage(_image)

                    buffer = QBuffer()
                    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                    pixmap.save(buffer, "PNG")
                    image_bytes = bytes(buffer.data())
                    content = base64.b64encode(image_bytes).decode("ascii")
                    content_type = "image"

                    metadata = {
                        "mime_type": "image/png",
                        "file_size": len(image_bytes),
                        "thumbnail": image_bytes,  # raw bytes for preview/thumbnail
                    }
                    return content, content_type, metadata

            # Text
            if mime_data.hasText():
                text = (mime_data.text() or "").strip()
                if text:
                    content = text
                    content_type = "text"
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
                    return bytes(buffer.data())
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
        return None

    def is_url(self, text):
        """Check if text looks like a URL."""
        try:
            result = urlparse(text)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def stop(self):
        """Stop the monitoring thread."""
        self.running = False
        try:
            self.wait(1500)
        except Exception:
            pass
