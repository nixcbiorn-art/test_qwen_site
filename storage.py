"""Работа с SQLite."""

import sqlite3
import json
import hashlib
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from config import DB_PATH, DATA_DIR


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            endpoint TEXT NOT NULL,
            data_hash TEXT NOT NULL,
            raw_data TEXT,
            has_changed BOOLEAN DEFAULT 0
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_endpoint ON snapshots(endpoint)")
    conn.commit()
    conn.close()


def save_snapshot(endpoint: str, data: Any, raw_data: Optional[str] = None) -> bool:
    data_str = json.dumps(data, sort_keys=True, default=str)
    data_hash = hashlib.sha256(data_str.encode()).hexdigest()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT data_hash FROM snapshots WHERE endpoint=? ORDER BY id DESC LIMIT 1",
        (endpoint,)
    )
    last_record = cursor.fetchone()

    has_changed = True
    if last_record and last_record[0] == data_hash:
        has_changed = False

    cursor.execute(
        "INSERT INTO snapshots (endpoint, data_hash, raw_data, has_changed) VALUES (?, ?, ?, ?)",
        (endpoint, data_hash, raw_data or data_str, has_changed)
    )
    conn.commit()
    conn.close()
    return has_changed


def get_latest_snapshot(endpoint: str) -> Optional[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM snapshots WHERE endpoint=? ORDER BY id DESC LIMIT 1",
        (endpoint,)
    )
    record = cursor.fetchone()
    conn.close()
    return dict(record) if record else None
