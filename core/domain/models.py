"""
Модели данных для доменной области.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class MarketData(BaseModel):
    """Базовая модель рыночных данных"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    symbol: str
    price: float
    volume: float = 0.0
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None

class Snapshot(BaseModel):
    """Снимок данных на момент времени"""
    id: Optional[int] = None
    endpoint: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any]
    checksum: str

class ChangeRecord(BaseModel):
    """Запись об изменении данных"""
    id: Optional[int] = None
    snapshot_id: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    change_type: str  # added, removed, modified
    field_path: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None

__all__ = ["MarketData", "Snapshot", "ChangeRecord"]
