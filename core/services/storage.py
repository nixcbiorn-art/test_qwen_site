"""
Хранилище данных на основе SQLite.
Реализует интерфейс IStorage.
"""
import sqlite3
import asyncio
from datetime import datetime
from typing import List, Optional
import json
import hashlib

from ..domain.interfaces import IStorage
from ..domain.models import Snapshot, ChangeRecord

class StorageService(IStorage):
    """Сервис хранения данных в SQLite"""
    
    def __init__(self, config):
        self.db_path = config.db_path
        self._init_db()
    
    def _init_db(self):
        """Инициализация БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                data TEXT NOT NULL,
                checksum TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                change_type TEXT NOT NULL,
                field_path TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def save_snapshot(self, snapshot: Snapshot) -> int:
        """Сохранить снимок данных"""
        conn = await asyncio.get_event_loop().run_in_executor(
            None, sqlite3.connect, self.db_path
        )
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO snapshots (endpoint, timestamp, data, checksum)
            VALUES (?, ?, ?, ?)
        ''', (
            snapshot.endpoint,
            snapshot.timestamp.isoformat(),
            json.dumps(snapshot.data),
            snapshot.checksum
        ))
        
        snapshot_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return snapshot_id
    
    async def get_latest_snapshots(self, endpoint: str, limit: int = 100) -> List[Snapshot]:
        """Получить последние снимки по эндпоинту"""
        conn = await asyncio.get_event_loop().run_in_executor(
            None, sqlite3.connect, self.db_path
        )
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, endpoint, timestamp, data, checksum
            FROM snapshots
            WHERE endpoint = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (endpoint, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            Snapshot(
                id=row[0],
                endpoint=row[1],
                timestamp=datetime.fromisoformat(row[2]),
                data=json.loads(row[3]),
                checksum=row[4]
            )
            for row in rows
        ]
    
    async def save_change(self, change: ChangeRecord) -> int:
        """Сохранить запись об изменении"""
        conn = await asyncio.get_event_loop().run_in_executor(
            None, sqlite3.connect, self.db_path
        )
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO changes (snapshot_id, timestamp, change_type, field_path, old_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            change.snapshot_id,
            change.timestamp.isoformat(),
            change.change_type,
            change.field_path,
            json.dumps(change.old_value) if change.old_value is not None else None,
            json.dumps(change.new_value) if change.new_value is not None else None
        ))
        
        change_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return change_id

__all__ = ["StorageService"]
