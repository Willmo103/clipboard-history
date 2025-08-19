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
);

CREATE INDEX IF NOT EXISTS idx_timestamp ON clipboard_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_hash ON clipboard_history(content_hash);
CREATE INDEX IF NOT EXISTS idx_favorite ON clipboard_history(is_favorite);
CREATE INDEX IF NOT EXISTS idx_type ON clipboard_history(content_type);
CREATE INDEX IF NOT EXISTS idx_backed_up ON clipboard_history(backed_up);


