"""Асинхронная работа с SQLite на основе aiosqlite."""

import json
import hashlib
import os
import structlog
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import aiosqlite
from config import DB_PATH, DATA_DIR

logger = structlog.get_logger()


class AsyncDatabaseError(Exception):
    """Базовое исключение для ошибок асинхронной базы данных."""
    pass


@asynccontextmanager
async def get_async_db_connection():
    """Асинхронный контекстный менеджер для подключения к БД."""
    conn = None
    try:
        conn = await aiosqlite.connect(DB_PATH)
        conn.row_factory = aiosqlite.Row
        yield conn
        await conn.commit()
    except aiosqlite.Error as e:
        if conn:
            await conn.rollback()
        raise AsyncDatabaseError(f"Ошибка асинхронной базы данных: {e}")
    finally:
        if conn:
            await conn.close()


async def init_async_db():
    """Асинхронная инициализация базы данных."""
    os.makedirs(DATA_DIR, exist_ok=True)
    logger.info("async_database_initialization_started", db_path=DB_PATH)
    
    async with get_async_db_connection() as conn:
        cursor = await conn.cursor()
        
        # Таблица снимков данных
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS async_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                endpoint TEXT NOT NULL,
                data_hash TEXT NOT NULL,
                raw_data TEXT,
                has_changed BOOLEAN DEFAULT 0
            )
        """)
        
        # Таблица истории изменений с детализацией
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS async_change_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                change_type TEXT NOT NULL,
                field_path TEXT,
                old_value TEXT,
                new_value TEXT,
                FOREIGN KEY (snapshot_id) REFERENCES async_snapshots(id)
            )
        """)
        
        # Индексы для ускорения поиска
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_async_endpoint ON async_snapshots(endpoint)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_async_timestamp ON async_snapshots(timestamp)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_async_change_snapshot ON async_change_history(snapshot_id)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_async_change_type ON async_change_history(change_type)")
        
        logger.info("async_database_initialization_completed")


async def save_async_snapshot(endpoint: str, data: Any, raw_data: Optional[str] = None, 
                              changes: Optional[List[str]] = None) -> bool:
    """
    Асинхронно сохраняет снимок данных и историю изменений.
    
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

    async with get_async_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            "SELECT id, data_hash FROM async_snapshots WHERE endpoint=? ORDER BY id DESC LIMIT 1",
            (endpoint,)
        )
        last_record = await cursor.fetchone()

        has_changed = True
        if last_record and last_record['data_hash'] == data_hash:
            has_changed = False

        await cursor.execute(
            "INSERT INTO async_snapshots (endpoint, data_hash, raw_data, has_changed) VALUES (?, ?, ?, ?)",
            (endpoint, data_hash, raw_data or data_str, has_changed)
        )
        
        snapshot_id = cursor.lastrowid
        
        if has_changed:
            logger.info("async_data_changed_detected", endpoint=endpoint, snapshot_id=snapshot_id)
        
        # Сохраняем детализацию изменений
        if has_changed and changes and last_record:
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
                
                await cursor.execute(
                    "INSERT INTO async_change_history (snapshot_id, change_type, field_path, old_value, new_value) VALUES (?, ?, ?, ?, ?)",
                    (snapshot_id, change_type, field_path, old_value, new_value)
                )

    return has_changed


async def get_async_latest_snapshot(endpoint: str) -> Optional[Dict]:
    """Асинхронно получает последний снимок для эндпоинта."""
    async with get_async_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute(
            "SELECT * FROM async_snapshots WHERE endpoint=? ORDER BY id DESC LIMIT 1",
            (endpoint,)
        )
        record = await cursor.fetchone()
        return dict(record) if record else None


async def get_async_change_history(endpoint: str, limit: int = 100) -> List[Dict]:
    """
    Асинхронно получает историю изменений для эндпоинта.
    
    Args:
        endpoint: Путь к эндпоинту
        limit: Максимальное количество записей
        
    Returns:
        Список записей об изменениях
    """
    async with get_async_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute("""
            SELECT ch.*, s.endpoint 
            FROM async_change_history ch
            JOIN async_snapshots s ON ch.snapshot_id = s.id
            WHERE s.endpoint = ?
            ORDER BY ch.timestamp DESC
            LIMIT ?
        """, (endpoint, limit))
        
        return [dict(row) for row in await cursor.fetchall()]


async def get_async_snapshots_count() -> int:
    """Асинхронно возвращает общее количество снимков в базе."""
    async with get_async_db_connection() as conn:
        cursor = await conn.cursor()
        await cursor.execute("SELECT COUNT(*) FROM async_snapshots")
        result = await cursor.fetchone()
        return result[0] if result else 0
