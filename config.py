"""
Конфигурация парсера.

Значения ниже — дефолты. Если рядом лежит data/settings.json (его пишет
вкладка "Настройки" в WPF-приложении), значения оттуда переопределяют
дефолты. Ключи в JSON — snake_case, совпадают с именами полей ниже.

Приоритет источников конфигурации:
1. Переменные окружения (.env файл или системные переменные)
2. data/settings.json (UI настройки)
3. Значения по умолчанию в этом файле
"""

import json
import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import structlog

logger = structlog.get_logger()

# Загружаем переменные из .env файла (если есть)
load_dotenv()


class EndpointConfig(BaseModel):
    """Конфигурация одного API эндпоинта."""
    path: str
    token: str = ""
    auth_mode: str = "login"
    paginate: bool = False
    items_path: str = ""
    mapping: Dict[str, str] = Field(default_factory=dict)
    max_pages: int = 50
    
    @field_validator('auth_mode')
    @classmethod
    def validate_auth_mode(cls, v: str) -> str:
        if v not in ("none", "token", "login"):
            return "login"
        return v
    
    @field_validator('max_pages')
    @classmethod
    def validate_max_pages(cls, v: int) -> int:
        return max(1, min(v, 1000))


class ParserConfig(BaseSettings):
    """Основная конфигурация парсера с валидацией через Pydantic."""
    
    model_config = SettingsConfigDict(
        env_prefix="PARSER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Базовые URL
    site_url: HttpUrl = Field(default="https://example.com", description="Базовый URL сайта")
    api_base_url: HttpUrl = Field(default="https://api.example.com/v1", description="Базовый URL API")
    
    # Авторизация
    username: str = Field(default="", description="Имя пользователя")
    password: str = Field(default="", description="Пароль")
    
    # Настройки мониторинга
    check_interval_seconds: int = Field(default=300, ge=10, le=86400, description="Интервал проверки в секундах")
    headless_browser: bool = Field(default=True, description="Режим браузера без GUI")
    
    # Браузер
    browser_type: str = Field(default="chromium", description="Тип браузера (chromium, firefox, webkit)")
    
    # Настройки краулера
    crawl_max_pages: int = Field(default=200, ge=1, le=10000, description="Максимум страниц для краулинга")
    crawl_delay_seconds: float = Field(default=1.0, ge=0.1, le=60.0, description="Задержка между запросами краулера")
    crawl_include_query: bool = Field(default=False, description="Включать query параметры в URL при краулинге")
    
    # Эндпоинты API
    endpoints: List[EndpointConfig] = Field(default_factory=lambda: [
        EndpointConfig(path="/data/items"),
        EndpointConfig(path="/data/status"),
    ])
    
    @property
    def login_url(self) -> str:
        return f"{self.site_url}/login"
    
    @property
    def data_dir(self) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "data")
    
    @property
    def db_path(self) -> str:
        return os.path.join(self.data_dir, "changes.db")
    
    @property
    def settings_path(self) -> str:
        return os.path.join(self.data_dir, "settings.json")
    
    @property
    def crawl_output_dir(self) -> str:
        return os.path.join(self.data_dir, "pages")
    
    @field_validator('site_url', 'api_base_url', mode='before')
    @classmethod
    def coerce_url(cls, v: Any) -> str:
        if isinstance(v, str):
            return v
        return str(v)


def _load_settings_json(config: ParserConfig) -> Dict[str, Any]:
    """Загрузить настройки из JSON файла если он существует."""
    if not os.path.exists(config.settings_path):
        logger.info("config_settings_file_not_found", path=config.settings_path)
        return {}
    
    try:
        with open(config.settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("config_settings_loaded", path=config.settings_path)
        return data
    except (OSError, json.JSONDecodeError) as e:
        logger.error("config_settings_load_error", path=config.settings_path, error=str(e))
        return {}


def _merge_settings(settings_data: Dict[str, Any], env_overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Объединить настройки: ENV имеет приоритет над JSON.
    Возвращает финальный словарь для инициализации ParserConfig.
    """
    merged = {}
    
    # Маппинг ключей JSON на поля Pydantic
    key_mapping = {
        "site_url": "site_url",
        "api_base_url": "api_base_url",
        "username": "username",
        "password": "password",
        "check_interval_seconds": "check_interval_seconds",
        "headless_browser": "headless_browser",
        "browser_type": "browser_type",
        "crawl_max_pages": "crawl_max_pages",
        "crawl_delay_seconds": "crawl_delay_seconds",
        "crawl_include_query": "crawl_include_query",
    }
    
    for json_key, pydantic_key in key_mapping.items():
        # ENV уже загружен pydantic-settings автоматически, используем только JSON
        if json_key in settings_data and settings_data[json_key]:
            merged[pydantic_key] = settings_data[json_key]
            logger.debug("config_override_applied", key=pydantic_key, source="settings.json")
    
    # Обработка endpoints
    if "endpoints" in settings_data and settings_data["endpoints"]:
        parsed_endpoints = []
        for e in settings_data["endpoints"]:
            path = e.get("path", "")
            if not path:
                continue
            
            token = e.get("token", "")
            auth_mode = e.get("auth_mode")
            
            if auth_mode not in ("none", "token", "login"):
                auth_mode = "token" if token else "login"
            
            mapping = e.get("mapping")
            if not isinstance(mapping, dict):
                mapping = {}
            
            try:
                max_pages = int(e.get("max_pages", 50))
            except (TypeError, ValueError):
                max_pages = 50
            
            parsed_endpoints.append({
                "path": path,
                "token": token,
                "auth_mode": auth_mode,
                "paginate": bool(e.get("paginate", False)),
                "items_path": e.get("items_path") or "",
                "mapping": mapping,
                "max_pages": max_pages,
            })
        
        merged["endpoints"] = parsed_endpoints
        logger.info("config_endpoints_loaded", count=len(parsed_endpoints))
    
    return merged


def get_config() -> ParserConfig:
    """Получить конфигурацию с учётом всех источников."""
    logger.info("config_loading_started")
    
    settings_data = _load_settings_json(ParserConfig())
    merged = _merge_settings(settings_data, {})
    
    config = ParserConfig(**merged)
    logger.info("config_loading_completed")
    
    return config


# Глобальный экземпляр конфигурации
config = get_config()

# Экспортируем свойства для обратной совместимости
SITE_URL = str(config.site_url)
API_BASE_URL = str(config.api_base_url)
LOGIN_URL = config.login_url
USERNAME = config.username
PASSWORD = config.password
CHECK_INTERVAL_SECONDS = config.check_interval_seconds
HEADLESS_BROWSER = config.headless_browser
BROWSER_TYPE = config.browser_type
CRAWL_MAX_PAGES = config.crawl_max_pages
CRAWL_DELAY_SECONDS = config.crawl_delay_seconds
CRAWL_INCLUDE_QUERY = config.crawl_include_query
DATA_DIR = config.data_dir
DB_PATH = config.db_path
CRAWL_OUTPUT_DIR = config.crawl_output_dir
SETTINGS_PATH = config.settings_path
API_ENDPOINTS = [e.model_dump() for e in config.endpoints]
