"""Работа с SQLite с улучшенной обработкой ошибок и версионированием."""

import sqlite3
import json
import hashlib
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from config import DB_PATH, DATA_DIR


class DatabaseError(Exception):
    """Базовое исключение для ошибок базы данных."""
    pass


@contextmanager
def get_db_connection():
    """Контекстный менеджер для безопасного подключения к БД."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        raise DatabaseError(f"Ошибка базы данных: {e}")
    finally:
        if conn:
            conn.close()


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Таблица снимков данных
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
        
        # Таблица истории изменений с детализацией
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS change_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                change_type TEXT NOT NULL,
                field_path TEXT,
                old_value TEXT,
                new_value TEXT,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
            )
        """)
        
        # Индексы для ускорения поиска
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_endpoint ON snapshots(endpoint)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON snapshots(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_change_snapshot ON change_history(snapshot_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_change_type ON change_history(change_type)")


def save_snapshot(endpoint: str, data: Any, raw_data: Optional[str] = None, 
                  changes: Optional[List[str]] = None) -> bool:
    """
    Сохраняет снимок данных и историю изменений.
    
    Args:
        endpoint: Путь к эндпоинту
        data: Данные для сохранения
        raw_data: Сырые данные (JSON строка)
        changes: Список описаний изменений
        
    Returns:
        bool: True если данные изменились
    """
    data_str = json.dumps(data, sort_keys=True, default=str)
    data_hash = hashlib.sha256(data_str.encode()).hexdigest()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, data_hash FROM snapshots WHERE endpoint=? ORDER BY id DESC LIMIT 1",
            (endpoint,)
        )
        last_record = cursor.fetchone()

        has_changed = True
        if last_record and last_record['data_hash'] == data_hash:
            has_changed = False

        cursor.execute(
            "INSERT INTO snapshots (endpoint, data_hash, raw_data, has_changed) VALUES (?, ?, ?, ?)",
            (endpoint, data_hash, raw_data or data_str, has_changed)
        )
        
        # Сохраняем детализацию изменений
        if has_changed and changes and last_record:
            snapshot_id = cursor.lastrowid
            for change in changes:
                # Парсим описание изменения (формат: "Тип: поле: старое -> новое")
                change_type = "modified"
                field_path = None
                old_value = None
                new_value = None
                
                if change.startswith("Добавлено:"):
                    change_type = "added"
                elif change.startswith("Удалено:"):
                    change_type = "deleted"
                elif change.startswith("Изменено:") or change.startswith("Изменён"):
                    change_type = "modified"
                
                cursor.execute(
                    "INSERT INTO change_history (snapshot_id, change_type, field_path, old_value, new_value) VALUES (?, ?, ?, ?, ?)",
                    (snapshot_id, change_type, field_path, old_value, new_value)
                )

    return has_changed


def get_latest_snapshot(endpoint: str) -> Optional[Dict]:
    """Получает последний снимок для эндпоинта."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM snapshots WHERE endpoint=? ORDER BY id DESC LIMIT 1",
            (endpoint,)
        )
        record = cursor.fetchone()
        return dict(record) if record else None


def get_change_history(endpoint: str, limit: int = 100) -> List[Dict]:
    """
    Получает историю изменений для эндпоинта.
    
    Args:
        endpoint: Путь к эндпоинту
        limit: Максимальное количество записей
        
    Returns:
        Список записей об изменениях
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ch.*, s.endpoint 
            FROM change_history ch
            JOIN snapshots s ON ch.snapshot_id = s.id
            WHERE s.endpoint = ?
            ORDER BY ch.timestamp DESC
            LIMIT ?
        """, (endpoint, limit))
        
        return [dict(row) for row in cursor.fetchall()]


def get_snapshots_count() -> int:
    """Возвращает общее количество снимков в базе."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM snapshots")
        return cursor.fetchone()[0]
