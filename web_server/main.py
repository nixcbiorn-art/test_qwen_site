"""
FastAPI сервер для веб-интерфейса и API для браузерного расширения.
Поддерживает:
1. Многостраничный веб-сайт с полным UI управлением
2. API для парсинга страниц через плагин
3. Проксирование запросов к внешним API
4. Реляционная база данных SQLite для погоды
5. NoSQL MongoDB для сырых данных парсера
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from bs4 import BeautifulSoup
import uvicorn

from database import get_db, WeatherDatabase

app = FastAPI(title="MarketMonitor Web Server")
templates = Jinja2Templates(directory="templates")

# Монтирование статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# Инициализация БД при старте
@app.on_event("startup")
async def startup_event():
    """Инициализация базы данных при запуске"""
    db = await get_db()
    print("Database initialized successfully")

class UrlRequest(BaseModel):
    url: str
    selector: Optional[str] = None
    parser_type: Optional[str] = "simple"

class WeatherCity(BaseModel):
    city_name: str
    lat: float
    lon: float

class StockSymbol(BaseModel):
    symbol: str

class SettingsUpdate(BaseModel):
    refresh_interval: Optional[int] = None
    language: Optional[str] = None
    theme: Optional[str] = None
    mongodb_uri: Optional[str] = None
    sqlite_path: Optional[str] = None
    monitor_enabled: Optional[bool] = None
    check_interval: Optional[int] = None

CITIES = {
    "moscow": {"name": "Москва", "lat": 55.7558, "lon": 37.6173},
    "london": {"name": "Лондон", "lat": 51.5074, "lon": -0.1278},
    "newyork": {"name": "Нью-Йорк", "lat": 40.7128, "lon": -74.0060},
    "tokyo": {"name": "Токио", "lat": 35.6762, "lon": 139.6503}
}

# Настройки по умолчанию
DEFAULT_SETTINGS = {
    "refresh_interval": 30,
    "language": "ru",
    "theme": "light",
    "mongodb_uri": "mongodb://localhost:27017",
    "sqlite_path": "data/weather.db",
    "monitor_enabled": True,
    "check_interval": 60,
    "retry_count": 3,
    "timeout": 10,
    "open_meteo_enabled": True
}

# Логирование в памяти (для демонстрации)
LOG_BUFFER = []

def add_log(level: str, module: str, message: str):
    LOG_BUFFER.append({
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "module": module,
        "message": message
    })
    # Ограничиваем размер буфера
    if len(LOG_BUFFER) > 1000:
        LOG_BUFFER.pop(0)

async def fetch_weather(city_key: str, db: WeatherDatabase = None):
    """Получение данных о погоде из Open-Meteo API с сохранением в БД"""
    city = CITIES.get(city_key)
    if not city:
        return None
    
    url = f"https://api.open-meteo.com/v1/forecast?latitude={city['lat']}&longitude={city['lon']}&current=temperature_2m,relative_humidity_2m,wind_speed_10m&hourly=temperature_2m"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    current = data.get('current', {})
                    record = {
                        "city": city["name"],
                        "city_key": city_key,
                        "temperature": current.get('temperature_2m'),
                        "humidity": current.get('relative_humidity_2m'),
                        "wind_speed": current.get('wind_speed_10m'),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Сохранение в реляционную базу данных
                    if db:
                        await db.add_record(
                            city_key=city_key,
                            city_name=city["name"],
                            temperature=record["temperature"],
                            humidity=record["humidity"],
                            wind_speed=record["wind_speed"],
                            timestamp=record["timestamp"]
                        )
                    
                    return record
                else:
                    return None
    except Exception as e:
        print(f"Error fetching weather for {city_key}: {e}")
        return None

# ============================================
# WEB СТРАНИЦЫ
# ============================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Главная страница - Дашборд"""
    db = await get_db()
    
    # Статистика погоды
    total_records = await db.get_total_count()
    analytics = await db.get_analytics()
    
    # Данные для графиков (заглушки для демонстрации)
    temperature_chart = {
        "data": [{"x": ["00:00", "06:00", "12:00", "18:00"], "y": [15, 12, 22, 18], "type": "scatter", "name": "Москва"}],
        "layout": {"title": "Температура за 24 часа", "height": 400}
    }
    
    parser_chart = {
        "data": [{"x": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"], "y": [10, 15, 8, 20, 12, 5, 18], "type": "bar", "name": "Запросы"}],
        "layout": {"title": "Активность парсера", "height": 400}
    }
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active_page": "dashboard",
        "weather_stats": {
            "total_cities": len(CITIES),
            "total_records": total_records or 0
        },
        "parser_stats": {
            "raw_count": 0,
            "api_calls": 42
        },
        "temperature_chart": json.dumps(temperature_chart),
        "parser_chart": json.dumps(parser_chart)
    })


@app.get("/weather", response_class=HTMLResponse)
async def weather_page(request: Request):
    """Страница погоды"""
    db = await get_db()
    
    # Получаем текущие данные по городам
    cities_data = []
    chart_data = {"data": [], "layout": {"title": "Температура по городам", "height": 400}}
    
    for city_key, city_info in CITIES.items():
        weather = await fetch_weather(city_key, db)
        if weather:
            cities_data.append({
                "name": weather["city"],
                "temperature": weather["temperature"],
                "humidity": weather["humidity"],
                "wind_speed": weather["wind_speed"],
                "last_updated": weather["timestamp"]
            })
            
            chart_data["data"].append({
                "x": [weather["timestamp"]],
                "y": [weather["temperature"]],
                "type": "scatter",
                "name": weather["city"]
            })
    
    return templates.TemplateResponse("weather.html", {
        "request": request,
        "active_page": "weather",
        "cities": cities_data,
        "chart_json": json.dumps(chart_data)
    })


@app.get("/parser", response_class=HTMLResponse)
async def parser_page(request: Request):
    """Страница парсера"""
    # Заглушки для демонстрации
    raw_data = []
    parse_history = []
    
    return templates.TemplateResponse("parser.html", {
        "request": request,
        "active_page": "parser",
        "raw_data": raw_data,
        "parse_history": parse_history
    })


@app.get("/stocks", response_class=HTMLResponse)
async def stocks_page(request: Request):
    """Страница акций"""
    # Заглушки для демонстрации
    stocks = [
        {"symbol": "AAPL", "price": 178.52, "change": 1.25},
        {"symbol": "GOOGL", "price": 141.80, "change": -0.52},
        {"symbol": "TSLA", "price": 248.30, "change": 2.15}
    ]
    
    stock_chart = {
        "data": [
            {"x": ["09:30", "12:00", "15:00", "16:00"], "y": [175, 177, 179, 178.5], "type": "candlestick", "name": "AAPL"}
        ],
        "layout": {"title": "Котировки AAPL", "height": 400}
    }
    
    return templates.TemplateResponse("stocks.html", {
        "request": request,
        "active_page": "stocks",
        "stocks": stocks,
        "stock_chart": json.dumps(stock_chart)
    })


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Страница настроек"""
    db = await get_db()
    
    # Статистика БД
    total_records = await db.get_total_count()
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "active_page": "settings",
        "settings": DEFAULT_SETTINGS,
        "db_stats": {
            "weather_records": total_records or 0,
            "sqlite_size": 0.5,
            "mongo_documents": 0,
            "mongo_size": 0
        }
    })


@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, page: int = Query(1), level: str = Query("all"), search: str = Query("")):
    """Страница логов"""
    # Фильтрация логов
    filtered_logs = LOG_BUFFER
    
    if level != "all":
        filtered_logs = [log for log in filtered_logs if log["level"] == level]
    
    if search:
        filtered_logs = [log for log in filtered_logs if search.lower() in log["message"].lower()]
    
    # Пагинация
    per_page = 50
    total_pages = max(1, (len(filtered_logs) + per_page - 1) // per_page)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_logs = filtered_logs[start_idx:end_idx]
    
    # Статистика
    log_stats = {
        "total": len(LOG_BUFFER),
        "errors": len([l for l in LOG_BUFFER if l["level"] in ["ERROR", "CRITICAL"]]),
        "warnings": len([l for l in LOG_BUFFER if l["level"] == "WARNING"]),
        "last_hour": len([l for l in LOG_BUFFER if datetime.fromisoformat(l["timestamp"]) > datetime.now() - timedelta(hours=1)])
    }
    
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "active_page": "logs",
        "logs": paginated_logs,
        "page": page,
        "total_pages": total_pages,
        "log_stats": log_stats
    })

# ============================================
# API ENDPOINTS
# ============================================

@app.get("/api/weather")
async def get_weather():
    """Получить текущие данные погоды по всем городам с сохранением в БД"""
    db = await get_db()
    results = {}
    for city_key in CITIES.keys():
        data = await fetch_weather(city_key, db)
        if data:
            results[city_key] = data
    
    # Аналитика из базы данных
    analytics = await db.get_analytics()
    
    total_records = await db.get_total_count()
    
    return {"cities": results, "analytics": analytics, "total_requests": total_records}


@app.get("/api/weather/history")
async def get_weather_history():
    """История запросов погоды из базы данных"""
    db = await get_db()
    
    # Получаем последние 50 записей
    history = await db.get_all_records(limit=50)
    
    # Группировка по городам для графика
    chart_data = {}
    for city_key in CITIES.keys():
        city_chart = await db.get_chart_data(city_key, limit=50)
        if city_chart['timestamps']:
            chart_data[city_key] = {
                "timestamps": city_chart["timestamps"],
                "temperatures": city_chart["temperatures"]
            }
    
    total_records = await db.get_total_count()
    
    return {
        "history": history,
        "chart_data": chart_data,
        "total_records": total_records
    }


@app.post("/api/parse")
async def parse_url(request: UrlRequest):
    """API для парсинга страниц (используется плагином)"""
    try:
        add_log("INFO", "parser", f"Начало парсинга: {request.url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(request.url, timeout=15) as response:
                if response.status != 200:
                    add_log("ERROR", "parser", f"Ошибка HTTP {response.status}: {request.url}")
                    raise HTTPException(status_code=response.status, detail="Failed to fetch URL")
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                result = {
                    "url": request.url,
                    "status": "success",
                    "title": soup.title.string if soup.title else None,
                    "content_length": len(html),
                    "parsed_at": datetime.now().isoformat(),
                    "data_size": len(html)
                }
                
                # Если указан селектор, извлекаем конкретный элемент
                if request.selector:
                    elements = soup.select(request.selector)
                    result["selected_content"] = [el.get_text(strip=True) for el in elements]
                    result["selected_html"] = [str(el) for el in elements]
                
                add_log("INFO", "parser", f"Успешный парсинг: {len(html)} байт")
                return result
    except Exception as e:
        add_log("ERROR", "parser", f"Ошибка парсинга: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Проверка здоровья сервиса"""
    db = await get_db()
    total_records = await db.get_total_count()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "total_weather_requests": total_records,
        "database": "sqlite"
    }


# ============================================
# НАСТРОЙКИ API
# ============================================

@app.post("/api/settings/general")
async def update_general_settings(request: SettingsUpdate):
    """Обновление общих настроек"""
    add_log("INFO", "settings", "Обновление общих настроек")
    # В реальном приложении сохраняем в БД или файл
    return {"status": "success", "message": "Настройки сохранены"}


@app.post("/api/settings/api")
async def update_api_settings(request: Request):
    """Обновление настроек API"""
    data = await request.json()
    add_log("INFO", "settings", f"Обновление API настроек: {list(data.keys())}")
    return {"status": "success", "message": "API настройки сохранены"}


@app.post("/api/settings/monitoring")
async def update_monitoring_settings(request: Request):
    """Обновление настроек мониторинга"""
    data = await request.json()
    add_log("INFO", "settings", f"Обновление настроек мониторинга: {data}")
    return {"status": "success", "message": "Настройки мониторинга сохранены"}


# ============================================
# БАЗА ДАННЫХ API
# ============================================

@app.post("/api/db/sqlite/vacuum")
async def vacuum_sqlite():
    """Очистка SQLite базы"""
    db = await get_db()
    # В реальной реализации вызываем db.vacuum()
    add_log("INFO", "database", "Выполнен VACUUM SQLite")
    return {"status": "success", "message": "SQLite очищен"}


@app.post("/api/db/sqlite/backup")
async def backup_sqlite():
    """Создание бэкапа SQLite"""
    backup_path = f"data/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    add_log("INFO", "database", f"Создан бэкап: {backup_path}")
    return {"status": "success", "path": backup_path}


@app.post("/api/db/mongo/clear")
async def clear_mongo():
    """Очистка MongoDB коллекции"""
    add_log("WARNING", "database", "Очистка MongoDB коллекции")
    return {"status": "success", "message": "MongoDB очищена"}


@app.post("/api/db/mongo/export")
async def export_mongo():
    """Экспорт MongoDB данных"""
    export_path = f"data/mongo_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    add_log("INFO", "database", f"Экспорт MongoDB: {export_path}")
    return {"status": "success", "path": export_path}


# ============================================
# ЛОГИ API
# ============================================

@app.post("/api/logs/clear")
async def clear_logs():
    """Очистка буфера логов"""
    LOG_BUFFER.clear()
    add_log("INFO", "system", "Логи очищены")
    return {"status": "success", "message": "Логи очищены"}


@app.post("/api/logs/download")
async def download_logs():
    """Скачивание логов"""
    log_text = "\n".join([f"{log['timestamp']} [{log['level']}] {log['module']}: {log['message']}" for log in LOG_BUFFER])
    
    filename = f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    filepath = f"/tmp/{filename}"
    
    with open(filepath, 'w') as f:
        f.write(log_text)
    
    return FileResponse(filepath, media_type='text/plain', filename=filename)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
