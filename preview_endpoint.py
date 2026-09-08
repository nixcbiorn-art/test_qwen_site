"""
CLI-инструмент: собрать компактное превью для одного эндпоинта из
config.API_ENDPOINTS (первые N строк + примерные ключи) и сохранить в
файл, чтобы вставить в промпт LLM при настройке mapping — без того, чтобы
скармливать нейросети весь ответ API целиком.

Запуск:
    python preview_endpoint.py                # список эндпоинтов с номерами
    python preview_endpoint.py 0               # превью эндпоинта №0
    python preview_endpoint.py 0 --rows 50     # ограничить выборку 50 строками
    python preview_endpoint.py 0 --out p.json  # сохранить в файл вместо печати
"""

import argparse
import sys

from api_client import APIClient
from config import API_ENDPOINTS
from paginator import fetch_all_pages
from preview import DEFAULT_SAMPLE_SIZE, build_field_preview_json


def _list_endpoints() -> None:
    print("Доступные эндпоинты (config.API_ENDPOINTS):")
    for i, entry in enumerate(API_ENDPOINTS):
        print(f"  [{i}] {entry['path']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=int, nargs="?", help="Номер эндпоинта из списка (см. запуск без аргументов)")
    parser.add_argument("--rows", type=int, default=DEFAULT_SAMPLE_SIZE, help="Сколько первых строк включить в превью")
    parser.add_argument("--out", type=str, default=None, help="Сохранить превью в файл вместо печати в консоль")
    args = parser.parse_args()

    if args.index is None:
        _list_endpoints()
        return

    if not (0 <= args.index < len(API_ENDPOINTS)):
        print(f"Нет эндпоинта с индексом {args.index}.", file=sys.stderr)
        _list_endpoints()
        sys.exit(1)

    entry = API_ENDPOINTS[args.index]
    path = entry["path"]

    token = entry.get("token") if entry.get("auth_mode") == "token" else None
    client = APIClient(token)

    print(f"Запрашиваю {path} ...", file=sys.stderr)
    items = fetch_all_pages(client, path, entry.get("items_path") or None,
                             entry.get("max_pages", 50) if entry.get("paginate") else 1)

    preview_json = build_field_preview_json(items, sample_size=args.rows)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(preview_json)
        print(f"Превью сохранено в {args.out}", file=sys.stderr)
    else:
        print(preview_json)


if __name__ == "__main__":
    main()
