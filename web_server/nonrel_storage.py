"""
Асинхронное хранилище неструктурированных данных (NoSQL) на базе MongoDB.
Предназначено для сохранения сырых данных парсера (Raw Data Lake).
"""
import os
import json
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId

class MongoRawStorage:
    """Класс для работы с MongoDB для хранения сырых данных парсинга."""

    def __init__(self, uri: str = None, db_name: str = "market_monitor_raw"):
        self.uri = uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.db_name = db_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self._connected = False

    async def connect(self):
        """Установление соединения с MongoDB."""
        if not self._connected:
            try:
                self.client = AsyncIOMotorClient(self.uri, serverSelectionTimeoutMS=5000)
                # Проверка соединения
                await self.client.admin.command('ping')
                self.db = self.client[self.db_name]
                self._connected = True
                print(f"[MongoDB] Connected to {self.uri} -> DB: {self.db_name}")
            except Exception as e:
                print(f"[MongoDB] Connection failed: {e}")
                self._connected = False
                raise e

    async def disconnect(self):
        """Закрытие соединения."""
        if self.client:
            self.client.close()
            self._connected = False
            print("[MongoDB] Connection closed")

    async def store_raw_data(
        self, 
        source_id: str, 
        data: Any, 
        content_type: str = "json", 
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Сохранение сырых данных.
        
        Args:
            source_id: Идентификатор источника (URL, API name).
            data: Сырые данные (dict, list, str).
            content_type: Тип данных ('json', 'html', 'text').
            metadata: Дополнительные метаданные (user_agent, status_code и т.д.).
            
        Returns:
            ID сохраненного документа.
        """
        if not self._connected:
            await self.connect()

        collection = self.db.raw_snapshots

        # Сериализация данных, если это строка (например, HTML)
        if isinstance(data, str) and content_type == "json":
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                pass  # Оставляем как строку, если не валидный JSON

        document = {
            "source_id": source_id,
            "content_type": content_type,
            "raw_data": data,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "processed": False  # Флаг: обработано ли это данные нормализатором
        }

        result = await collection.insert_one(document)
        return str(result.inserted_id)

    async def get_unprocessed(self, source_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Получение необработанных данных для дальнейшей обработки."""
        if not self._connected:
            await self.connect()

        collection = self.db.raw_snapshots
        query = {"processed": False}
        if source_id:
            query["source_id"] = source_id

        cursor = collection.find(query).sort("created_at", 1).limit(limit)
        results = await cursor.to_list(length=limit)

        # Конвертация ObjectId в строку для JSON-сериализации
        for doc in results:
            doc["_id"] = str(doc["_id"])
        
        return results

    async def mark_as_processed(self, record_id: str):
        """Отметка записи как обработанной."""
        if not self._connected:
            await self.connect()

        collection = self.db.raw_snapshots
        try:
            oid = ObjectId(record_id)
            await collection.update_one({"_id": oid}, {"$set": {"processed": True}})
        except Exception as e:
            print(f"[MongoDB] Error marking as processed: {e}")

    async def get_history(self, source_id: str, limit: int = 50) -> List[Dict]:
        """История сырых данных по источнику."""
        if not self._connected:
            await self.connect()

        collection = self.db.raw_snapshots
        query = {"source_id": source_id}
        cursor = collection.find(query).sort("created_at", -1).limit(limit)
        results = await cursor.to_list(length=limit)

        for doc in results:
            doc["_id"] = str(doc["_id"])
            if "created_at" in doc:
                doc["created_at"] = doc["created_at"].isoformat()
        
        return results

    async def cleanup_old_data(self, days: int = 7):
        """Удаление старых сырых данных для экономии места."""
        if not self._connected:
            await self.connect()

        collection = self.db.raw_snapshots
        threshold = datetime.utcnow()
        from datetime import timedelta
        threshold -= timedelta(days=days)
        
        result = await collection.delete_many({"created_at": {"$lt": threshold}})
        print(f"[MongoDB] Deleted {result.deleted_count} old raw records")
        return result.deleted_count

# Глобальный экземпляр (Singleton pattern для использования в приложении)
raw_storage = MongoRawStorage()
