#!/usr/bin/env python3
"""
Боевой тест: Сбор данных о погоде с Open-Meteo API (бесплатно, без ключа)
Длительность: 10 минут
Интервал: 30 секунд
Аналитика в реальном времени
"""

import requests
import time
import json
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sys

# Конфигурация
API_URL = "https://api.open-meteo.com/v1/forecast"
CITIES = {
    "Moscow": {"lat": 55.7558, "lon": 37.6173},
    "London": {"lat": 51.5074, "lon": -0.1278},
    "New York": {"lat": 40.7128, "lon": -74.0060},
    "Tokyo": {"lat": 35.6762, "lon": 139.6503}
}
PARAMS = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
INTERVAL_SECONDS = 30
DURATION_MINUTES = 10

def fetch_weather(city_name, coords):
    """Запрос к API погоды"""
    try:
        params = {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "current": PARAMS,
            "timezone": "auto"
        }
        response = requests.get(API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        current = data.get("current", {})
        return {
            "timestamp": datetime.now(),
            "city": city_name,
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "precipitation": current.get("precipitation"),
            "wind_speed": current.get("wind_speed_10m"),
            "status": "success"
        }
    except Exception as e:
        return {
            "timestamp": datetime.now(),
            "city": city_name,
            "temperature": None,
            "humidity": None,
            "precipitation": None,
            "wind_speed": None,
            "status": "error",
            "error": str(e)
        }

def main():
    print("=" * 60)
    print("🌍 БОЕВОЙ ТЕСТ: СБОР ДАННЫХ ПОГОДЫ (OPEN-METEO API)")
    print("=" * 60)
    print(f"📍 Города: {', '.join(CITIES.keys())}")
    print(f"⏱ Интервал: {INTERVAL_SECONDS} сек")
    print(f"⏳ Длительность: {DURATION_MINUTES} мин")
    print(f"🔗 API: {API_URL}")
    print("=" * 60)
    
    all_data = []
    start_time = time.time()
    cycle = 0
    
    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed >= DURATION_MINUTES * 60:
                print("\n✅ Время теста истекло!")
                break
            
            cycle += 1
            print(f"\n🔄 Цикл {cycle} | {datetime.now().strftime('%H:%M:%S')} | Прошло: {elapsed/60:.1f} мин")
            
            cycle_data = []
            for city, coords in CITIES.items():
                result = fetch_weather(city, coords)
                cycle_data.append(result)
                all_data.append(result)
                
                status_icon = "✅" if result["status"] == "success" else "❌"
                temp = f"{result['temperature']}°C" if result['temperature'] is not None else "N/A"
                print(f"  {status_icon} {city}: {temp}, влажность: {result['humidity']}%, ветер: {result['wind_speed']} м/с")
            
            # Быстрая аналитика за последний цикл
            temps = [d['temperature'] for d in cycle_data if d['temperature'] is not None]
            if temps:
                avg_temp = sum(temps) / len(temps)
                max_temp = max(temps)
                min_temp = min(temps)
                print(f"  📊 Средняя температура по городам: {avg_temp:.1f}°C (мин: {min_temp}°, макс: {max_temp}°)")
            
            # Ждем следующего интервала
            sleep_time = max(0, INTERVAL_SECONDS - (time.time() - start_time - (cycle - 1) * INTERVAL_SECONDS))
            if elapsed + sleep_time < DURATION_MINUTES * 60:
                time.sleep(sleep_time)
    
    except KeyboardInterrupt:
        print("\n⚠ Тест прерван пользователем")
    
    # Финальная аналитика
    print("\n" + "=" * 60)
    print("📈 ФИНАЛЬНАЯ АНАЛИТИКА")
    print("=" * 60)
    
    df = pd.DataFrame(all_data)
    
    # Статистика по успешности
    total_requests = len(df)
    successful = len(df[df['status'] == 'success'])
    success_rate = (successful / total_requests * 100) if total_requests > 0 else 0
    print(f"Всего запросов: {total_requests}")
    print(f"Успешных: {successful} ({success_rate:.1f}%)")
    print(f"Ошибок: {total_requests - successful}")
    
    # Статистика по городам
    print("\n📊 Статистика по городам:")
    for city in CITIES.keys():
        city_data = df[df['city'] == city]
        successful_city = len(city_data[city_data['status'] == 'success'])
        temps = city_data['temperature'].dropna()
        
        if len(temps) > 0:
            print(f"  {city}:")
            print(f"    Успешность: {successful_city}/{len(city_data)} ({successful_city/len(city_data)*100:.1f}%)")
            print(f"    Температура: средн={temps.mean():.1f}°, мин={temps.min():.1f}°, макс={temps.max():.1f}°")
            print(f"    Влажность: средн={city_data['humidity'].mean():.1f}%")
            print(f"    Ветер: средн={city_data['wind_speed'].mean():.1f} м/с")
    
    # Сохранение данных
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"weather_data_{timestamp}.csv"
    df.to_csv(csv_file, index=False)
    print(f"\n💾 Данные сохранены в: {csv_file}")
    
    # Построение графика
    try:
        plt.figure(figsize=(14, 8))
        
        for city in CITIES.keys():
            city_df = df[df['city'] == city].copy()
            city_df = city_df[city_df['temperature'].notna()]
            if len(city_df) > 0:
                plt.plot(city_df['timestamp'], city_df['temperature'], marker='o', label=city, linewidth=2, markersize=4)
        
        plt.xlabel('Время', fontsize=12)
        plt.ylabel('Температура (°C)', fontsize=12)
        plt.title('Динамика температуры в городах (10 минут)', fontsize=14, fontweight='bold')
        plt.legend(loc='best')
        plt.grid(True, alpha=0.3)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.tight_layout()
        
        graph_file = f"weather_graph_{timestamp}.png"
        plt.savefig(graph_file, dpi=150)
        print(f"📊 График сохранен в: {graph_file}")
    except Exception as e:
        print(f"⚠ Не удалось построить график: {e}")
    
    print("\n✅ Тест завершен успешно!")
    return df

if __name__ == "__main__":
    main()
