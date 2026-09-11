import requests
import time
import random
import statistics
from datetime import datetime
import sys

# Конфигурация
DURATION_MINUTES = 10
INTERVAL_SECONDS = 5  # Частый опрос для набора статистики
BASE_LAT = 55.7558    # Москва
BASE_LON = 37.6173
RANGE_DEG = 0.5       # Разброс координат (~50км)

def get_weather(lat, lon):
    """Запрос к Open-Meteo API"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        "timezone": "auto"
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data['current_weather']
    except Exception as e:
        return None

def generate_random_coords():
    """Генерация случайных координат вокруг центра"""
    lat = BASE_LAT + random.uniform(-RANGE_DEG, RANGE_DEG)
    lon = BASE_LON + random.uniform(-RANGE_DEG, RANGE_DEG)
    return round(lat, 4), round(lon, 4)

print(f"🌍 Запуск погодного мониторинга на {DURATION_MINUTES} минут...")
print(f"📍 Центр: Москва ({BASE_LAT}, {BASE_LON}), разброс: {RANGE_DEG}°")
print(f"⏱ Интервал: {INTERVAL_SECONDS} сек")
print("-" * 50)

collected_data = []
start_time = time.time()
end_time = start_time + (DURATION_MINUTES * 60)
iteration = 0

try:
    while time.time() < end_time:
        iteration += 1
        lat, lon = generate_random_coords()
        weather = get_weather(lat, lon)
        
        if weather:
            temp = weather['temperature']
            wind = weather['windspeed']
            code = weather['weathercode']
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            collected_data.append({
                "time": timestamp,
                "lat": lat,
                "lon": lon,
                "temp": temp,
                "wind": wind,
                "code": code
            })
            
            # Вывод прогресса (каждые 10 итераций или в конце)
            if iteration % 10 == 0:
                print(f"[{timestamp}] Точка #{iteration}: {lat}, {lon} -> T: {temp}°C, Wind: {wind} км/ч")
            else:
                # Просто точка для индикации активности
                sys.stdout.write('.')
                sys.stdout.flush()
        else:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Ошибка получения данных")
        
        # Ждем следующий интервал
        time.sleep(INTERVAL_SECONDS)

except KeyboardInterrupt:
    print("\n⚠️ Прервано пользователем")

# --- АНАЛИТИКА ---
print("\n\n" + "=" * 50)
print("📊 АНАЛИТИЧЕСКИЙ ОТЧЕТ")
print("=" * 50)

if collected_data:
    temps = [d['temp'] for d in collected_data]
    winds = [d['wind'] for d in collected_data]
    
    print(f"✅ Всего собрано точек: {len(collected_data)}")
    print(f"⏳ Фактическое время сбора: {len(collected_data) * INTERVAL_SECONDS} сек")
    
    # Температура
    print("\n🌡 ТЕМПЕРАТУРА (°C):")
    print(f"   Среднее: {statistics.mean(temps):.2f}")
    print(f"   Медиана: {statistics.median(temps):.2f}")
    print(f"   Мин: {min(temps):.1f}")
    print(f"   Макс: {max(temps):.1f}")
    print(f"   Разброс (StdDev): {statistics.stdev(temps) if len(temps) > 1 else 0:.2f}")
    
    # Ветер
    print("\n💨 ВЕТЕР (км/ч):")
    print(f"   Средний: {statistics.mean(winds):.2f}")
    print(f"   Порывы (Макс): {max(winds):.1f}")
    
    # Погодные условия
    codes = {d['code'] for d in collected_data}
    print(f"\n☁️ Варианты погоды (коды WMO): {codes}")
    
    # Простая визуализация распределения температур
    print("\n📈 Гистограмма температур:")
    min_t, max_t = int(min(temps)), int(max(temps)) + 1
    bins = {}
    for t in range(min_t, max_t):
        bins[t] = temps.count(t) + temps.count(t+0.1) + temps.count(t+0.2) # Грубая группировка если есть дроби
    
    # Нормализация для вывода
    if bins:
        max_count = max(bins.values()) if bins.values() else 1
        for t in sorted(bins.keys()):
            count = sum(1 for x in temps if int(x) == t) # Пересчет точно по целым для гистограммы
            if count > 0:
                bar = '#' * int((count / max_count) * 40)
                print(f"   {t:3d}°C | {bar} ({count})")
    
    print("\n✅ Тест завершен успешно. API стабильно.")
else:
    print("❌ Данные не собраны.")

