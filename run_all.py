#!/usr/bin/env python3
"""
Universal Launcher: Site + Analytics + Plugin Backend
Запускает веб-сервер с сайтом, API и бэкендом для браузерного плагина
"""

import subprocess
import sys
import os
import time

def check_dependencies():
    """Проверка и установка зависимостей из requirements.txt"""
    print("Обновление зависимостей из requirements.txt...")
    print("=" * 60)
    
    # Явная установка всех зависимостей из requirements.txt
    subprocess.check_call([
        sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '--upgrade'
    ])
    
    print("\nЗависимости обновлены.")
    print("=" * 60)

def run_server():
    """Запуск веб-сервера"""
    print("\n[1/1] Запуск веб-сервера (Сайт + API + Plugin Backend)...")
    print("=" * 60)
    print("Сервер запущен на: http://localhost:8000")
    print("Сайт: http://localhost:8000")
    print("API Weather: http://localhost:8000/api/weather")
    print("API Analytics: http://localhost:8000/api/analytics")
    print("API Scrape: http://localhost:8000/api/scrape (POST)")
    print("=" * 60)
    print("\nДля установки браузерного плагина:")
    print("1. Откройте Chrome/Edge")
    print("2. Перейдите на chrome://extensions/")
    print("3. Включите 'Режим разработчика'")
    print("4. Нажмите 'Загрузить распакованное расширение'")
    print("5. Выберите папку:", os.path.abspath('extension'))
    print("\nНажмите Ctrl+C для остановки сервера\n")
    
    # Запускаем сервер напрямую, чтобы избежать проблем с кодировкой
    import uvicorn
    from server import app
    uvicorn.run(app, host="0.0.0.0", port=8000)

def main():
    try:
        check_dependencies()
        run_server()
    except KeyboardInterrupt:
        print("\n\nОстановка сервера...")
        print("До свидания!")
    except Exception as e:
        print(f"\nОшибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
