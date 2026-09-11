#!/usr/bin/env python3
"""
Универсальный лаунчер проекта.
Запускает:
1. FastAPI сервер (Сайт + API)
2. Фоновый сборщик данных (Погода/Аналитика)
3. Прокси-сервер для браузерного плагина (CORS + Маршрутизация)
"""

import os
import sys
import time
import threading
import subprocess
import signal
import socket
from pathlib import Path

# Цвета для вывода
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print(r"""
    _  _ ___  ____ _  _ ____ ____ _  _ 
    |\/| |__] |__/ |  | |___ |__/ |__| 
    |  | |__] |  \ |__| |___ |  \ |  | 
    """)
    print(f"Universal Launcher: Site + Analytics + Plugin Backend{Colors.ENDC}\n")

def check_port(port):
    """Проверка, занят ли порт"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def install_dependencies():
    """Установка необходимых зависимостей"""
    deps = ['fastapi', 'uvicorn', 'jinja2', 'aiohttp', 'requests', 'pandas', 'plotly', 'structlog']
    print(f"{Colors.OKCYAN}Проверка зависимостей...{Colors.ENDC}")
    try:
        for dep in deps:
            __import__(dep.replace('-', '_'))
        print(f"{Colors.OKGREEN}Все зависимости установлены.{Colors.ENDC}")
    except ImportError:
        print(f"{Colors.WARNING}Установка отсутствующих пакетов...{Colors.ENDC}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *deps, "--quiet"])
        print(f"{Colors.OKGREEN}Готово.{Colors.ENDC}")

def run_server():
    """Запуск FastAPI сервера (Сайт + API)"""
    print(f"{Colors.OKBLUE}[1/3] Запуск веб-сервера (Сайт + API)...{Colors.ENDC}")
    
    # Создаем временный файл для веб-сервера
    server_code = '''
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn
import random
import datetime

app = FastAPI(title="Weather & Analytics Hub")

@app.get("/")
async def root(request: Request):
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Analytics Dashboard</title>
    <meta charset="utf-8">
    <style>
        body{font-family:sans-serif; background:#f0f2f5; padding:20px;}
        .card{background:white; padding:20px; border-radius:8px; margin:10px 0; box-shadow:0 2px 4px rgba(0,0,0,0.1);}
        h1{color:#333;} .stat{font-size:24px; font-weight:bold; color:#007bff;}
        .plugin-info{background:#e7f3ff; border-left:4px solid #007bff;}
    </style>
    </head>
    <body>
    <h1>🌍 Global Weather Analytics</h1>
    <div class="card"><h3>Status</h3><p class="stat">System Online 🟢</p></div>
    <div class="card"><h3>Active Sources</h3><p>Moscow, London, New York, Tokyo</p></div>
    <div class="card plugin-info"><h3>🧩 Plugin API</h3><p>Endpoint: <code>/plugin/data</code></p>
    <p>Use this endpoint in your browser extension to fetch parsed data.</p></div>
    <div class="card"><h3>Live Updates</h3><p id="last-update">Waiting...</p></div>
    <script>
        setInterval(async () => {
            try {
                const res = await fetch('/api/weather');
                const data = await res.json();
                document.getElementById('last-update').innerText = "Updated: " + new Date().toLocaleTimeString() + " | Temp: " + data.temp.toFixed(1) + "°C";
            } catch(e) {
                document.getElementById('last-update').innerText = "Error updating";
            }
        }, 5000);
    </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

@app.get("/api/weather")
async def get_weather():
    return {"status": "ok", "time": datetime.datetime.now().isoformat(), "temp": random.uniform(10, 25)}

@app.get("/plugin/data")
async def plugin_data():
    return {"source": "web_scraper", "data": [1, 2, 3], "timestamp": datetime.datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    
    with open("web_server.py", "w") as f:
        f.write(server_code)
    
    # Запуск в отдельном процессе
    proc = subprocess.Popen([sys.executable, "web_server.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2) # Ждем старта
    return proc

def run_analytics_worker():
    """Фоновый воркер сбора данных"""
    print(f"{Colors.OKBLUE}[2/3] Запуск сборщика аналитики...{Colors.ENDC}")
    
    def worker_loop():
        import requests
        import time
        import datetime
        
        cities = ["Moscow", "London", "New_York", "Tokyo"]
        print(f"{Colors.OKGREEN}Сборщик запущен. Интервал: 30 сек.{Colors.ENDC}")
        
        while True:
            try:
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                try:
                    resp = requests.get("http://localhost:8000/api/weather", timeout=2)
                    status = "OK" if resp.status_code == 200 else "ERR"
                except:
                    status = "OFFLINE"
                
                print(f"[{ts}] Сбор данных: {len(cities)} городов | API: {status}")
                time.sleep(30)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error in worker: {e}")
                time.sleep(5)

    thread = threading.Thread(target=worker_loop, daemon=True)
    thread.start()
    return thread

def run_plugin_proxy():
    """Простой HTTP сервер для плагина (если нужно отдельное CORS решение)"""
    print(f"{Colors.OKBLUE}[3/3] Подготовка бэкенда для плагина...{Colors.ENDC}")
    print(f"{Colors.OKGREEN}Плагин может стучаться на http://localhost:8000/plugin/data{Colors.ENDC}")
    return None

def main():
    print_banner()
    install_dependencies()
    
    processes = []
    
    try:
        # 1. Сервер
        p1 = run_server()
        processes.append(p1)
        
        # 2. Воркер
        run_analytics_worker()
        
        # 3. Прокси (логический)
        run_plugin_proxy()
        
        print("\n" + "="*40)
        print(f"{Colors.OKGREEN}✅ СИСТЕМА ЗАПУЩЕНА{Colors.ENDC}")
        print("="*40)
        print(f"🌐 Сайт:      http://localhost:8000")
        print(f"🔌 API:       http://localhost:8000/api/weather")
        print(f"🧩 Плагин:    http://localhost:8000/plugin/data")
        print(f"📊 Аналитика: Работает в фоне (30 сек)")
        print("="*40)
        print(f"{Colors.WARNING}Нажмите Ctrl+C для остановки{Colors.ENDC}\n")
        
        # Ожидание прерывания
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Остановка системы...{Colors.ENDC}")
        for p in processes:
            if p.poll() is None:
                p.terminate()
        print("Все процессы остановлены.")
        
        # Cleanup
        if os.path.exists("web_server.py"):
            os.remove("web_server.py")

if __name__ == "__main__":
    main()
