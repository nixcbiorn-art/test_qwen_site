"""
CLI-инструмент: применить готовый маппинг, предложенный нейросетью (LLM),
к конкретному эндпоинту в settings.json — без ручного редактирования JSON
и без открытия ParserApp.

Обычный сценарий:
    1. python preview_endpoint.py 0 --out preview.json
    2. Отдать preview.json нейросети с просьбой предложить mapping.
    3. Сохранить ответ LLM в llm_mapping.json.
    4. python apply_mapping.py 0 llm_mapping.json

Ожидаемый формат mapping-файла (именно так стоит просить LLM вернуть ответ):
    {
      "items_path": "data",
      "mapping": {"id": "id", "title": "attributes.name", "price": "attributes.price.value"}
    }
Также принимается файл, где верхний уровень — сразу словарь маппинга,
без items_path:
    {"id": "id", "title": "attributes.name"}
"""

import argparse
import json
import os
import sys

from config import API_ENDPOINTS, SETTINGS_PATH


def _list_endpoints() -> None:
    print("Доступные эндпоинты (config.API_ENDPOINTS):")
    for i, entry in enumerate(API_ENDPOINTS):
        print(f"  [{i}] {entry['path']}")


def _load_llm_mapping(path: str):
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, dict) and isinstance(payload.get("mapping"), dict):
        items_path = payload.get("items_path") or ""
        mapping = payload["mapping"]
    elif isinstance(payload, dict):
        items_path = ""
        mapping = payload
    else:
        raise ValueError("Ожидался JSON-объект: {\"mapping\": {...}} или сразу {\"поле\": \"путь\", ...}")

    if not mapping or not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
        raise ValueError("mapping должен быть непустым {\"выходное_поле\": \"путь.в.json\"} (только строки)")

    return items_path, mapping


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("index", type=int, nargs="?", help="Номер эндпоинта из списка (см. запуск без аргументов)")
    parser.add_argument("mapping_file", type=str, nargs="?", help="Путь к JSON-файлу с маппингом от LLM")
    parser.add_argument("--paginate", action="store_true", help="Заодно включить paginate=true для этого эндпоинта")
    args = parser.parse_args()

    if args.index is None or args.mapping_file is None:
        _list_endpoints()
        return

    if not (0 <= args.index < len(API_ENDPOINTS)):
        print(f"Нет эндпоинта с индексом {args.index}.", file=sys.stderr)
        _list_endpoints()
        sys.exit(1)

    try:
        items_path, mapping = _load_llm_mapping(args.mapping_file)
    except (json.JSONDecodeError, ValueError, OSError) as e:
        print(f"Не удалось прочитать маппинг из {args.mapping_file}: {e}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(SETTINGS_PATH):
        print(f"Файл настроек не найден: {SETTINGS_PATH}. Сохрани настройки хотя бы раз через ParserApp.", file=sys.stderr)
        sys.exit(1)

    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        settings = json.load(f)

    endpoints = settings.get("endpoints", [])
    if not (0 <= args.index < len(endpoints)):
        print("Индекс не совпадает со списком endpoints в settings.json — открой ParserApp и сверь список.", file=sys.stderr)
        sys.exit(1)

    endpoints[args.index]["items_path"] = items_path
    endpoints[args.index]["mapping"] = mapping
    if args.paginate:
        endpoints[args.index]["paginate"] = True

    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

    print(f"Готово: маппинг применён к эндпоинту [{args.index}] {endpoints[args.index]['path']}")
    print(f"  items_path = {items_path or '(автоопределение)'}")
    print(f"  mapping = {mapping}")
    print(f"  файл: {SETTINGS_PATH}")


if __name__ == "__main__":
    main()
