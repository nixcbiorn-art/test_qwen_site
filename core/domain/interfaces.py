"""
Интерфейсы для сервисов ядра.
Позволяют менять реализации без изменения бизнес-логики.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
from .models import Snapshot, ChangeRecord, MarketData

class IDataSource(ABC):
    """Интерфейс источника данных (API, файл, etc.)"""
    
    @abstractmethod
    async def fetch(self, url: str, **kwargs) -> Dict[str, Any]:
        """Получить данные из источника"""
        pass
    
    @abstractmethod
    async def fetch_market_data(self, symbol: str) -> MarketData:
        """Получить рыночные данные по символу"""
        pass

class IStorage(ABC):
    """Интерфейс хранилища данных"""
    
    @abstractmethod
    async def save_snapshot(self, snapshot: Snapshot) -> int:
        """Сохранить снимок данных, вернуть ID"""
        pass
    
    @abstractmethod
    async def get_latest_snapshots(self, endpoint: str, limit: int = 100) -> List[Snapshot]:
        """Получить последние снимки"""
        pass
    
    @abstractmethod
    async def save_change(self, change: ChangeRecord) -> int:
        """Сохранить запись об изменении"""
        pass

class INotifier(ABC):
    """Интерфейс системы уведомлений"""
    
    @abstractmethod
    async def send(self, message: str, context: Dict[str, Any]) -> bool:
        """Отправить уведомление"""
        pass

__all__ = ["IDataSource", "IStorage", "INotifier"]
