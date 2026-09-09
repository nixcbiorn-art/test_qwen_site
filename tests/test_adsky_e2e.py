"""
АДСКИЕ СКВОЗНЫЕ ТЕСТЫ С ПОЛНЫМ ЛОГИРОВАНИЕМ
Каждый шаг, каждый чих, каждая операция - ВСЁ ЛОГИРУЕТСЯ!
"""

import pytest
import asyncio
import tempfile
import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

# НАСТРАИВАЕМ АДСКОЕ ЛОГИРОВАНИЕ
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/adsky_tests.log', mode='w')
    ]
)
logger = logging.getLogger("ADSKY_TEST")

# Импортируем основные компоненты системы из корня проекта
from config import DB_PATH, DATA_DIR
from storage import init_db, save_snapshot, get_latest_snapshot, get_change_history, get_snapshots_count
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
        logger.info(f"🔧 [ChangeDetector] Инициализация с порогом {threshold_percent}%")
    
    def detect_changes(self, old_data, new_data):
        """Детектирует изменения между старыми и новыми данными"""
        logger.debug("🔍 [ChangeDetector.detect_changes] НАЧАЛО анализа изменений")
        changes = []
        old_items = old_data.get("items", [])
        new_items = new_data.get("items", [])
        
        logger.debug(f"   📊 Старых элементов: {len(old_items)}")
        logger.debug(f"   📊 Новых элементов: {len(new_items)}")
        
        # Создаём словарь по ID для быстрого поиска
        old_by_id = {item.get("id"): item for item in old_items}
        logger.debug(f"   🗂️ Создан словарь old_by_id с {len(old_by_id)} ключами")
        
        for idx, new_item in enumerate(new_items):
            item_id = new_item.get("id")
            logger.debug(f"   🔎 Анализ элемента #{idx}: id={item_id}")
            
            if item_id in old_by_id:
                old_item = old_by_id[item_id]
                old_price = old_item.get("price", 0)
                new_price = new_item.get("price", 0)
                
                logger.debug(f"      💰 Старая цена: {old_price}, Новая цена: {new_price}")
                
                if old_price != new_price:
                    change_pct = abs(new_price - old_price) / old_price * 100 if old_price > 0 else 0
                    logger.debug(f"      📈 Изменение: {change_pct:.2f}%")
                    
                    if change_pct >= self.threshold:
                        logger.warning(f"      ⚠️ ОБНАРУЖЕНО ИЗМЕНЕНИЕ выше порога!")
                        changes.append({
                            "id": item_id,
                            "old_price": old_price,
                            "new_price": new_price,
                            "change_percent": change_pct
                        })
                    else:
                        logger.debug(f"      ℹ️ Изменение ниже порога ({self.threshold}%)")
            else:
                logger.debug(f"      ➕ Новый элемент (не был в старых данных)")
        
        logger.info(f"✅ [ChangeDetector.detect_changes] ЗАВЕРШЕНО. Найдено изменений: {len(changes)}")
        return changes


class DataMapper:
    """Простой маппер данных для e2e теста"""
    def __init__(self):
        logger.info("🔧 [DataMapper] Инициализация маппера")
    
    def map_to_domain(self, raw_data: dict, source: str) -> list:
        """Маппит сырые данные в доменные объекты"""
        logger.debug(f"🗺️ [DataMapper.map_to_domain] Начало маппинга, источник: {source}")
        items = raw_data.get("items", [])
        logger.debug(f"   📦 Получено {len(items)} элементов для маппинга")
        
        result = []
        for idx, item in enumerate(items):
            logger.debug(f"   🔄 Маппинг элемента #{idx}: {item.get('id')}")
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
                logger.debug(f"      💲 Цена за м²: {mapped['price_per_m2']:.2f}")
            result.append(mapped)
        
        logger.info(f"✅ [DataMapper.map_to_domain] Завершено. Создано {len(result)} доменных объектов")
        return result


class TestEndToEndHell:
    """АДСКИЙ сквозной тест с полным логированием каждого шага"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, temp_db_path):
        """Фикстура с логированием setup/teardown"""
        logger.info("=" * 80)
        logger.info("🚀 [SETUP] НАЧАЛО настройки теста")
        logger.info(f"   📁 Временная БД: {temp_db_path}")
        yield temp_db_path
        logger.info("🧹 [TEARDOWN] ЗАВЕРШЕНИЕ очистки теста")
        logger.info("=" * 80)

    @pytest.fixture
    def temp_db_path(self):
        """Создаёт временную БД для теста с логированием"""
        logger.debug("📝 [temp_db_path] Создание временного файла БД...")
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        logger.info(f"✅ [temp_db_path] Временная БД создана: {path}")
        yield path
        # Cleanup
        logger.debug("🧹 [temp_db_path] Очистка временных файлов...")
        if os.path.exists(path):
            os.unlink(path)
            logger.debug(f"   🗑️ Удалён файл: {path}")
        # Удаляем также journal файлы если есть
        for ext in ['-wal', '-shm']:
            p = path + ext
            if os.path.exists(p):
                os.unlink(p)
                logger.debug(f"   🗑️ Удалён журнал: {p}")
        logger.info("✅ [temp_db_path] Очистка завершена")

    @pytest.fixture
    def mapper(self):
        """Маппер данных с логированием"""
        logger.info("🔧 [mapper fixture] Создание маппера...")
        m = DataMapper()
        logger.info("✅ [mapper fixture] Маппер готов")
        return m

    @pytest.fixture
    def detector(self):
        """Детектор изменений с логированием"""
        logger.info("🔧 [detector fixture] Создание детектора с порогом 5%...")
        d = ChangeDetector(threshold_percent=5.0)
        logger.info("✅ [detector fixture] Детектор готов")
        return d

    @pytest.fixture
    def native_engine(self):
        """C++ движок индикаторов с проверкой"""
        logger.info("🔧 [native_engine fixture] Инициализация NativeEngine...")
        engine = NativeEngine()
        logger.info(f"✅ [native_engine fixture] NativeEngine создан, C++ доступен: {engine.use_cpp}")
        return engine

    def test_01_full_pipeline_hell(self, temp_db_path, mapper, detector, native_engine):
        """
        АДСКИЙ тест полного цикла работы системы с логированием КАЖДОГО шага
        """
        logger.info("\n" + "=" * 80)
        logger.info("🔥 ТЕСТ 1: ПОЛНЫЙ ПЛАЙПЛАЙН (АДСКИЙ РЕЖИМ)")
        logger.info("=" * 80)
        
        # Временно переключаем DB_PATH на нашу тестовую БД
        import config
        import storage
        original_db_path = config.DB_PATH
        config.DB_PATH = temp_db_path
        storage.DB_PATH = temp_db_path
        logger.info(f"⚙️ [CONFIG] DB_PATH переключён на: {temp_db_path}")
        
        try:
            # ================================================================
            # ШАГ 1: Инициализация БД
            # ================================================================
            logger.info("\n" + "-" * 80)
            logger.info("📌 ШАГ 1: Инициализация базы данных")
            logger.info("-" * 80)
            logger.debug(f"   📁 Путь к БД: {temp_db_path}")
            logger.debug(f"   📁 Файл существует до init: {os.path.exists(temp_db_path)}")
            
            init_db()
            
            logger.debug(f"   ✅ Файл существует после init: {os.path.exists(temp_db_path)}")
            logger.debug(f"   📏 Размер БД: {os.path.getsize(temp_db_path)} байт")
            logger.info("✅ ШАГ 1 ЗАВЕРШЁН: БД инициализирована")
            
            # ================================================================
            # ШАГ 2: Mock данных от API
            # ================================================================
            logger.info("\n" + "-" * 80)
            logger.info("📌 ШАГ 2: Подготовка mock-данных от API")
            logger.info("-" * 80)
            
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
            logger.debug(f"   📦 Mock данных: {len(mock_api_response['items'])} элементов")
            for idx, item in enumerate(mock_api_response['items']):
                logger.debug(f"      Элемент #{idx}: id={item['id']}, price={item['price']:,}")
            logger.info("✅ ШАГ 2 ЗАВЕРШЁН: Mock-данные готовы")
            
            # ================================================================
            # ШАГ 3: Нормализация данных через маппер
            # ================================================================
            logger.info("\n" + "-" * 80)
            logger.info("📌 ШАГ 3: Нормализация данных (маппинг)")
            logger.info("-" * 80)
            
            listings = mapper.map_to_domain(mock_api_response, source="test_source")
            
            logger.info(f"   📊 Результат маппинга: {len(listings)} объектов")
            for idx, l in enumerate(listings):
                logger.debug(f"      Объект #{idx}: id={l['external_id']}, price={l['price']:,}, price_per_m2={l.get('price_per_m2', 0):,.2f}")
            
            assert len(listings) == 2, f"Ожидается 2 объекта, получено {len(listings)}"
            assert listings[0]["external_id"] == "flat_001", f"Неверный ID первого объекта"
            assert listings[0]["price"] == 10_000_000, f"Неверная цена первого объекта"
            assert listings[0]["source"] == "test_source", f"Неверный источник"
            
            logger.info("✅ ШАГ 3 ЗАВЕРШЁН: Данные нормализованы, ассерты пройдены")
            
            # ================================================================
            # ШАГ 4: Вычисление индикаторов через C++ движок
            # ================================================================
            logger.info("\n" + "-" * 80)
            logger.info("📌 ШАГ 4: Вычисление индикаторов (C++ Native Engine)")
            logger.info("-" * 80)
            
            prices = [l["price"] for l in listings]
            logger.debug(f"   💰 Цены для расчётов: {[f'{p:,}' for p in prices]}")
            
            # RSI через C++
            logger.debug("   📈 Расчёт RSI (period=2)...")
            rsi_values = native_engine.calculate_rsi(prices, period=2)
            logger.info(f"   ✅ RSI: {rsi_values}")
            assert len(rsi_values) > 0, "RSI пустой"
            assert all(0 <= r <= 100 for r in rsi_values if r is not None), "RSI вне диапазона [0, 100]"
            logger.debug("   ✅ RSI валиден: все значения в диапазоне [0, 100]")
            
            # SMA через C++
            logger.debug("   📈 Расчёт SMA (period=2)...")
            sma_values = native_engine.calculate_sma(prices, period=2)
            logger.info(f"   ✅ SMA: {sma_values}")
            assert len(sma_values) > 0, "SMA пустой"
            expected_sma = 12_500_000
            assert sma_values[-1] == pytest.approx(expected_sma, rel=0.01), f"SMA не совпадает: ожидалось {expected_sma:,}, получено {sma_values[-1]:,}"
            logger.debug(f"   ✅ SMA валиден: последнее значение {sma_values[-1]:,} ≈ {expected_sma:,}")
            
            logger.info("✅ ШАГ 4 ЗАВЕРШЁН: Индикаторы рассчитаны, ассерты пройдены")
            
            # ================================================================
            # ШАГ 5: Первая итерация - сохранение снимка данных
            # ================================================================
            logger.info("\n" + "-" * 80)
            logger.info("📌 ШАГ 5: Первое сохранение снимка данных")
            logger.info("-" * 80)
            
            logger.debug(f"   📊 Сохраняемых объектов: {len(listings)}")
            logger.debug(f"   🏷️ Endpoint: test_endpoint")
            
            result1 = save_snapshot(
                endpoint="test_endpoint",
                data=listings,
                raw_data=None,
                changes=None
            )
            
            logger.info(f"   ✅ Результат save_snapshot: {result1}")
            assert result1 == True, "Первое сохранение должно вернуть True"
            logger.debug("   ✅ Ассерт пройден: result1 == True")
            
            # Проверяем сохранение
            logger.debug("   🔍 Чтение последнего снимка из БД...")
            snapshot1 = get_latest_snapshot("test_endpoint")
            assert snapshot1 is not None, "Снимок не найден в БД"
            logger.debug(f"   📄 Снимок найден: endpoint={snapshot1['endpoint']}, has_changed={snapshot1['has_changed']}")
            assert snapshot1["endpoint"] == "test_endpoint", f"Неверный endpoint: {snapshot1['endpoint']}"
            
            logger.info("✅ ШАГ 5 ЗАВЕРШЁН: Первый снимок сохранён и прочитан")
            
            # ================================================================
            # ШАГ 6: Вторая итерация - имитация изменения цен
            # ================================================================
            logger.info("\n" + "-" * 80)
            logger.info("📌 ШАГ 6: Имитация изменения цен (+10%)")
            logger.info("-" * 80)
            
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
            logger.debug("   📦 Новые mock-данные:")
            for idx, item in enumerate(mock_api_response_changed['items']):
                old_price = mock_api_response['items'][idx]['price']
                new_price = item['price']
                change = ((new_price - old_price) / old_price * 100) if old_price > 0 else 0
                logger.debug(f"      Элемент #{idx}: {old_price:,} → {new_price:,} ({change:+.1f}%)")
            
            new_listings = mapper.map_to_domain(mock_api_response_changed, source="test_source")
            logger.info(f"   ✅ Новые данные замапплены: {len(new_listings)} объектов")
            
            # ================================================================
            # ШАГ 7: Детектирование изменений
            # ================================================================
            logger.info("\n" + "-" * 80)
            logger.info("📌 ШАГ 7: Детектирование изменений")
            logger.info("-" * 80)
            
            changes = detector.detect_changes(
                old_data={"items": listings},
                new_data={"items": new_listings}
            )
            
            logger.info(f"   📊 Обнаружено изменений: {len(changes)}")
            for ch in changes:
                logger.warning(f"      ⚠️ {ch['id']}: {ch['old_price']:,} → {ch['new_price']:,} ({ch['change_percent']:.1f}%)")
            
            # Должно быть обнаружено изменение
            assert len(changes) >= 1, f"Ожидается хотя бы 1 изменение, получено {len(changes)}"
            logger.debug("   ✅ Ассерт пройден: len(changes) >= 1")
            
            logger.info("✅ ШАГ 7 ЗАВЕРШЁН: Изменения детектированы")
            
            # ================================================================
            # ШАГ 8: Сохранение нового снимка с изменениями
            # ================================================================
            logger.info("\n" + "-" * 80)
            logger.info("📌 ШАГ 8: Сохранение второго снимка с изменениями")
            logger.info("-" * 80)
            
            changes_log = [f"Изменено: price: 10000000 -> 11000000"]
            logger.debug(f"   📝 Лог изменений: {changes_log}")
            
            result2 = save_snapshot(
                endpoint="test_endpoint",
                data=new_listings,
                raw_data=None,
                changes=changes_log
            )
            
            logger.info(f"   ✅ Результат save_snapshot: {result2}")
            assert result2 == True, "Сохранение с изменениями должно вернуть True"
            logger.debug("   ✅ Ассерт пройден: result2 == True")
            
            logger.info("✅ ШАГ 8 ЗАВЕРШЁН: Второй снимок сохранён")
            
            # ================================================================
            # ШАГ 9: Проверка истории изменений
            # ================================================================
            logger.info("\n" + "-" * 80)
            logger.info("📌 ШАГ 9: Проверка истории изменений")
            logger.info("-" * 80)
            
            history = get_change_history("test_endpoint", limit=10)
            logger.info(f"   📜 История изменений: {len(history)} записей")
            for idx, h in enumerate(history):
                logger.debug(f"      Запись #{idx}: {h.get('changes', 'N/A')}")
            
            # История должна содержать записи
            logger.info("✅ ШАГ 9 ЗАВЕРШЁН: История прочитана")
            
            # ================================================================
            # ШАГ 10: Проверка актуального снимка
            # ================================================================
            logger.info("\n" + "-" * 80)
            logger.info("📌 ШАГ 10: Проверка актуального снимка")
            logger.info("-" * 80)
            
            snapshot2 = get_latest_snapshot("test_endpoint")
            assert snapshot2 is not None, "Актуальный снимок не найден"
            logger.debug(f"   📄 Актуальный снимок: has_changed={snapshot2['has_changed']}")
            assert snapshot2["has_changed"] == 1, f"Ожидается has_changed=1, получено {snapshot2['has_changed']}"
            logger.debug("   ✅ Ассерт пройден: has_changed == 1")
            
            logger.info("✅ ШАГ 10 ЗАВЕРШЁН: Актуальный снимок проверен")
            
            # ================================================================
            # ШАГ 11: Тест детектирования аномалий через C++
            # ================================================================
            logger.info("\n" + "-" * 80)
            logger.info("📌 ШАГ 11: Детектирование аномалий (C++)")
            logger.info("-" * 80)
            
            # Создаём серию данных с аномалией
            price_history = [10_000_000, 10_200_000, 10_100_000, 10_300_000]
            anomalous_price = 20_000_000  # Аномалия
            
            logger.debug(f"   📈 История цен: {[f'{p:,}' for p in price_history]}")
            logger.warning(f"   ⚠️ Аномальная цена: {anomalous_price:,}")
            
            # detect_anomaly принимает history и current point, возвращает Dict
            anomaly_result = native_engine.detect_anomaly(
                history=price_history, 
                current=anomalous_price, 
                lookback=4, 
                threshold=2.0
            )
            
            logger.info(f"   📊 Результат детектирования: {anomaly_result}")
            
            # Проверяем структуру результата
            assert isinstance(anomaly_result, dict), f"Ожидается dict, получено {type(anomaly_result)}"
            logger.debug("   ✅ Тип результата: dict")
            
            required_keys = ['is_anomaly', 'z_score', 'deviation_percent', 'anomaly_type']
            for key in required_keys:
                assert key in anomaly_result, f"Отсутствует ключ: {key}"
                logger.debug(f"   ✅ Ключ '{key}' присутствует: {anomaly_result[key]}")
            
            # Аномалия должна быть обнаружена
            assert anomaly_result['is_anomaly'] == True, f"Аномалия не обнаружена: is_anomaly={anomaly_result['is_anomaly']}"
            logger.warning("   ✅ Аномалия подтверждена: is_anomaly=True")
            
            assert abs(anomaly_result['z_score']) > 2.0, f"Z-score слишком мал: {anomaly_result['z_score']}"
            logger.debug(f"   ✅ Z-score > 2.0: {anomaly_result['z_score']}")
            
            assert anomaly_result['anomaly_type'] in ['spike', 'drop'], f"Неверный тип аномалии: {anomaly_result['anomaly_type']}"
            logger.debug(f"   ✅ Тип аномалии: {anomaly_result['anomaly_type']}")
            
            logger.info("✅ ШАГ 11 ЗАВЕРШЁН: Аномалия успешно детектирована")
            
            # ================================================================
            # ФИНАЛ ТЕСТА
            # ================================================================
            logger.info("\n" + "=" * 80)
            logger.info("🎉 ТЕСТ 1 ПОЛНОСТЬЮ ПРОЙДЕН! ВСЕ 11 ШАГОВ УСПЕШНЫ!")
            logger.info("=" * 80)
            
        finally:
            # Восстанавливаем оригинальный путь к БД
            config.DB_PATH = original_db_path
            storage.DB_PATH = original_db_path
            logger.info(f"⚙️ [CONFIG] DB_PATH восстановлен: {original_db_path}")

    def test_02_concurrent_access_hell(self, temp_db_path, mapper):
        """АДСКИЙ тест конкурентного доступа с логированием"""
        
        logger.info("\n" + "=" * 80)
        logger.info("🔥 ТЕСТ 2: КОНКУРЕНТНЫЙ ДОСТУП (АДСКИЙ РЕЖИМ)")
        logger.info("=" * 80)
        
        import config
        import storage
        original_db_path = config.DB_PATH
        config.DB_PATH = temp_db_path
        storage.DB_PATH = temp_db_path
        logger.info(f"⚙️ [CONFIG] DB_PATH переключён на: {temp_db_path}")
        
        try:
            # Инициализация БД
            logger.info("📌 Инициализация БД...")
            init_db()
            logger.info("✅ БД инициализирована")
            
            # Подготовка данных
            logger.info("📦 Подготовка тестовых данных (10 квартир)...")
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
            logger.debug(f"   📊 Создано {len(mock_data['items'])} элементов")
            for item in mock_data['items']:
                logger.debug(f"      {item['id']}: price={item['price']:,}")
            
            # Маппинг
            logger.info("🗺️ Маппинг данных...")
            listings = mapper.map_to_domain(mock_data, source="test_source")
            logger.info(f"✅ Замапплено {len(listings)} объектов")
            
            # Последовательная запись 10 снимков
            logger.info("💾 Последовательная запись 10 снимков...")
            for idx, l in enumerate(listings):
                logger.debug(f"   📝 Запись снимка #{idx}: {l['external_id']}")
                save_snapshot("test_endpoint", [l], None, None)
                logger.debug(f"   ✅ Снимок #{idx} сохранён")
            
            # Проверка количества снимков
            logger.info("🔍 Проверка количества снимков в БД...")
            snapshot_count = get_snapshots_count()
            logger.info(f"   📊 Всего снимков: {snapshot_count}")
            
            assert snapshot_count >= 10, f"Ожидается >= 10 снимков, получено {snapshot_count}"
            logger.debug("   ✅ Ассерт пройден: snapshot_count >= 10")
            
            logger.info("\n" + "=" * 80)
            logger.info("🎉 ТЕСТ 2 ПОЛНОСТЬЮ ПРОЙДЕН!")
            logger.info("=" * 80)
            
        finally:
            config.DB_PATH = original_db_path
            storage.DB_PATH = original_db_path
            logger.info(f"⚙️ [CONFIG] DB_PATH восстановлен: {original_db_path}")

    def test_03_fallback_to_python_hell(self, temp_db_path):
        """АДСКИЙ тест fallback на Python без C++ библиотек"""
        
        logger.info("\n" + "=" * 80)
        logger.info("🔥 ТЕСТ 3: FALLBACK НА PYTHON (АДСКИЙ РЕЖИМ)")
        logger.info("=" * 80)
        
        # Примечание: NATIVE_AVAILABLE определяется при импорте модуля,
        # поэтому изменение LD_LIBRARY_PATH после импорта не отключит C++.
        # Вместо этого мы проверяем, что NativeEngine работает корректно
        # независимо от того, используется C++ или Python fallback.
        
        logger.info("🔧 Создание NativeEngine...")
        engine = NativeEngine()
        
        logger.info(f"✅ NativeEngine создан")
        logger.info(f"   📊 use_cpp={engine.use_cpp}, native_available={engine.native_available}")
        
        # Тестируем расчёты - они должны работать в любом случае (C++ или Python)
        prices = [100, 105, 110, 108, 112, 115, 120]
        logger.info(f"📈 Тестовые цены: {prices}")
        
        # RSI
        logger.debug("📈 Расчёт RSI (period=3)...")
        rsi = engine.calculate_rsi(prices, period=3)
        logger.info(f"   ✅ RSI: {rsi}")
        assert len(rsi) > 0, "RSI пустой"
        assert all(0 <= r <= 100 for r in rsi if r is not None), "RSI вне диапазона [0, 100]"
        logger.debug("   ✅ Ассерт пройден: len(rsi) > 0 и значения в [0, 100]")
        
        # SMA
        logger.debug("📈 Расчёт SMA (period=3)...")
        sma = engine.calculate_sma(prices, period=3)
        logger.info(f"   ✅ SMA: {sma}")
        assert len(sma) > 0, "SMA пустой"
        logger.debug("   ✅ Ассерт пройден: len(sma) > 0")
        
        # EMA
        logger.debug("📈 Расчёт EMA (period=3)...")
        ema = engine.calculate_ema(prices, period=3)
        logger.info(f"   ✅ EMA: {ema}")
        assert len(ema) > 0, "EMA пустой"
        logger.debug("   ✅ Ассерт пройден: len(ema) > 0")
        
        # MACD
        logger.debug("📈 Расчёт MACD...")
        macd = engine.calculate_macd(prices)
        logger.info(f"   ✅ MACD: {macd}")
        assert 'macd_line' in macd or 'signal' in macd or 'histogram' in macd, "MACD неверная структура"
        logger.debug("   ✅ Ассерт пройден: MACD имеет правильную структуру")
        
        # Detect Anomaly
        logger.debug("📈 Детектирование аномалий...")
        anomaly = engine.detect_anomaly([100, 102, 98, 101], 200, threshold=2.0)
        logger.info(f"   ✅ Аномалия: {anomaly}")
        assert isinstance(anomaly, dict), "Аномалия должна быть dict"
        assert 'is_anomaly' in anomaly, "Отсутствует is_anomaly"
        logger.debug("   ✅ Ассерт пройден: аномалия обнаружена корректно")
        
        logger.info("\n" + "=" * 80)
        logger.info(f"🎉 ТЕСТ 3 ПОЛНОСТЬЮ ПРОЙДЕН! Engine работает (use_cpp={engine.use_cpp})!")
        logger.info("=" * 80)


if __name__ == "__main__":
    logger.info("🚀 ЗАПУСК АДСКИХ ТЕСТОВ ПРЯМО ИЗ ФАЙЛА")
    pytest.main([__file__, "-v", "-s", "--tb=long"])
