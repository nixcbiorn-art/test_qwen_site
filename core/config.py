"""
Конфигурация приложения через Pydantic Settings.
Загружает из .env, settings.json или дефолтов.
"""
import os
from typing import List, Optional
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings

class EndpointConfig(BaseSettings):
    name: str
    url: str
    method: str = "GET"
    auth_type: str = "none"  # none, bearer, api_key
    headers: dict = {}
    mapping: dict = {}

class NotificationConfig(BaseSettings):
    email_enabled: bool = False
    email_smtp: str = ""
    email_from: str = ""
    email_to: str = ""
    webhook_enabled: bool = False
    webhook_url: str = ""
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

class AppConfig(BaseSettings):
    api_base_url: Optional[str] = None
    api_timeout: int = 30
    retry_count: int = 3
    check_interval: int = 60
    
    db_path: str = "data/changes.db"
    
    endpoints: List[EndpointConfig] = []
    notifications: NotificationConfig = NotificationConfig()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def get_config() -> AppConfig:
    """Получить конфигурацию приложения"""
    return AppConfig()

__all__ = ["get_config", "AppConfig", "EndpointConfig", "NotificationConfig"]
