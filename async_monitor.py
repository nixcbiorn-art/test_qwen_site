"""Асинхронный модуль мониторинга API."""

import asyncio
import json
import structlog
from typing import Any, List, Tuple
from auth import get_auth_token
from async_api_client import AsyncAPIClient
from detector import compare_data
from mapping import map_items
from paginator import fetch_all_pages, DEFAULT_MAX_PAGES
from async_storage import init_async_db, save_async_snapshot, get_async_latest_snapshot
from config import CHECK_INTERVAL_SECONDS, API_ENDPOINTS

logger = structlog.get_logger()


async def check_api_changes_async(client: AsyncAPIClient, endpoint_path: str, endpoint_cfg: dict):
    """Асинхронная проверка изменений для эндпоинта."""
    try:
        logger.info("async_api_check_started", endpoint=endpoint_path)

        paginate = endpoint_cfg.get("paginate", False)
        items_path = endpoint_cfg.get("items_path") or None
        mapping = endpoint_cfg.get("mapping") or None
        max_pages = endpoint_cfg.get("max_pages", DEFAULT_MAX_PAGES)

        if paginate or items_path or mapping:
            # Асинхронно обходим ВСЕ страницы и нормализуем данные
            items = await fetch_all_pages_async(client, endpoint_path, items_path, max_pages)
            items = map_items(items, mapping)
            data = items
            logger.info("async_api_pagination_completed", endpoint=endpoint_path, items_count=len(items))
        else:
            # Старое поведение: один запрос, весь ответ как есть
            data = await client.get(endpoint_path)

        # Детектирование изменений с загрузкой предыдущего снимка
        latest = await get_async_latest_snapshot(f"api:{endpoint_path}")
        if latest:
            old_data = json.loads(latest['raw_data'])
            has_changed, changes = compare_data(old_data, data)
        else:
            has_changed = True
            changes = ["Первый снимок данных"]
        
        # Сохранение снимка
        await save_async_snapshot(
            f"api:{endpoint_path}", 
            data, 
            raw_data=None, 
            changes=changes if has_changed else None
        )
        
        if has_changed:
            logger.warning("async_changes_detected", endpoint=endpoint_path, changes=changes)
        else:
            logger.info("async_no_changes_detected", endpoint=endpoint_path)
            
    except Exception as e:
        logger.error("async_api_check_error", endpoint=endpoint_path, error=str(e))


async def fetch_all_pages_async(client: AsyncAPIClient, endpoint: str, items_path: str | None = None, max_pages: int = DEFAULT_MAX_PAGES) -> list:
    """
    Асинхронная версия fetch_all_pages для работы с AsyncAPIClient.
    Пока используем синхронную версию, так как paginator.py ещё не асинхронный.
    В будущем можно переписать paginator на aiohttp.
    """
    # Временное решение: используем синхронную версию
    # Для полноценной асинхронности нужно переписать paginator.py
    from paginator import fetch_all_pages as sync_fetch_all_pages
    
    # Создаём синхронный клиент для совместимости
    from api_client import APIClient
    sync_client = APIClient(token=client.token, base_url=client.base_url)
    
    return sync_fetch_all_pages(sync_client, endpoint, items_path, max_pages)


async def build_async_clients(shared_token: str | None) -> dict:
    """
    Строит {endpoint_path: (AsyncAPIClient, endpoint_cfg)} для каждого
    эндпоинта из config.API_ENDPOINTS, в зависимости от его auth_mode.
    """
    clients = {}
    for entry in API_ENDPOINTS:
        path = entry["path"]
        mode = entry.get("auth_mode", "login")

        if mode == "none":
            logger.info("async_client_created_no_auth", endpoint=path)
            clients[path] = (AsyncAPIClient(None), entry)

        elif mode == "token":
            token = entry.get("token")
            if not token:
                logger.warning("async_client_skip_no_token", endpoint=path)
                continue
            clients[path] = (AsyncAPIClient(token), entry)

        else:  # "login"
            if not shared_token:
                logger.warning("async_client_skip_no_shared_token", endpoint=path)
                continue
            clients[path] = (AsyncAPIClient(shared_token), entry)

    return clients


async def run_async_monitoring():
    """Основной цикл асинхронного мониторинга."""
    logger.info("async_monitoring_initialization_started")
    await init_async_db()

    if not API_ENDPOINTS:
        logger.error("no_endpoints_configured")
        return

    # Общий токен через логин нужен, только если хотя бы у одного
    # эндпоинта режим auth_mode == "login".
    needs_shared_token = any(
        entry.get("auth_mode", "login") == "login" for entry in API_ENDPOINTS
    )
    shared_token = None

    if needs_shared_token:
        logger.info("async_authentication_started")
        try:
            # get_auth_token пока синхронный, можно сделать асинхронным в будущем
            shared_token = get_auth_token()
            logger.info("async_authentication_completed_successfully")
        except Exception as e:
            logger.error("async_authentication_failed", error=str(e))
    else:
        logger.info("async_shared_login_not_required")

    clients = await build_async_clients(shared_token)
    if not clients:
        logger.error("no_async_clients_created")
        return

    logger.info("async_monitoring_started", interval=CHECK_INTERVAL_SECONDS, endpoints_count=len(clients))

    while True:
        try:
            # Параллельная проверка всех эндпоинтов
            tasks = [
                check_api_changes_async(client, path, endpoint_cfg)
                for path, (client, endpoint_cfg) in clients.items()
            ]
            await asyncio.gather(*tasks)

            logger.info("async_waiting_for_next_check", interval=CHECK_INTERVAL_SECONDS)
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logger.info("async_monitoring_stopped_by_user")
            break
        except Exception as e:
            logger.error("async_monitoring_loop_error", error=str(e))
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run_async_monitoring())
