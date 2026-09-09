"""
FastAPI сервер для MarketMonitor.
Предоставляет REST API и WebSocket для веб-интерфейса.
Интегрирован с core и native_engine.
"""
import asyncio
import json
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Импорт ядра
import sys
sys.path.insert(0, '/workspace')
from core.config import get_config
from core.services.monitor import MonitorService
from core.services.storage import StorageService
from core.services.native_engine import NativeEngine

# Глобальные состояния
monitor_service: Optional[MonitorService] = None
storage_service: Optional[StorageService] = None
native_engine: Optional[NativeEngine] = None
active_connections: List[WebSocket] = []

class MonitorStatus(BaseModel):
    is_running: bool
    endpoints_count: int
    last_check: Optional[str] = None

class DataPoint(BaseModel):
    timestamp: str
    symbol: str
    price: float
    volume: float

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация сервисов при старте"""
    global monitor_service, storage_service, native_engine
    
    config = get_config()
    storage_service = StorageService(config)
    native_engine = NativeEngine()
    monitor_service = MonitorService(config, storage_service, native_engine)
    
    # Запуск фонового мониторинга если нужно
    asyncio.create_task(run_background_monitor())
    
    yield
    
    # Очистка при shutdown
    if monitor_service:
        await monitor_service.stop()

async def run_background_monitor():
    """Фоновая задача мониторинга"""
    while True:
        try:
            if monitor_service and monitor_service.is_running:
                await monitor_service.run_cycle()
            await asyncio.sleep(10)  # Интервал проверки
        except Exception as e:
            print(f"Error in background monitor: {e}")
            await asyncio.sleep(5)

app = FastAPI(title="MarketMonitor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Для разработки. В продакшене ограничить!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/status", response_model=MonitorStatus)
async def get_status():
    """Получить статус системы"""
    if not monitor_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return MonitorStatus(
        is_running=monitor_service.is_running,
        endpoints_count=len(monitor_service.config.endpoints),
        last_check=monitor_service.last_check_time
    )

@app.get("/api/data/{symbol}", response_model=List[DataPoint])
async def get_data(symbol: str, limit: int = 100):
    """Получить исторические данные по символу"""
    if not storage_service:
        raise HTTPException(status_code=503, detail="Storage not initialized")
    
    data = await storage_service.get_latest_snapshots(symbol, limit=limit)
    return [
        DataPoint(
            timestamp=str(d.timestamp),
            symbol=d.symbol,
            price=d.price,
            volume=d.volume
        )
        for d in data
    ]

@app.post("/api/monitor/start")
async def start_monitoring():
    """Запустить мониторинг"""
    if not monitor_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    await monitor_service.start()
    return {"status": "started"}

@app.post("/api/monitor/stop")
async def stop_monitoring():
    """Остановить мониторинг"""
    if not monitor_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    await monitor_service.stop()
    return {"status": "stopped"}

@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket для real-time обновлений"""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Ждем сообщения от клиента (например, подписку на символ)
            data = await websocket.receive_text()
            # Можно обработать подписку
            await websocket.send_json({"type": "subscribed", "data": data})
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def broadcast_update(data: dict):
    """Отправить обновление всем подключенным клиентам"""
    if active_connections:
        message = json.dumps(data)
        await asyncio.gather(
            *[conn.send_text(message) for conn in active_connections],
            return_exceptions=True
        )

# Экспорт функции для использования в мониторе
__all__ = ["app", "broadcast_update"]
