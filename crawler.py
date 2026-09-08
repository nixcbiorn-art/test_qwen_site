"""
Грубый полный обход сайта.

Логика:
1. Стартуем с SITE_URL.
2. BFS по ссылкам <a href> в пределах того же домена.
3. Каждую страницу сохраняем как отдельный HTML-файл + запись в SQLite (таблица pages).
4. Останавливаемся по достижении CRAWL_MAX_PAGES или когда очередь пуста.

Это НЕ полноценный production-краулер:
- не учитывает robots.txt / crawl-delay с сайта
- не различает "мусорные" URL с одинаковым содержимым (сортировки, пагинация,
  utm-метки и т.п.) — по умолчанию query-параметры вообще отбрасываются
- не рендерит бесконечный скролл / динамическую подгрузку контента, кроме
  того, что успевает подгрузиться до networkidle
- не умеет резюмировать прерванный обход — при повторном запуске начнёт с нуля

Для чего-то большего (инкрементальный обход, вежливость к серверу,
дедупликация по контенту) — дорабатывать отдельно.
"""

import hashlib
import os
import sqlite3
import sys
import time
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag

from playwright.sync_api import sync_playwright

from config import (
    SITE_URL,
    HEADLESS_BROWSER,
    BROWSER_TYPE,
    DB_PATH,
    DATA_DIR,
    CRAWL_MAX_PAGES,
    CRAWL_DELAY_SECONDS,
    CRAWL_OUTPUT_DIR,
    CRAWL_INCLUDE_QUERY,
)

import logging

# stdout, а не stderr — иначе GUI на C# помечает обычные INFO-логи как ошибки
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def _init_pages_table():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            status_code INTEGER,
            content_hash TEXT,
            file_path TEXT,
            crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def _normalize_url(base_url: str, href: str) -> str | None:
    """Приводит относительные ссылки к абсолютным и отбрасывает то, что не относится к делу."""
    if not href:
        return None

    href = href.strip()

    # Пропускаем якоря, mailto, tel, javascript-ссылки
    if href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None

    absolute = urljoin(base_url, href)
    absolute, _fragment = urldefrag(absolute)  # убираем #anchor

    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https"):
        return None

    if not CRAWL_INCLUDE_QUERY:
        absolute = absolute.split("?")[0]

    # Убираем завершающий "/" для консистентности, кроме корня
    if absolute.endswith("/") and parsed.path != "/":
        absolute = absolute.rstrip("/")

    return absolute


def _is_same_domain(url: str, root_domain: str) -> bool:
    return urlparse(url).netloc == root_domain


def _safe_filename(url: str) -> str:
    h = hashlib.sha256(url.encode()).hexdigest()[:16]
    return f"{h}.html"


def crawl_site(start_url: str = SITE_URL, max_pages: int = CRAWL_MAX_PAGES) -> dict:
    """Запускает обход и возвращает сводку. Основная точка входа модуля."""
    _init_pages_table()
    os.makedirs(CRAWL_OUTPUT_DIR, exist_ok=True)

    root_domain = urlparse(start_url).netloc
    visited: set[str] = set()
    queue: deque[str] = deque([start_url])

    saved = 0
    failed = 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with sync_playwright() as p:
        browser_type = getattr(p, BROWSER_TYPE)
        browser = browser_type.launch(headless=HEADLESS_BROWSER)
        page = browser.new_page()

        try:
            while queue and len(visited) < max_pages:
                url = queue.popleft()
                if url in visited:
                    continue
                visited.add(url)

                logger.info(f"[{len(visited)}/{max_pages}] Загрузка: {url}")

                try:
                    response = page.goto(url, timeout=15000)
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception as e:
                    logger.warning(f"Не удалось загрузить {url}: {e}")
                    failed += 1
                    continue

                status_code = response.status if response else None
                html = page.content()
                title = page.title()
                content_hash = hashlib.sha256(html.encode("utf-8", "ignore")).hexdigest()

                file_name = _safe_filename(url)
                file_path = os.path.join(CRAWL_OUTPUT_DIR, file_name)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html)

                cursor.execute(
                    """
                    INSERT INTO pages (url, title, status_code, content_hash, file_path)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        title=excluded.title,
                        status_code=excluded.status_code,
                        content_hash=excluded.content_hash,
                        file_path=excluded.file_path,
                        crawled_at=CURRENT_TIMESTAMP
                    """,
                    (url, title, status_code, content_hash, file_path),
                )
                conn.commit()
                saved += 1

                # Собираем ссылки со страницы
                hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))")
                for href in hrefs:
                    normalized = _normalize_url(url, href)
                    if not normalized:
                        continue
                    if not _is_same_domain(normalized, root_domain):
                        continue
                    if normalized not in visited:
                        queue.append(normalized)

                time.sleep(CRAWL_DELAY_SECONDS)

        finally:
            browser.close()
            conn.close()

    summary = {
        "start_url": start_url,
        "pages_saved": saved,
        "pages_failed": failed,
        "pages_visited": len(visited),
        "output_dir": CRAWL_OUTPUT_DIR,
    }
    logger.info(f"Готово: {summary}")
    return summary


if __name__ == "__main__":
    crawl_site()
