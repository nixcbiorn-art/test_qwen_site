"""
Автоматический обход всех страниц пагинированного API.

Раньше monitor.py делал ровно один запрос на endpoint — то есть, если у
источника пагинация (page[number]/offset), парсились только данные с той
одной страницы, что указана в URL. Этот модуль решает задачу "спарсить
ВЕСЬ API": по параметрам в самом URL автоопределяется тип пагинации, и
запросы повторяются со следующими страницами/смещением, пока источник не
перестанет отдавать новые элементы.

Поддерживаемые виды пагинации (автоопределение по query-параметрам,
которые уже есть в настроенном URL endpoint'а):
  - "page[number]" или "page"  -> постраничная, инкремент номера страницы
  - "offset"                    -> постраничная по смещению
                                    (инкремент на limit/page[size])
Если ни один из этих параметров не найден в URL — считаем, что источник
без пагинации, и просто делаем один запрос (как раньше).
"""

import logging
import time
from typing import Any, List, Optional
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from mapping import extract_items

logger = logging.getLogger(__name__)

_PAGE_NUMBER_PARAMS = ("page[number]", "page")
_OFFSET_PARAMS = ("offset",)
_PAGE_SIZE_PARAMS = ("page[size]", "limit", "per_page", "pageSize")

PAGINATION_DELAY_SECONDS = 0.3  # пауза между запросами страниц (вежливость к серверу)
DEFAULT_MAX_PAGES = 50          # защита от бесконечного обхода


def _split_query(path: str):
    parts = urlsplit(path)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    return parts, query


def _rebuild(parts, query: dict) -> str:
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _detect_pagination_param(query: dict):
    for p in _PAGE_NUMBER_PARAMS:
        if p in query:
            return "page", p
    for p in _OFFSET_PARAMS:
        if p in query:
            return "offset", p
    return None, None


def _detect_page_size(query: dict) -> Optional[int]:
    for p in _PAGE_SIZE_PARAMS:
        if p in query:
            try:
                return int(query[p])
            except ValueError:
                pass
    return None


def fetch_all_pages(client, path: str, items_path: Optional[str] = None,
                     max_pages: int = DEFAULT_MAX_PAGES) -> List[Any]:
    """
    Проходит все страницы источника, начиная с URL из `path`, и объединяет
    элементы всех страниц в один список.

    path может быть как относительным ("estate/..."), так и полным URL
    ("https://fsk.ru/api/..." для endpoint'ов на другом домене) — работает
    одинаково в обоих случаях, т.к. APIClient сам решает, приклеивать ли
    базовый URL.

    Останов происходит когда: страница вернула 0 элементов, либо элементов
    меньше заявленного размера страницы (если размер удалось определить
    по параметрам URL), либо достигнут max_pages (страховка).
    """
    parts, query = _split_query(path)
    mode, param = _detect_pagination_param(query)

    if mode is None:
        # В URL нет распознаваемых параметров пагинации — обычный
        # одиночный запрос, как и раньше.
        data = client.get(path)
        return extract_items(data, items_path)

    page_size = _detect_page_size(query)
    all_items: List[Any] = []
    current = int(query.get(param, 1 if mode == "page" else 0))

    for page_num in range(1, max_pages + 1):
        query[param] = str(current)
        url = _rebuild(parts, query)

        data = client.get(url)
        items = extract_items(data, items_path)
        all_items.extend(items)

        logger.info(f"  страница {page_num}: {len(items)} элем. (всего: {len(all_items)})")

        if not items:
            break
        if page_size is not None and len(items) < page_size:
            break

        current = current + 1 if mode == "page" else current + (page_size or len(items))

        if page_num < max_pages:
            time.sleep(PAGINATION_DELAY_SECONDS)
    else:
        logger.warning(f"  достигнут лимит страниц ({max_pages}) — обход остановлен принудительно")

    return all_items
