"""
Тестовый клиент для проверки API с интервалом 30 секунд.
Отправляет запросы к ping-серверу в течение 10 минут.
"""
import asyncio
import aiohttp
import time
from datetime import datetime

PING_URL = "http://localhost:8080/ping"
STATUS_URL = "http://localhost:8080/api/status"
DATA_URL = "http://localhost:8080/api/data/AAPL"
INTERVAL = 30  # секунд между запросами
DURATION = 600  # 10 минут в секундах

async def make_request(session, url, endpoint_name):
    """Сделать запрос и вернуть результат"""
    try:
        start = time.time()
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            elapsed = (time.time() - start) * 1000  # мс
            data = await response.json()
            return {
                "endpoint": endpoint_name,
                "status": response.status,
                "time_ms": round(elapsed, 2),
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }
    except Exception as e:
        return {
            "endpoint": endpoint_name,
            "status": "ERROR",
            "time_ms": None,
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

async def run_test():
    """Запустить тестирование"""
    print(f"🚀 Запуск теста API на {DURATION//60} минут (интервал {INTERVAL} сек)")
    print(f"Начало: {datetime.utcnow().isoformat()}")
    print("-" * 60)
    
    start_time = time.time()
    request_count = 0
    success_count = 0
    error_count = 0
    
    async with aiohttp.ClientSession() as session:
        while (time.time() - start_time) < DURATION:
            cycle_start = time.time()
            request_count += 1
            
            print(f"\n📡 Запрос #{request_count} [{datetime.utcnow().strftime('%H:%M:%S')}]")
            
            # Делаем запросы ко всем эндпоинтам
            tasks = [
                make_request(session, PING_URL, "ping"),
                make_request(session, STATUS_URL, "status"),
                make_request(session, DATA_URL, "data")
            ]
            
            results = await asyncio.gather(*tasks)
            
            for result in results:
                status_icon = "✅" if result["status"] == 200 else "❌"
                if result["status"] == 200:
                    success_count += 1
                else:
                    error_count += 1
                
                if result["status"] == 200:
                    print(f"  {status_icon} {result['endpoint']:10s} | Status: {result['status']} | Time: {result['time_ms']}ms")
                else:
                    print(f"  {status_icon} {result['endpoint']:10s} | Status: {result['status']} | Error: {result.get('error', 'N/A')}")
            
            # Ждём до следующего интервала
            elapsed_cycle = time.time() - cycle_start
            wait_time = max(0, INTERVAL - elapsed_cycle)
            if wait_time > 0 and (time.time() - start_time) < DURATION:
                print(f"  ⏳ Ожидание {wait_time:.1f} сек до следующего запроса...")
                await asyncio.sleep(wait_time)
    
    # Итоги
    print("\n" + "=" * 60)
    print("📊 ИТОГИ ТЕСТА")
    print("=" * 60)
    print(f"Длительность: {(time.time() - start_time)/60:.2f} минут")
    print(f"Всего запросов: {request_count * 3}")  # 3 эндпоинта за цикл
    print(f"Успешных: {success_count}")
    print(f"Ошибок: {error_count}")
    print(f"Процент успеха: {success_count/(success_count+error_count)*100:.1f}%")
    print(f"Конец: {datetime.utcnow().isoformat()}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_test())
