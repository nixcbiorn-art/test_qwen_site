"""
Реляционная база данных на SQLite для хранения данных о погоде.
Поддерживает:
1. Сохранение записей о погоде
2. Получение истории по городам
3. Аналитику через SQL-запросы
4. Автоматическую очистку старых записей
"""

import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "weather.db")

class WeatherDatabase:
    """Класс для работы с реляционной базой данных погоды"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._initialized = False
    
    async def initialize(self):
        """Инициализация базы данных и создание таблиц"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица для хранения данных о погоде
            await db.execute("""
                CREATE TABLE IF NOT EXISTS weather_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city_key TEXT NOT NULL,
                    city_name TEXT NOT NULL,
                    temperature REAL,
                    humidity REAL,
                    wind_speed REAL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Индексы для ускорения поиска
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_city_key 
                ON weather_records(city_key)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON weather_records(timestamp)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_city_timestamp 
                ON weather_records(city_key, timestamp)
            """)
            
            await db.commit()
        
        self._initialized = True
        print(f"Database initialized at {self.db_path}")
    
    async def add_record(self, city_key: str, city_name: str, 
                         temperature: Optional[float], 
                         humidity: Optional[float], 
                         wind_speed: Optional[float],
                         timestamp: str):
        """Добавление записи о погоде"""
        if not self._initialized:
            await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO weather_records 
                (city_key, city_name, temperature, humidity, wind_speed, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (city_key, city_name, temperature, humidity, wind_speed, timestamp))
            await db.commit()
    
    async def get_all_records(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Получение всех записей с ограничением"""
        if not self._initialized:
            await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT id, city_key, city_name, temperature, humidity, 
                       wind_speed, timestamp, created_at
                FROM weather_records
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_records_by_city(self, city_key: str, 
                                   limit: int = 100) -> List[Dict[str, Any]]:
        """Получение записей по конкретному городу"""
        if not self._initialized:
            await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT id, city_key, city_name, temperature, humidity, 
                       wind_speed, timestamp, created_at
                FROM weather_records
                WHERE city_key = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (city_key, limit))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_analytics(self) -> Dict[str, Any]:
        """Получение аналитики через SQL-агрегацию"""
        if not self._initialized:
            await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Общая статистика
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    AVG(temperature) as avg_temperature,
                    MAX(temperature) as max_temperature,
                    MIN(temperature) as min_temperature,
                    AVG(humidity) as avg_humidity,
                    MAX(wind_speed) as max_wind_speed
                FROM weather_records
                WHERE temperature IS NOT NULL
            """)
            stats = await cursor.fetchone()
            
            if not stats or stats['total_records'] == 0:
                return {
                    "total_records": 0,
                    "avg_temperature": None,
                    "max_temperature": None,
                    "min_temperature": None,
                    "avg_humidity": None,
                    "max_wind_speed": None,
                    "hottest_city": None,
                    "coldest_city": None,
                    "windiest_city": None
                }
            
            # Самый жаркий город (последние записи по каждому городу)
            cursor = await db.execute("""
                SELECT city_name, temperature
                FROM weather_records w1
                WHERE timestamp = (
                    SELECT MAX(timestamp) 
                    FROM weather_records w2 
                    WHERE w2.city_key = w1.city_key
                )
                AND temperature IS NOT NULL
                ORDER BY temperature DESC
                LIMIT 1
            """)
            hottest = await cursor.fetchone()
            
            # Самый холодный город
            cursor = await db.execute("""
                SELECT city_name, temperature
                FROM weather_records w1
                WHERE timestamp = (
                    SELECT MAX(timestamp) 
                    FROM weather_records w2 
                    WHERE w2.city_key = w1.city_key
                )
                AND temperature IS NOT NULL
                ORDER BY temperature ASC
                LIMIT 1
            """)
            coldest = await cursor.fetchone()
            
            # Самый ветреный город
            cursor = await db.execute("""
                SELECT city_name, wind_speed
                FROM weather_records w1
                WHERE timestamp = (
                    SELECT MAX(timestamp) 
                    FROM weather_records w2 
                    WHERE w2.city_key = w1.city_key
                )
                AND wind_speed IS NOT NULL
                ORDER BY wind_speed DESC
                LIMIT 1
            """)
            windiest = await cursor.fetchone()
            
            return {
                "total_records": stats['total_records'],
                "avg_temperature": round(stats['avg_temperature'], 1) if stats['avg_temperature'] else None,
                "max_temperature": stats['max_temperature'],
                "min_temperature": stats['min_temperature'],
                "avg_humidity": round(stats['avg_humidity'], 1) if stats['avg_humidity'] else None,
                "max_wind_speed": stats['max_wind_speed'],
                "hottest_city": hottest['city_name'] if hottest else None,
                "coldest_city": coldest['city_name'] if coldest else None,
                "windiest_city": windiest['city_name'] if windiest else None
            }
    
    async def get_chart_data(self, city_key: str, 
                              limit: int = 50) -> Dict[str, List]:
        """Получение данных для графика по городу"""
        records = await self.get_records_by_city(city_key, limit)
        
        # Сортировка по времени (от старого к новому)
        records.sort(key=lambda x: x['timestamp'])
        
        return {
            "timestamps": [r['timestamp'] for r in records],
            "temperatures": [r['temperature'] for r in records],
            "humidities": [r['humidity'] for r in records],
            "wind_speeds": [r['wind_speed'] for r in records]
        }
    
    async def cleanup_old_records(self, days_to_keep: int = 7):
        """Удаление старых записей (старше N дней)"""
        if not self._initialized:
            await self.initialize()
        
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM weather_records
                WHERE timestamp < ?
            """, (cutoff_date,))
            deleted_count = cursor.rowcount
            await db.commit()
        
        return deleted_count
    
    async def get_total_count(self) -> int:
        """Получение общего количества записей"""
        if not self._initialized:
            await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM weather_records")
            result = await cursor.fetchone()
            return result[0] if result else 0


# Глобальный экземпляр базы данных
db = WeatherDatabase()


async def get_db() -> WeatherDatabase:
    """Получение экземпляра базы данных"""
    if not db._initialized:
        await db.initialize()
    return db
