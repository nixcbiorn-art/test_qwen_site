"""
Маппинг (нормализация) элементов ответа API в единый плоский формат.

Разные источники (redcat, fsk.ru, samolet.ru и т.п.) возвращают данные в
разной структуре. Этот модуль решает две задачи:

1. Достать список элементов из ответа, где бы он ни лежал
   (response["data"], response["results"], сам response как список, ...).
2. Опционально привести каждый элемент к единому набору полей по
   конфигурации endpoint'а ("mapping" в settings.json), например:
       {"id": "id", "title": "attributes.name", "price": "attributes.price"}
   Тогда для любого источника в базе будут одинаковые ключи id/title/price,
   и их удобно сравнивать между собой и по времени.
"""

from typing import Any, Dict, List, Optional

# Ключи, где чаще всего лежит список элементов, если items_path не задан.
_COMMON_LIST_KEYS = (
    "data", "results", "items", "list", "records",
    "flats", "apartments", "complexes", "objects",
)


def get_by_path(obj: Any, path: str) -> Any:
    """
    Достаёт значение по пути вида "attributes.price.value" или
    "images.0.url" (числовой сегмент — индекс в списке).
    Возвращает None, если путь не найден.
    """
    if not path:
        return obj

    current = obj
    for part in path.split("."):
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


def extract_items(response: Any, items_path: Optional[str] = None) -> List[Any]:
    """
    Достаёт список элементов из ответа API.

    - Если items_path задан явно — берём строго по этому пути.
    - Если не задан — автоопределение: если response сам список, берём
      его; если словарь — ищем первый из типичных ключей (_COMMON_LIST_KEYS),
      под которым лежит список.
    - Если ничего не найдено — оборачиваем весь response в список из
      одного элемента, чтобы не терять данные.
    """
    if items_path:
        found = get_by_path(response, items_path)
        if isinstance(found, list):
            return found
        return [] if found is None else [found]

    if isinstance(response, list):
        return response

    if isinstance(response, dict):
        for key in _COMMON_LIST_KEYS:
            value = response.get(key)
            if isinstance(value, list):
                return value

    return [response]


def map_item(item: Any, mapping: Optional[Dict[str, str]]) -> Any:
    """Применяет маппинг {выходное_поле: путь_в_json} к одному элементу."""
    if not mapping:
        return item
    return {out_field: get_by_path(item, src_path) for out_field, src_path in mapping.items()}


def map_items(items: List[Any], mapping: Optional[Dict[str, str]]) -> List[Any]:
    if not mapping:
        return items
    return [map_item(item, mapping) for item in items]
