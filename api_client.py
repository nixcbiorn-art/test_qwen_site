"""HTTP клиент для работы с API."""

import httpx
from typing import Optional, Dict, Any
from config import API_BASE_URL


class APIClient:
    def __init__(self, token: Optional[str] = None):
        """
        token=None означает работу без авторизации (открытый/публичный API):
        заголовок Authorization просто не добавляется.
        """
        self.token = token
        self.base_url = API_BASE_URL
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

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

    def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
