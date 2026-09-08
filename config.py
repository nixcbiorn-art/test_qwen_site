"""
Конфигурация парсера.

Значения ниже — дефолты. Если рядом лежит data/settings.json (его пишет
вкладка "Настройки" в WPF-приложении), значения оттуда переопределяют
дефолты. Ключи в JSON — snake_case, совпадают с именами полей ниже.
"""

import json
import os

SITE_URL = "https://example.com"
API_BASE_URL = "https://api.example.com/v1"

LOGIN_URL = f"{SITE_URL}/login"
USERNAME = ""
PASSWORD = ""

CHECK_INTERVAL_SECONDS = 300
HEADLESS_BROWSER = True

# Абсолютные пути относительно расположения ЭТОГО файла (config.py), а не
# текущей рабочей директории процесса. Раньше пути были относительными
# ("data/settings.json") и резолвились от cwd — если скрипт запущен не из
# папки C:\parser (например, из ParserApp без явного WorkingDirectory),
# settings.json тихо не находился и использовались дефолты из этого файла.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(_BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "changes.db")

BROWSER_TYPE = "chromium"

# --- Настройки полного обхода сайта (crawler.py) ---
CRAWL_MAX_PAGES = 200          # ограничитель, чтобы не улететь в бесконечный обход
CRAWL_DELAY_SECONDS = 1.0      # пауза между запросами (вежливость к серверу)
CRAWL_OUTPUT_DIR = os.path.join(DATA_DIR, "pages")  # куда сохранять сырой HTML
CRAWL_INCLUDE_QUERY = False    # учитывать ли ?query-параметры как отдельные страницы

# --- Список API-эндпоинтов для monitor.py ---
# Каждый элемент:
# {
#   "path": "/data/items", "token": "", "auth_mode": "login",
#   "paginate": false,      # true -> автоматически обойти ВСЕ страницы
#                           #   (по page[number]/page/offset в URL) и
#                           #   объединить элементы всех страниц
#   "items_path": "",       # где в ответе лежит список элементов, если
#                           #   автоопределение не справляется, напр. "data"
#   "mapping": {},          # {"выходное_поле": "путь.в.json"} — нормализует
#                           #   каждый элемент к единому набору полей,
#                           #   удобному для сравнения между источниками.
#                           #   Пусто -> элементы сохраняются как есть.
#   "max_pages": 50          # страховка от бесконечного обхода при paginate
# }
#
# auth_mode задаёт способ взаимодействия с этим конкретным эндпоинтом:
#   "none"  — без авторизации вообще (открытый/публичный API, запрос идёт
#             без заголовка Authorization);
#   "token" — свой статический токен для этого эндпоинта (поле "token");
#             логин через браузер для него не требуется;
#   "login" — общий токен, полученный через auth.get_auth_token()
#             (Username/Password выше).
#
# Если auth_mode не задан (старый settings.json) — определяется
# автоматически: непустой token -> "token", иначе -> "login".
API_ENDPOINTS = [
    {"path": "/data/items", "token": "", "auth_mode": "login",
     "paginate": False, "items_path": "", "mapping": {}, "max_pages": 50},
    {"path": "/data/status", "token": "", "auth_mode": "login",
     "paginate": False, "items_path": "", "mapping": {}, "max_pages": 50},
]

SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")


def _apply_overrides():
    """Подтягивает settings.json, если он есть, и переопределяет дефолты выше."""
    global SITE_URL, API_BASE_URL, LOGIN_URL, USERNAME, PASSWORD
    global CHECK_INTERVAL_SECONDS, HEADLESS_BROWSER, API_ENDPOINTS

    if not os.path.exists(SETTINGS_PATH):
        return

    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[config] Не удалось прочитать {SETTINGS_PATH}: {e}")
        return

    if "site_url" in data and data["site_url"]:
        SITE_URL = data["site_url"]
        LOGIN_URL = f"{SITE_URL}/login"

    if "api_base_url" in data and data["api_base_url"]:
        API_BASE_URL = data["api_base_url"]

    if "username" in data:
        USERNAME = data["username"]

    if "password" in data:
        PASSWORD = data["password"]

    if "check_interval_seconds" in data:
        try:
            CHECK_INTERVAL_SECONDS = int(data["check_interval_seconds"])
        except (TypeError, ValueError):
            pass

    if "headless_browser" in data:
        HEADLESS_BROWSER = bool(data["headless_browser"])

    endpoints = data.get("endpoints")
    if endpoints:
        parsed_endpoints = []
        for e in endpoints:
            path = e.get("path", "")
            if not path:
                continue

            token = e.get("token", "")
            auth_mode = e.get("auth_mode")

            if auth_mode not in ("none", "token", "login"):
                # Старый settings.json без auth_mode: определяем режим
                # по наличию токена, как раньше.
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

        API_ENDPOINTS = parsed_endpoints


_apply_overrides()
