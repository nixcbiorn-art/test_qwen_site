"""
FastAPI сервер для веб-интерфейса и API для браузерного расширения.
Поддерживает:
1. Веб-сайт с аналитикой погоды
2. API для парсинга страниц через плагин
3. Проксирование запросов к внешним API
"""

import asyncio
import aiohttp
import pandas as pd
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from bs4 import BeautifulSoup
import uvicorn

app = FastAPI(title="Weather & Parser API")
templates = Jinja2Templates(directory="templates")

# Хранилище данных о погоде
weather_data_store = []

class UrlRequest(BaseModel):
    url: str
    selector: str = None

class WeatherCity(BaseModel):
    city: str
    lat: float
    lon: float

CITIES = {
    "moscow": {"name": "Москва", "lat": 55.7558, "lon": 37.6173},
    "london": {"name": "Лондон", "lat": 51.5074, "lon": -0.1278},
    "newyork": {"name": "Нью-Йорк", "lat": 40.7128, "lon": -74.0060},
    "tokyo": {"name": "Токио", "lat": 35.6762, "lon": 139.6503}
}

async def fetch_weather(city_key: str):
    """Получение данных о погоде из Open-Meteo API"""
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
                    weather_data_store.append(record)
                    return record
                else:
                    return None
    except Exception as e:
        print(f"Error fetching weather for {city_key}: {e}")
        return None

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Главная страница сайта"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/weather")
async def get_weather():
    """Получить текущие данные погоды по всем городам"""
    results = {}
    for city_key in CITIES.keys():
        data = await fetch_weather(city_key)
        if data:
            results[city_key] = data
    
    # Аналитика
    analytics = {}
    if results:
        temps = [r["temperature"] for r in results.values() if r["temperature"] is not None]
        humidities = [r["humidity"] for r in results.values() if r["humidity"] is not None]
        winds = [r["wind_speed"] for r in results.values() if r["wind_speed"] is not None]
        
        analytics = {
            "avg_temperature": round(sum(temps) / len(temps), 1) if temps else None,
            "max_temperature": max(temps) if temps else None,
            "min_temperature": min(temps) if temps else None,
            "avg_humidity": round(sum(humidities) / len(humidities), 1) if humidities else None,
            "max_wind_speed": max(winds) if winds else None,
            "hottest_city": max(results.values(), key=lambda x: x["temperature"] or 0)["city"] if temps else None,
            "coldest_city": min(results.values(), key=lambda x: x["temperature"] or 100)["city"] if temps else None,
            "windiest_city": max(results.values(), key=lambda x: x["wind_speed"] or 0)["city"] if winds else None
        }
    
    return {"cities": results, "analytics": analytics, "total_requests": len(weather_data_store)}

@app.get("/api/weather/history")
async def get_weather_history():
    """История запросов погоды"""
    df = pd.DataFrame(weather_data_store)
    if df.empty:
        return {"history": [], "chart_data": None}
    
    # Группировка по городам для графика
    chart_data = {}
    for city_key in CITIES.keys():
        city_data = df[df["city_key"] == city_key]
        if not city_data.empty:
            chart_data[city_key] = {
                "timestamps": city_data["timestamp"].tolist(),
                "temperatures": city_data["temperature"].tolist()
            }
    
    return {
        "history": weather_data_store[-50:],  # Последние 50 записей
        "chart_data": chart_data,
        "total_records": len(weather_data_store)
    }

@app.post("/api/parse")
async def parse_url(request: UrlRequest):
    """API для парсинга страниц (используется плагином)"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(request.url, timeout=15) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail="Failed to fetch URL")
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                result = {
                    "url": request.url,
                    "status": "success",
                    "title": soup.title.string if soup.title else None,
                    "content_length": len(html),
                    "parsed_at": datetime.now().isoformat()
                }
                
                # Если указан селектор, извлекаем конкретный элемент
                if request.selector:
                    elements = soup.select(request.selector)
                    result["selected_content"] = [el.get_text(strip=True) for el in elements]
                    result["selected_html"] = [str(el) for el in elements]
                
                return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "total_weather_requests": len(weather_data_store)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
