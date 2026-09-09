"""
Сервис мониторинга.
Управляет циклом проверки эндпоинтов и детектированием изменений.
"""
import asyncio
from datetime import datetime
from typing import Optional, List

from ..config import AppConfig
from .storage import StorageService
from .native_engine import NativeEngine
from ..domain.models import Snapshot, ChangeRecord

class MonitorService:
    """Сервис мониторинга изменений данных"""
    
    def __init__(self, config: AppConfig, storage: StorageService, native_engine: NativeEngine):
        self.config = config
        self.storage = storage
        self.native_engine = native_engine
        self.is_running = False
        self.last_check_time: Optional[datetime] = None
    
    async def start(self):
        """Запустить мониторинг"""
        self.is_running = True
    
    async def stop(self):
        """Остановить мониторинг"""
        self.is_running = False
    
    async def run_cycle(self):
        """Выполнить один цикл проверки всех эндпоинтов"""
        if not self.is_running:
            return
        
        self.last_check_time = datetime.utcnow()
        
        for endpoint in self.config.endpoints:
            try:
                await self._check_endpoint(endpoint)
            except Exception as e:
                print(f"Error checking endpoint {endpoint.name}: {e}")
        
        await asyncio.sleep(self.config.check_interval)
    
    async def _check_endpoint(self, endpoint):
        """Проверить один эндпоинт на изменения"""
        # Здесь должна быть логика запроса к API
        # Для примера создаём фиктивный снапшот
        
        snapshot = Snapshot(
            endpoint=endpoint.name,
            timestamp=datetime.utcnow(),
            data={"status": "ok"},  # Данные от API
            checksum="abc123"
        )
        
        # Сохраняем снапшот
        snapshot_id = await self.storage.save_snapshot(snapshot)
        
        # Проверяем на изменения (сравниваем с предыдущим)
        prev_snapshots = await self.storage.get_latest_snapshots(endpoint.name, limit=2)
        if len(prev_snapshots) > 1:
            changes = self._detect_changes(prev_snapshots[0], prev_snapshots[1])
            for change in changes:
                change.snapshot_id = snapshot_id
                await self.storage.save_change(change)
    
    def _detect_changes(self, current: Snapshot, previous: Snapshot) -> List[ChangeRecord]:
        """Детектировать изменения между снапшотами"""
        changes = []
        
        # Простая реализация - сравнение checksum
        if current.checksum != previous.checksum:
            changes.append(ChangeRecord(
                change_type="modified",
                field_path="data",
                old_value=previous.data,
                new_value=current.data
            ))
        
        return changes

__all__ = ["MonitorService"]
