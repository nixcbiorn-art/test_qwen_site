"""Детектор изменений с улучшенной детализацией."""

import json
import structlog
from typing import Any, Dict, List, Tuple
from storage import save_snapshot, get_latest_snapshot

logger = structlog.get_logger()


def compare_data(old_data: Any, new_data: Any) -> Tuple[bool, List[str]]:
    """Сравнивает старые и новые данные, возвращает флаг изменения и список изменений."""
    if isinstance(old_data, dict) and isinstance(new_data, dict):
        return _compare_dicts(old_data, new_data)
    elif isinstance(old_data, list) and isinstance(new_data, list):
        return _compare_lists(old_data, new_data)
    else:
        changed = old_data != new_data
        return changed, [f"Значение изменено: {old_data} -> {new_data}"] if changed else []


def _compare_dicts(old: Dict, new: Dict) -> Tuple[bool, List[str]]:
    changes = []
    old_keys = set(old.keys())
    new_keys = set(new.keys())

    for key in new_keys - old_keys:
        changes.append(f"Добавлено: {key} = {new[key]}")
    for key in old_keys - new_keys:
        changes.append(f"Удалено: {key}")
    for key in old_keys & new_keys:
        if old[key] != new[key]:
            changes.append(f"Изменено: {key}: {old[key]} -> {new[key]}")

    return len(changes) > 0, changes


def _looks_like_id_list(lst: List) -> bool:
    """Список словарей, где у каждого элемента есть ключ 'id'."""
    return bool(lst) and all(isinstance(x, dict) and "id" in x for x in lst)


def _diff_fields(old: Dict, new: Dict) -> str:
    parts = []
    for key in sorted(set(old.keys()) | set(new.keys())):
        if old.get(key) != new.get(key):
            parts.append(f"{key}: {old.get(key)} -> {new.get(key)}")
    return "; ".join(parts) if parts else "(без видимых отличий по полям)"


def _compare_lists_by_id(old: List[Dict], new: List[Dict]) -> Tuple[bool, List[str]]:
    """
    Сравнение списков записей по полю "id" (получается после mapping.py,
    когда каждый элемент нормализован и имеет id). Даёт куда более полезный
    результат, чем позиционное сравнение: видно конкретно, какие записи
    добавились/пропали/изменились и в каком поле.
    """
    old_by_id = {item["id"]: item for item in old}
    new_by_id = {item["id"]: item for item in new}

    changes = []
    for _id in new_by_id.keys() - old_by_id.keys():
        changes.append(f"Новый элемент: id={_id}")
    for _id in old_by_id.keys() - new_by_id.keys():
        changes.append(f"Элемент удалён: id={_id}")
    for _id in old_by_id.keys() & new_by_id.keys():
        if old_by_id[_id] != new_by_id[_id]:
            changes.append(f"Изменён id={_id}: {_diff_fields(old_by_id[_id], new_by_id[_id])}")

    return len(changes) > 0, changes


def _compare_lists(old: List, new: List) -> Tuple[bool, List[str]]:
    if _looks_like_id_list(old) and _looks_like_id_list(new):
        return _compare_lists_by_id(old, new)

    if len(old) != len(new):
        return True, [f"Размер списка: {len(old)} -> {len(new)}"]
    changes = []
    for i, (o, n) in enumerate(zip(old, new)):
        if o != n:
            changes.append(f"Элемент [{i}] изменен")
    return len(changes) > 0, changes


def detect_and_store(endpoint: str, new_data: Any) -> Dict:
    """
    Обнаруживает изменения и сохраняет снимок данных.
    
    Args:
        endpoint: Путь к эндпоинту
        new_data: Новые данные
        
    Returns:
        Dict с результатами: has_changed, changes, timestamp
    """
    latest = get_latest_snapshot(endpoint)
    if latest:
        old_data = json.loads(latest['raw_data'])
        has_changed, changes = compare_data(old_data, new_data)
    else:
        has_changed = True
        changes = ["Первый снимок данных"]

    logger.info("change_detection_completed", endpoint=endpoint, has_changed=has_changed, changes_count=len(changes))
    
    # Передаём изменения для сохранения в историю
    save_snapshot(endpoint, new_data, changes=changes if has_changed else None)
    
    return {
        "has_changed": has_changed, 
        "changes": changes, 
        "timestamp": latest['timestamp'] if latest else None
    }
