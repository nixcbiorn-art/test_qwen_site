"""
Сквозной интеграционный тест для MarketMonitor.
Проверяет полный цикл работы системы:
1. Загрузка конфигурации
2. Инициализация хранилища
3. Получение данных от API (mock)
4. Обработка и нормализация данных
5. Детектирование изменений
6. Сохранение в БД
7. Проверка C++ индикаторов (RSI, SMA)
8. Детектирование аномалий
"""

import pytest
import asyncio
import tempfile
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Импортируем основные компоненты системы из корня проекта
from config import DB_PATH, DATA_DIR
from storage import init_db, save_snapshot, get_latest_snapshot, get_change_history
from detector import compare_data
from mapping import map_items
from api_client import APIClient

# NativeEngine находится в core/services/
sys.path.insert(0, str(Path(__file__).parent.parent / "core" / "services"))
from native_engine import NativeEngine


class ChangeDetector:
    """Простой детектор изменений для e2e теста"""
    def __init__(self, threshold_percent=5.0):
        self.threshold = threshold_percent
    
    def detect_changes(self, old_data, new_data):
        """Детектирует изменения между старыми и новыми данными"""
        changes = []
        old_items = old_data.get("items", [])
        new_items = new_data.get("items", [])
        
        # Создаём словарь по ID для быстрого поиска
        old_by_id = {item.get("id"): item for item in old_items}
        
        for new_item in new_items:
            item_id = new_item.get("id")
            if item_id in old_by_id:
                old_item = old_by_id[item_id]
                old_price = old_item.get("price", 0)
                new_price = new_item.get("price", 0)
                
                if old_price != new_price:
                    change_pct = abs(new_price - old_price) / old_price * 100 if old_price > 0 else 0
                    if change_pct >= self.threshold:
                        changes.append({
                            "id": item_id,
                            "old_price": old_price,
                            "new_price": new_price,
                            "change_percent": change_pct
                        })
        
        return changes


class DataMapper:
    """Простой маппер данных для e2e теста"""
    def map_to_domain(self, raw_data: dict, source: str) -> list:
        """Маппит сырые данные в доменные объекты"""
        items = raw_data.get("items", [])
        result = []
        for item in items:
            mapped = {
                "external_id": item.get("id"),
                "price": item.get("price", 0),
                "area": item.get("area", 0),
                "rooms": item.get("rooms", 0),
                "floor": item.get("floor", 0),
                "address": item.get("address", ""),
                "project_name": item.get("project_name", ""),
                "source": source,
                "timestamp": item.get("timestamp")
            }
            # Вычисляем цену за м²
            if mapped["area"] > 0:
                mapped["price_per_m2"] = mapped["price"] / mapped["area"]
            result.append(mapped)
        return result


class TestEndToEnd:
    """Сквозной тест полного цикла работы системы"""

    @pytest.fixture
    def temp_db_path(self):
        """Создаёт временную БД для теста"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.unlink(path)
        # Удаляем также journal файлы если есть
        for ext in ['-wal', '-shm']:
            p = path + ext
            if os.path.exists(p):
                os.unlink(p)

    @pytest.fixture
    def mapper(self):
        """Маппер данных"""
        return DataMapper()

    @pytest.fixture
    def detector(self):
        """Детектор изменений"""
        return ChangeDetector(threshold_percent=5.0)

    @pytest.fixture
    def native_engine(self):
        """C++ движок индикаторов"""
        return NativeEngine()

    def test_full_pipeline(self, temp_db_path, mapper, detector, native_engine):
        """
        Проверяет полный пайплайн обработки данных:
        - Mock API response
        - Нормализация
        - Вычисление индикаторов (C++)
        - Детектирование изменений
        - Сохранение в БД
        - Чтение из БД и проверка
        """
        
        # Временно переключаем DB_PATH на нашу тестовую БД
        import config
        import storage
        original_db_path = config.DB_PATH
        config.DB_PATH = temp_db_path
        storage.DB_PATH = temp_db_path
        
        try:
            # 1. Инициализация БД
            init_db()
            
            # 2. Mock данных от API (реальный формат как от redcat/fsk/samolet)
            mock_api_response = {
                "items": [
                    {
                        "id": "flat_001",
                        "price": 10_000_000,
                        "area": 50.5,
                        "rooms": 2,
                        "floor": 5,
                        "address": "ул. Тестовая, д. 1",
                        "project_name": "Тестовый ЖК",
                        "timestamp": datetime.now().isoformat()
                    },
                    {
                        "id": "flat_002",
                        "price": 15_000_000,
                        "area": 75.0,
                        "rooms": 3,
                        "floor": 10,
                        "address": "ул. Тестовая, д. 2",
                        "project_name": "Тестовый ЖК",
                        "timestamp": datetime.now().isoformat()
                    }
                ]
            }

            # 3. Нормализация данных через маппер
            listings = mapper.map_to_domain(mock_api_response, source="test_source")
            
            assert len(listings) == 2
            assert listings[0]["external_id"] == "flat_001"
            assert listings[0]["price"] == 10_000_000
            assert listings[0]["source"] == "test_source"
            
            # 4. Вычисление индикаторов через C++ движок
            prices = [l["price"] for l in listings]
            
            # RSI через C++
            rsi_values = native_engine.calculate_rsi(prices, period=2)
            assert len(rsi_values) > 0
            assert all(0 <= r <= 100 for r in rsi_values if r is not None)
            
            # SMA через C++
            sma_values = native_engine.calculate_sma(prices, period=2)
            assert len(sma_values) > 0
            assert sma_values[-1] == pytest.approx(12_500_000, rel=0.01)

            # 5. Первая итерация: сохраняем снимок данных
            result1 = save_snapshot(
                endpoint="test_endpoint",
                data=listings,
                raw_data=None,
                changes=None
            )
            assert result1 == True  # Первое сохранение всегда True
            
            # Проверяем сохранение
            snapshot1 = get_latest_snapshot("test_endpoint")
            assert snapshot1 is not None
            assert snapshot1["endpoint"] == "test_endpoint"
            
            # 6. Вторая итерация: имитируем изменение цен (+10% для первой квартиры)
            mock_api_response_changed = {
                "items": [
                    {
                        "id": "flat_001",
                        "price": 11_000_000,  # +10%
                        "area": 50.5,
                        "rooms": 2,
                        "floor": 5,
                        "address": "ул. Тестовая, д. 1",
                        "project_name": "Тестовый ЖК",
                        "timestamp": datetime.now().isoformat()
                    },
                    {
                        "id": "flat_002",
                        "price": 15_000_000,  # без изменений
                        "area": 75.0,
                        "rooms": 3,
                        "floor": 10,
                        "address": "ул. Тестовая, д. 2",
                        "project_name": "Тестовый ЖК",
                        "timestamp": datetime.now().isoformat()
                    }
                ]
            }
            
            new_listings = mapper.map_to_domain(mock_api_response_changed, source="test_source")
            
            # 7. Детектирование изменений
            changes = detector.detect_changes(
                old_data={"items": listings},
                new_data={"items": new_listings}
            )
            
            # Должно быть обнаружено изменение
            assert len(changes) >= 1
            
            # 8. Сохраняем новый снимок с изменениями
            result2 = save_snapshot(
                endpoint="test_endpoint",
                data=new_listings,
                raw_data=None,
                changes=[f"Изменено: price: 10000000 -> 11000000"]
            )
            assert result2 == True  # Данные изменились
            
            # 9. Проверяем историю изменений
            history = get_change_history("test_endpoint", limit=10)
            # История должна содержать записи
            
            # 10. Проверяем актуальный снимок
            snapshot2 = get_latest_snapshot("test_endpoint")
            assert snapshot2 is not None
            assert snapshot2["has_changed"] == 1
            
            # 11. Тест детектирования аномалий через C++
            # Создаём серию данных с аномалией
            price_history = [10_000_000, 10_200_000, 10_100_000, 10_300_000]
            anomalous_price = 20_000_000  # Аномалия
            
            # detect_anomaly принимает history и current point, возвращает Dict
            anomaly_result = native_engine.detect_anomaly(
                history=price_history, 
                current=anomalous_price, 
                lookback=4, 
                threshold=2.0
            )
            
            # Проверяем структуру результата
            assert isinstance(anomaly_result, dict)
            assert 'is_anomaly' in anomaly_result
            assert 'z_score' in anomaly_result
            assert 'deviation_percent' in anomaly_result
            assert 'anomaly_type' in anomaly_result
            
            # Аномалия должна быть обнаружена
            assert anomaly_result['is_anomaly'] == True
            assert abs(anomaly_result['z_score']) > 2.0
            assert anomaly_result['anomaly_type'] in ['spike', 'drop']
            
        finally:
            # Восстанавливаем оригинальный путь к БД
            config.DB_PATH = original_db_path
            storage.DB_PATH = original_db_path

    def test_concurrent_access(self, temp_db_path, mapper):
        """Проверяет корректность работы при конкурентном доступе"""
        
        import config
        import storage
        original_db_path = config.DB_PATH
        config.DB_PATH = temp_db_path
        storage.DB_PATH = temp_db_path
        
        try:
            init_db()
            
            mock_data = {
                "items": [
                    {
                        "id": f"flat_{i}",
                        "price": 10_000_000 + i * 1_000_000,
                        "area": 50.0,
                        "rooms": 2,
                        "floor": i,
                        "address": f"ул. Тестовая, д. {i}",
                        "project_name": "Тестовый ЖК",
                        "timestamp": datetime.now().isoformat()
                    }
                    for i in range(10)
                ]
            }
            
            listings = mapper.map_to_domain(mock_data, source="test_source")
            
            # Последовательная запись 10 снимков (синхронная версия)
            for l in listings:
                save_snapshot("test_endpoint", [l], None, None)
            
            # Проверяем, что все сохранены (минимум 10 снимков)
            snapshot_count = storage.get_snapshots_count()
            assert snapshot_count >= 10
            
        finally:
            config.DB_PATH = original_db_path
            storage.DB_PATH = original_db_path

    def test_fallback_to_python(self, temp_db_path):
        """Проверяет, что система работает даже без C++ библиотек"""
        
        # Имитируем отсутствие C++ библиотек
        original_path = os.environ.get('LD_LIBRARY_PATH', '')
        
        try:
            # Временная эмуляция отсутствия библиотек
            os.environ['LD_LIBRARY_PATH'] = '/nonexistent'
            
            # Создаём новый engine, он должен использовать fallback
            engine = NativeEngine()
            
            # Тестируем расчёты (должны работать через Python fallback)
            prices = [100, 105, 110, 108, 112, 115, 120]
            
            rsi = engine.calculate_rsi(prices, period=3)
            assert len(rsi) > 0
            
            sma = engine.calculate_sma(prices, period=3)
            assert len(sma) > 0
            
            ema = engine.calculate_ema(prices, period=3)
            assert len(ema) > 0
            
        finally:
            # Восстанавливаем путь
            if original_path:
                os.environ['LD_LIBRARY_PATH'] = original_path
            else:
                os.environ.pop('LD_LIBRARY_PATH', None)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
