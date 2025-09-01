import base64
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path


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
