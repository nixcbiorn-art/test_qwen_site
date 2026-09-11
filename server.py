import asyncio
import json
import time
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
import aiohttp
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Хранилище данных
weather_data = {
    "cities": [],
    "history": [],
    "last_update": None
}

CITIES = {
    "Moscow": {"lat": 55.7558, "lon": 37.6173},
    "London": {"lat": 51.5074, "lon": -0.1278},
    "New York": {"lat": 40.7128, "lon": -74.0060},
    "Tokyo": {"lat": 35.6762, "lon": 139.6503}
}

async def fetch_weather(session, city, coords):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&current_weather=true"
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    "city": city,
                    "temp": data["current_weather"]["temperature"],
                    "wind": data["current_weather"]["windspeed"],
                    "time": data["current_weather"]["time"]
                }
    except Exception as e:
        print(f"Error fetching {city}: {e}")
    return None

async def collect_weather():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_weather(session, city, coords) for city, coords in CITIES.items()]
        results = await asyncio.gather(*tasks)
        valid_results = [r for r in results if r is not None]
        
        weather_data["cities"] = valid_results
        weather_data["history"].append({
            "timestamp": datetime.now().isoformat(),
            "data": valid_results
        })
        weather_data["last_update"] = datetime.now().strftime("%H:%M:%S")
        
        # Ограничим историю последними 100 записями
        if len(weather_data["history"]) > 100:
            weather_data["history"] = weather_data["history"][-100:]

@app.on_event("startup")
async def startup_event():
    # Запускаем фоновый сборщик данных
    asyncio.create_task(background_collector())

async def background_collector():
    while True:
        await collect_weather()
        await asyncio.sleep(30)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", context={"request": request, "data": weather_data})

@app.get("/api/weather")
async def get_weather():
    return JSONResponse(content=weather_data)

@app.get("/api/analytics")
async def get_analytics():
    if not weather_data["history"]:
        return {"error": "No data yet"}
    
    # Простая аналитика
    history = weather_data["history"]
    analytics = {}
    
    for city in CITIES.keys():
        temps = [item["data"][0]["temp"] for item in history if any(c["city"] == city for c in item["data"])]
        if temps:
            analytics[city] = {
                "avg_temp": sum(temps) / len(temps),
                "min_temp": min(temps),
                "max_temp": max(temps),
                "samples": len(temps)
            }
    
    return analytics

@app.post("/api/scrape")
async def receive_scraped_data(request: Request):
    """Endpoint для получения данных от браузерного плагина"""
    try:
        data = await request.json()
        filename = f"scraped_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Scraped data saved to {filename}")
        return {"status": "success", "file": filename}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
