"""Главный модуль мониторинга."""

import sys
import time
import logging
from auth import get_auth_token
from api_client import APIClient
from detector import detect_and_store
from mapping import map_items
from paginator import fetch_all_pages, DEFAULT_MAX_PAGES
from storage import init_db
from config import CHECK_INTERVAL_SECONDS, API_ENDPOINTS

# По умолчанию logging пишет в stderr — GUI на C# помечает весь stderr
# как ошибку. Явно направляем в stdout, чтобы обычные INFO-сообщения
# не подсвечивались как [ERR].
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def check_api_changes(client: APIClient, endpoint_path: str, endpoint_cfg: dict):
    try:
        logger.info(f"Проверка API: {endpoint_path}")

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
            logger.info(f"  итого элементов: {len(items)}")
        else:
            # Старое поведение: один запрос, весь ответ как есть.
            data = client.get(endpoint_path)

        result = detect_and_store(f"api:{endpoint_path}", data)
        if result['has_changed']:
            logger.warning(f"Изменения в {endpoint_path}:")
            for c in result['changes']:
                logger.warning(f"  - {c}")
        else:
            logger.info(f"Нет изменений в {endpoint_path}")
    except Exception as e:
        logger.error(f"Ошибка API {endpoint_path}: {e}")


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
            logger.info(f"{path}: без авторизации (открытый источник)")
            clients[path] = (APIClient(None), entry)

        elif mode == "token":
            token = entry.get("token")
            if not token:
                logger.warning(f"Для {path} режим 'token', но токен не задан — пропускаю")
                continue
            clients[path] = (APIClient(token), entry)

        else:  # "login"
            if not shared_token:
                logger.warning(f"Для {path} режим 'login', но общий токен не получен — пропускаю")
                continue
            clients[path] = (APIClient(shared_token), entry)

    return clients


def run_monitoring():
    logger.info("Инициализация БД...")
    init_db()

    if not API_ENDPOINTS:
        logger.error("Список эндпоинтов пуст (config.API_ENDPOINTS). Нечего мониторить.")
        return

    # Общий токен через логин нужен, только если хотя бы у одного
    # эндпоинта режим auth_mode == "login".
    needs_shared_token = any(
        entry.get("auth_mode", "login") == "login" for entry in API_ENDPOINTS
    )
    shared_token = None

    if needs_shared_token:
        logger.info("Авторизация (логин через Playwright)...")
        try:
            shared_token = get_auth_token()
            logger.info("Успешно")
        except Exception as e:
            logger.error(f"Ошибка авторизации: {e}")
            # Не выходим сразу — возможно, у части эндпоинтов режим "none"/"token"
    else:
        logger.info("Ни одному эндпоинту не нужен общий логин-токен — логин через браузер пропущен.")

    clients = build_clients(shared_token)
    if not clients:
        logger.error("Не удалось получить токен ни для одного эндпоинта. Останов.")
        return

    logger.info(f"Мониторинг запущен (интервал: {CHECK_INTERVAL_SECONDS}с, эндпоинтов: {len(clients)})")

    while True:
        try:
            for path, (client, endpoint_cfg) in clients.items():
                check_api_changes(client, path, endpoint_cfg)

            logger.info(f"Ожидание {CHECK_INTERVAL_SECONDS}с...")
            time.sleep(CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logger.info("Остановлен")
            break
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            time.sleep(60)


if __name__ == "__main__":
    run_monitoring()
