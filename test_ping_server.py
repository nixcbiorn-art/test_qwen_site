"""
Простой ping-сервер для тестирования API.
Отвечает на запросы статусом и текущим временем.
"""
from fastapi import FastAPI
from datetime import datetime
import random

app = FastAPI(title="Ping Test Server")

@app.get("/ping")
async def ping():
    """Вернуть простой ping ответ"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "random_value": random.random()  # Чтобы данные менялись
    }

@app.get("/api/status")
async def status():
    """Статус сервиса"""
    return {
        "service": "ping-server",
        "running": True,
        "uptime": "active"
    }

@app.get("/api/data/{symbol}")
async def get_data(symbol: str, limit: int = 100):
    """Фейковые данные для символа"""
    import random
    data = []
    base_price = 150.0 if symbol == "AAPL" else 100.0
    for i in range(limit):
        price = base_price + random.uniform(-5, 5) + i * 0.1
        data.append({
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "price": round(price, 2),
            "volume": random.randint(1000, 10000)
        })
    return data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
