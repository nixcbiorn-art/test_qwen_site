#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Launcher: Site + Analytics + Plugin Backend
Запускает веб-сервер, сборщик аналитики и бэкенд для плагина.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Проверка зависимостей
REQUIRED_PACKAGES = ['fastapi', 'uvicorn', 'aiohttp', 'pandas', 'plotly']

def check_dependencies():
    print("[INFO] Проверка зависимостей...")
    missing = []
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"[WARN] Установка отсутствующих пакетов: {', '.join(missing)}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])
    print("[OK] Зависимости готовы.")

def create_server_file():
    """Создает файл веб-сервера без эмодзи (для совместимости с Windows)"""
    server_code = '''import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import asyncio
import aiohttp
import pandas as pd
from datetime import datetime
import os

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "weather_data.csv")
os.makedirs(BASE_DIR, exist_ok=True)

weather_history = []

async def fetch_weather(session, city, lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=auto"
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                current = data.get("current", {})
                record = {
                    "timestamp": datetime.now().isoformat(),
                    "city": city,
                    "temp": current.get("temperature_2m"),
                    "humidity": current.get("relative_humidity_2m"),
                    "wind": current.get("wind_speed_10m")
                }
                weather_history.append(record)
                return record
    except Exception as e:
        print(f"Error fetching {city}: {e}")
    return None

async def background_collector():
    cities = [
        {"name": "Moscow", "lat": 55.75, "lon": 37.61},
        {"name": "London", "lat": 51.50, "lon": -0.12},
        {"name": "New York", "lat": 40.71, "lon": -74.00},
        {"name": "Tokyo", "lat": 35.67, "lon": 139.65}
    ]
    async with aiohttp.ClientSession() as session:
        while True:
            tasks = [fetch_weather(session, c["name"], c["lat"], c["lon"]) for c in cities]
            await asyncio.gather(*tasks)
            
            if weather_history:
                df = pd.DataFrame(weather_history)
                df.to_csv(DATA_FILE, index=False)
            
            await asyncio.sleep(30)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_collector())

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Weather Analytics</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f0f2f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #333; }
        #plot { width: 100%; height: 600px; }
        .status { color: green; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Global Weather Monitor</h1>
        <p>Status: <span class="status">Live Updating (30s)</span></p>
        <div id="plot"></div>
    </div>
    <script>
        async function updatePlot() {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                if (data.length > 0) {
                    const cities = [...new Set(data.map(d => d.city))];
                    const traces = cities.map(city => {
                        const cityData = data.filter(d => d.city === city);
                        return {
                            x: cityData.map(d => d.timestamp),
                            y: cityData.map(d => d.temp),
                            name: city,
                            type: 'scatter',
                            mode: 'lines+markers'
                        };
                    });
                    Plotly.newPlot('plot', traces, {
                        title: 'Temperature Trends',
                        xaxis: { title: 'Time' },
                        yaxis: { title: 'Temp (C)' }
                    });
                }
            } catch (e) { console.error(e); }
        }
        updatePlot();
        setInterval(updatePlot, 30000);
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

@app.get("/api/data")
async def get_data():
    return weather_history[-100:]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    
    server_path = Path(__file__).parent / "web_server.py"
    with open(server_path, "w", encoding="utf-8") as f:
        f.write(server_code)
    return str(server_path)

def main():
    print("=" * 60)
    print("Universal Launcher: Site + Analytics + Plugin Backend")
    print("=" * 60)
    
    check_dependencies()
    
    server_path = create_server_file()
    print(f"[OK] Файл сервера создан: {server_path}")
    
    print("\n[INFO] Запуск веб-сервера на http://localhost:8000")
    print("[INFO] Нажмите Ctrl+C для остановки\n")
    
    try:
        subprocess.run([sys.executable, server_path], check=True)
    except KeyboardInterrupt:
        print("\n[INFO] Остановка сервера...")

if __name__ == "__main__":
    main()
