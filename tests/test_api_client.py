"""Тесты для API клиента."""

import pytest
from httpx import Response
from api_client import APIClient, APIError, RateLimitError


class TestAPIClientInit:
    def test_no_token(self):
        client = APIClient(token=None)
        assert client.token is None
        assert "Authorization" not in client.headers

    def test_with_token(self):
        client = APIClient(token="test-token")
        assert client.token == "test-token"
        assert client.headers["Authorization"] == "Bearer test-token"

    def test_custom_retry_params(self):
        client = APIClient(max_retries=5, base_delay=2.0)
        assert client.max_retries == 5
        assert client.base_delay == 2.0


class TestBuildUrl:
    def test_relative_endpoint(self):
        client = APIClient(base_url="https://api.example.com/v1")
        url = client._build_url("/data/items")
        assert url == "https://api.example.com/v1/data/items"

    def test_full_url_unchanged(self):
        client = APIClient(base_url="https://api.example.com/v1")
        url = client._build_url("https://other-api.com/data")
        assert url == "https://other-api.com/data"

    def test_trailing_slashes(self):
        client = APIClient(base_url="https://api.example.com/v1/")
        url = client._build_url("/data/items")
        assert url == "https://api.example.com/v1/data/items"
