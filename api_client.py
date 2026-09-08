"""HTTP клиент для работы с API с поддержкой retry."""

import httpx
import time
import logging
from typing import Optional, Dict, Any
from config import API_BASE_URL

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Базовое исключение для ошибок API."""
    pass


class RateLimitError(APIError):
    """Превышен лимит запросов."""
    pass


class APIClient:
    def __init__(self, token: Optional[str] = None, max_retries: int = 3, base_delay: float = 1.0):
        """
        token=None означает работу без авторизации (открытый/публичный API):
        заголовок Authorization просто не добавляется.
        
        Args:
            token: Токен авторизации (None для публичных API)
            max_retries: Максимальное количество попыток при ошибке
            base_delay: Базовая задержка между попытками (секунды)
        """
        self.token = token
        self.base_url = API_BASE_URL
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

    def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Выполняет HTTP-запрос с экспоненциальной задержкой при ошибках."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.request(method, url, headers=self.headers, **kwargs)
                    
                    # Обработка rate limit
                    if response.status_code == 429:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            delay = float(retry_after)
                        else:
                            delay = self.base_delay * (2 ** attempt)
                        
                        if attempt < self.max_retries:
                            logger.warning(f"Rate limit. Ожидание {delay:.1f}с...")
                            time.sleep(delay)
                            continue
                        else:
                            raise RateLimitError(f"Превышен лимит запросов после {self.max_retries} попыток")
                    
                    response.raise_for_status()
                    return response
                    
            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code >= 500 and attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Ошибка сервера {e.response.status_code}. Попытка {attempt + 1}/{self.max_retries}. Ожидание {delay:.1f}с...")
                    time.sleep(delay)
                else:
                    break
            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Ошибка сети: {e}. Попытка {attempt + 1}/{self.max_retries}. Ожидание {delay:.1f}с...")
                    time.sleep(delay)
                else:
                    break
        
        raise APIError(f"Не удалось выполнить запрос после {self.max_retries} попыток: {last_exception}")

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        response = self._request_with_retry("GET", url, params=params)
        return response.json()

    def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        response = self._request_with_retry("POST", url, json=data)
        return response.json()
