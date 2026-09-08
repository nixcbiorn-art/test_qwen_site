"""Главный модуль мониторинга."""

import sys
import time
import structlog
from auth import get_auth_token
from api_client import APIClient
from detector import detect_and_store
from mapping import map_items
from paginator import fetch_all_pages, DEFAULT_MAX_PAGES
from storage import init_db
from config import CHECK_INTERVAL_SECONDS, API_ENDPOINTS

logger = structlog.get_logger()


def check_api_changes(client: APIClient, endpoint_path: str, endpoint_cfg: dict):
    try:
        logger.info("api_check_started", endpoint=endpoint_path)

        paginate = endpoint_cfg.get("paginate", False)
        items_path = endpoint_cfg.get("items_path") or None
        mapping = endpoint_cfg.get("mapping") or None
        max_pages = endpoint_cfg.get("max_pages", DEFAULT_MAX_PAGES)

        if paginate or items_path or mapping:
            # Обходим ВСЕ страницы (если пагинация распознана в URL) и/или
            # достаём+нормализуем список элементов, а не сырой ответ целиком.
            items = fetch_all_pages(client, endpoint_path, items_path, max_pages)
            items = map_items(items, mapping)
            data = items
            logger.info("api_pagination_completed", endpoint=endpoint_path, items_count=len(items))
        else:
            # Старое поведение: один запрос, весь ответ как есть.
            data = client.get(endpoint_path)

        result = detect_and_store(f"api:{endpoint_path}", data)
        if result['has_changed']:
            logger.warning("changes_detected", endpoint=endpoint_path, changes=result['changes'])
        else:
            logger.info("no_changes_detected", endpoint=endpoint_path)
    except Exception as e:
        logger.error("api_check_error", endpoint=endpoint_path, error=str(e))


def build_clients(shared_token: str | None) -> dict:
    """
    Строит {endpoint_path: (APIClient, endpoint_cfg)} для каждого
    эндпоинта из config.API_ENDPOINTS, в зависимости от его auth_mode:
      "none"  — без авторизации (открытый/публичный API);
      "token" — собственный статический токен эндпоинта;
      "login" — общий токен, полученный через логин (Username/Password).
    """
    clients = {}
    for entry in API_ENDPOINTS:
        path = entry["path"]
        mode = entry.get("auth_mode", "login")

        if mode == "none":
            logger.info("client_created_no_auth", endpoint=path)
            clients[path] = (APIClient(None), entry)

        elif mode == "token":
            token = entry.get("token")
            if not token:
                logger.warning("client_skip_no_token", endpoint=path)
                continue
            clients[path] = (APIClient(token), entry)

        else:  # "login"
            if not shared_token:
                logger.warning("client_skip_no_shared_token", endpoint=path)
                continue
            clients[path] = (APIClient(shared_token), entry)

    return clients


def run_monitoring():
    logger.info("monitoring_initialization_started")
    init_db()

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
        logger.info("authentication_started")
        try:
            shared_token = get_auth_token()
            logger.info("authentication_completed_successfully")
        except Exception as e:
            logger.error("authentication_failed", error=str(e))
            # Не выходим сразу — возможно, у части эндпоинтов режим "none"/"token"
    else:
        logger.info("shared_login_not_required")

    clients = build_clients(shared_token)
    if not clients:
        logger.error("no_clients_created")
        return

    logger.info("monitoring_started", interval=CHECK_INTERVAL_SECONDS, endpoints_count=len(clients))

    while True:
        try:
            for path, (client, endpoint_cfg) in clients.items():
                check_api_changes(client, path, endpoint_cfg)

            logger.info("waiting_for_next_check", interval=CHECK_INTERVAL_SECONDS)
            time.sleep(CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logger.info("monitoring_stopped_by_user")
            break
        except Exception as e:
            logger.error("monitoring_loop_error", error=str(e))
            time.sleep(60)


if __name__ == "__main__":
    run_monitoring()
