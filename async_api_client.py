"""Асинхронный HTTP клиент для работы с API на основе aiohttp."""

import asyncio
import structlog
from typing import Optional, Dict, Any
from config import API_BASE_URL

import aiohttp

logger = structlog.get_logger()


class AsyncAPIError(Exception):
    """Базовое исключение для ошибок асинхронного API."""
    pass


class AsyncRateLimitError(AsyncAPIError):
    """Превышен лимит запросов в асинхронном режиме."""
    pass


class AsyncAPIClient:
    def __init__(self, token: Optional[str] = None, max_retries: int = 3, base_delay: float = 1.0, base_url: Optional[str] = None):
        """
        Асинхронный клиент для работы с API.
        
        token=None означает работу без авторизации (открытый/публичный API):
        заголовок Authorization просто не добавляется.
        
        Args:
            token: Токен авторизации (None для публичных API)
            max_retries: Максимальное количество попыток при ошибке
            base_delay: Базовая задержка между попытками (секунды)
            base_url: Базовый URL API (по умолчанию берётся из config.API_BASE_URL)
        """
        self.token = token
        self.base_url = base_url if base_url is not None else API_BASE_URL
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def _build_url(self, endpoint: str) -> str:
        """
        Если endpoint уже полный URL (http:// или https://) — используем
        его как есть, без склейки с API_BASE_URL. Это нужно для публичных
        источников на других доменах (например, "https://fsk.ru/api/v3/flats").
        Иначе endpoint считается путём относительно API_BASE_URL, как раньше.
        """
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        return f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    async def _request_with_retry(self, method: str, url: str, session: aiohttp.ClientSession, **kwargs) -> aiohttp.ClientResponse:
        """Выполняет асинхронный HTTP-запрос с экспоненциальной задержкой при ошибках."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with session.request(method, url, headers=self.headers, **kwargs) as response:
                    # Обработка rate limit
                    if response.status == 429:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            delay = float(retry_after)
                        else:
                            delay = self.base_delay * (2 ** attempt)
                        
                        if attempt < self.max_retries:
                            logger.warning("async_rate_limit_exceeded", delay=delay, attempt=attempt + 1)
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise AsyncRateLimitError(f"Превышен лимит запросов после {self.max_retries} попыток")
                    
                    response.raise_for_status()
                    # Возвращаем копию ответа, так как оригинал закроется с контекстным менеджером
                    return await response.json()
                    
            except aiohttp.ClientResponseError as e:
                last_exception = e
                if e.status >= 500 and attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning("async_server_error", status_code=e.status, attempt=attempt + 1, max_retries=self.max_retries, delay=delay)
                    await asyncio.sleep(delay)
                else:
                    break
            except aiohttp.ClientError as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning("async_network_error", error=str(e), attempt=attempt + 1, max_retries=self.max_retries, delay=delay)
                    await asyncio.sleep(delay)
                else:
                    break
        
        raise AsyncAPIError(f"Не удалось выполнить запрос после {self.max_retries} попыток: {last_exception}")

    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Асинхронный GET запрос."""
        url = self._build_url(endpoint)
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            return await self._request_with_retry("GET", url, session, params=params)

    async def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Асинхронный POST запрос."""
        url = self._build_url(endpoint)
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            return await self._request_with_retry("POST", url, session, json=data)
