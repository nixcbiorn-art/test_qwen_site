"""
Превью данных для валидации полей нейросетью (LLM) — дёшево и быстро.

Проблема: чтобы LLM помогла настроить/проверить mapping (items_path +
поля) для нового источника, ей обычно скармливают весь ответ API. Но
ответ может быть тысячами строк и мегабайтами JSON — это дорого (много
токенов) и медленно, а для понимания структуры данных совершенно не
нужно: одинаковые ключи повторяются в каждом элементе списка.

Этот модуль готовит компактную выжимку:
  - "approx_keys" — свод ВСЕХ путей полей, встретившихся в выборке
    (напр. "attributes.price.value"), с одним примером значения на каждый
    путь — этого достаточно, чтобы понять структуру данных;
  - "rows" — первые sample_size (по умолчанию 100) элементов как есть —
    достаточно LLM, чтобы убедиться, что примеры значений реалистичны, и
    предложить сам mapping ({"выходное_поле": "путь.в.json"}).

Итоговый объём на выходе почти не растёт с размером реального датасета
(100 записей и 10 000 записей дают примерно одинаковый по размеру
preview), в отличие от передачи LLM всего ответа целиком.
"""

import json
from typing import Any, Dict, List, Optional

from mapping import extract_items

DEFAULT_SAMPLE_SIZE = 100
MAX_KEY_DEPTH = 5           # глубина вложенности при сборе ключей
MAX_VALUE_PREVIEW_LEN = 120  # обрезка длинных значений (описания, base64 и т.п.)


def _truncate(value: Any) -> Any:
    if isinstance(value, str) and len(value) > MAX_VALUE_PREVIEW_LEN:
        return value[:MAX_VALUE_PREVIEW_LEN] + "…"
    return value


def _walk_keys(obj: Any, prefix: str, depth: int, keys: Dict[str, Any]) -> None:
    """
    Рекурсивно собирает пути полей (в том же формате точечной нотации,
    что использует mapping.get_by_path) и запоминает первый встретившийся
    непустой пример значения для каждого пути.
    """
    if depth > MAX_KEY_DEPTH:
        return

    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, (dict, list)):
                _walk_keys(value, path, depth + 1, keys)
            elif path not in keys or keys[path] in (None, "", []):
                keys[path] = _truncate(value)

    elif isinstance(obj, list):
        if obj:
            # Одного первого элемента списка достаточно, чтобы понять его
            # структуру — не раздуваем превью на каждый элемент вложенного списка.
            _walk_keys(obj[0], f"{prefix}.0", depth + 1, keys)


def build_field_preview(response: Any, items_path: Optional[str] = None,
                         sample_size: int = DEFAULT_SAMPLE_SIZE) -> Dict[str, Any]:
    """
    Готовит компактное превью для LLM.

    response:    сырой ответ API, либо уже готовый список элементов
                 (list) — тогда items_path игнорируется.
    items_path:  где в ответе лежит список элементов (см. mapping.py).
                 Пусто — автоопределение, как и в mapping.extract_items.
    sample_size: сколько первых элементов включить как есть (по умолчанию 100).

    Возвращает dict:
      total_items  — сколько элементов реально найдено в ответе;
      sample_size  — сколько из них попало в превью;
      approx_keys  — {"путь.в.json": пример_значения} по всей выборке;
      rows         — первые sample_size элементов как есть.
    """
    items: List[Any] = response if isinstance(response, list) else extract_items(response, items_path)
    sample = items[:sample_size]

    keys: Dict[str, Any] = {}
    for item in sample:
        _walk_keys(item, "", 1, keys)

    return {
        "total_items": len(items),
        "sample_size": len(sample),
        "approx_keys": keys,
        "rows": sample,
    }


def build_field_preview_json(response: Any, items_path: Optional[str] = None,
                              sample_size: int = DEFAULT_SAMPLE_SIZE) -> str:
    """
    То же, что build_field_preview, но сразу сериализовано в компактную
    JSON-строку — удобно вставлять прямо в промпт LLM.
    """
    preview = build_field_preview(response, items_path, sample_size)
    return json.dumps(preview, ensure_ascii=False, separators=(",", ":"))
