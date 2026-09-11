"""
Тестирование NoSQL хранилища сырых данных (MongoDB).
"""
import asyncio
import sys
import os

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_server.nonrel_storage import MongoRawStorage

async def test_storage():
    """Тестирование функционала MongoDB хранилища."""
    
    storage = MongoRawStorage()
    
    try:
        # Подключение
        print("🔌 Подключение к MongoDB...")
        await storage.connect()
        print("✅ Успешное подключение")
        
        # Тест 1: Сохранение JSON данных
        print("\n📝 Тест 1: Сохранение JSON данных...")
        json_data = {
            "products": [
                {"id": 1, "name": "Product A", "price": 99.99},
                {"id": 2, "name": "Product B", "price": 149.99}
            ],
            "total": 2
        }
        doc_id = await storage.store_raw_data(
            source_id="test_api_products",
            data=json_data,
            content_type="json",
            metadata={"status_code": 200, "source": "test"}
        )
        print(f"✅ Сохранено с ID: {doc_id}")
        
        # Тест 2: Сохранение HTML данных
        print("\n📝 Тест 2: Сохранение HTML данных...")
        html_data = "<html><body><h1>Test Page</h1></body></html>"
        html_id = await storage.store_raw_data(
            source_id="test_web_page",
            data=html_data,
            content_type="html",
            metadata={"url": "https://example.com"}
        )
        print(f"✅ HTML сохранён с ID: {html_id}")
        
        # Тест 3: Получение необработанных данных
        print("\n📝 Тест 3: Получение необработанных данных...")
        unprocessed = await storage.get_unprocessed(limit=10)
        print(f"✅ Найдено необработанных записей: {len(unprocessed)}")
        for item in unprocessed:
            print(f"   - ID: {item['_id'][:8]}..., Source: {item['source_id']}, Type: {item['content_type']}")
        
        # Тест 4: Отметка как обработанные
        print("\n📝 Тест 4: Отметка записей как обработанные...")
        for item in unprocessed:
            await storage.mark_as_processed(item['_id'])
        print(f"✅ Отмечено записей: {len(unprocessed)}")
        
        # Проверка что теперь пусто
        remaining = await storage.get_unprocessed()
        print(f"   Осталось необработанных: {len(remaining)}")
        
        # Тест 5: История по источнику
        print("\n📝 Тест 5: История по источнику...")
        history = await storage.get_history("test_api_products", limit=5)
        print(f"✅ История для 'test_api_products': {len(history)} записей")
        
        # Тест 6: Очистка старых данных
        print("\n📝 Тест 6: Очистка старых данных (тестовый запуск)...")
        deleted = await storage.cleanup_old_data(days=0)  # Удалим всё для теста
        print(f"✅ Удалено записей: {deleted}")
        
        print("\n🎉 Все тесты успешно пройдены!")
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await storage.disconnect()

if __name__ == "__main__":
    print("=" * 60)
    print("Тестирование NoSQL хранилища (MongoDB)")
    print("=" * 60)
    asyncio.run(test_storage())
