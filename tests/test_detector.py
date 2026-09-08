"""Тесты для модуля detector."""

import pytest
from detector import compare_data, _compare_dicts, _compare_lists


class TestCompareData:
    def test_primitives_equal(self):
        changed, changes = compare_data(5, 5)
        assert changed is False
        assert changes == []

    def test_primitives_different(self):
        changed, changes = compare_data(5, 10)
        assert changed is True
        assert len(changes) == 1

    def test_dicts_equal(self):
        old = {"a": 1, "b": 2}
        new = {"a": 1, "b": 2}
        changed, changes = compare_data(old, new)
        assert changed is False

    def test_dicts_added_key(self):
        old = {"a": 1}
        new = {"a": 1, "b": 2}
        changed, changes = compare_data(old, new)
        assert changed is True
        assert any("Добавлено" in c for c in changes)

    def test_dicts_removed_key(self):
        old = {"a": 1, "b": 2}
        new = {"a": 1}
        changed, changes = compare_data(old, new)
        assert changed is True
        assert any("Удалено" in c for c in changes)

    def test_dicts_modified_value(self):
        old = {"a": 1}
        new = {"a": 2}
        changed, changes = compare_data(old, new)
        assert changed is True
        assert any("Изменено" in c for c in changes)


class TestCompareLists:
    def test_lists_equal(self):
        old = [{"id": 1}, {"id": 2}]
        new = [{"id": 1}, {"id": 2}]
        changed, changes = compare_data(old, new)
        assert changed is False

    def test_lists_added_element_by_id(self):
        old = [{"id": 1}]
        new = [{"id": 1}, {"id": 2}]
        changed, changes = compare_data(old, new)
        assert changed is True
        assert any("Новый элемент" in c for c in changes)

    def test_lists_removed_element_by_id(self):
        old = [{"id": 1}, {"id": 2}]
        new = [{"id": 1}]
        changed, changes = compare_data(old, new)
        assert changed is True
        assert any("удалён" in c.lower() for c in changes)

    def test_lists_modified_element_by_id(self):
        old = [{"id": 1, "name": "a"}]
        new = [{"id": 1, "name": "b"}]
        changed, changes = compare_data(old, new)
        assert changed is True
        assert any("Изменён" in c for c in changes)

    def test_lists_different_size(self):
        old = [1, 2]
        new = [1, 2, 3]
        changed, changes = compare_data(old, new)
        assert changed is True
