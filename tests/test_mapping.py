"""Тесты для модуля mapping."""

import pytest
from mapping import get_by_path, extract_items, map_item, map_items


class TestGetByPath:
    def test_simple_key(self):
        data = {"id": 123, "name": "test"}
        assert get_by_path(data, "id") == 123
        assert get_by_path(data, "name") == "test"

    def test_nested_path(self):
        data = {"attributes": {"price": {"value": 100}}}
        assert get_by_path(data, "attributes.price.value") == 100

    def test_list_index(self):
        data = {"images": [{"url": "a.jpg"}, {"url": "b.jpg"}]}
        assert get_by_path(data, "images.0.url") == "a.jpg"
        assert get_by_path(data, "images.1.url") == "b.jpg"

    def test_missing_path(self):
        data = {"id": 1}
        assert get_by_path(data, "nonexistent") is None
        assert get_by_path(data, "attributes.price") is None

    def test_empty_path(self):
        data = {"id": 1}
        assert get_by_path(data, "") == data

    def test_none_value(self):
        assert get_by_path(None, "any.path") is None


class TestExtractItems:
    def test_response_is_list(self):
        response = [{"id": 1}, {"id": 2}]
        assert extract_items(response) == response

    def test_common_keys_data(self):
        response = {"data": [{"id": 1}], "meta": {}}
        assert extract_items(response) == [{"id": 1}]

    def test_common_keys_results(self):
        response = {"results": [{"id": 1}]}
        assert extract_items(response) == [{"id": 1}]

    def test_items_path_explicit(self):
        response = {"nested": {"items": [{"id": 1}]}}
        assert extract_items(response, "nested.items") == [{"id": 1}]

    def test_wrap_single_item(self):
        response = {"id": 1}
        assert extract_items(response) == [{"id": 1}]


class TestMapItem:
    def test_simple_mapping(self):
        item = {"id": 1, "attributes": {"name": "test"}}
        mapping = {"id": "id", "title": "attributes.name"}
        result = map_item(item, mapping)
        assert result == {"id": 1, "title": "test"}

    def test_no_mapping(self):
        item = {"id": 1}
        assert map_item(item, None) == item
        assert map_item(item, {}) == item

    def test_missing_field(self):
        item = {"id": 1}
        mapping = {"id": "id", "missing": "nonexistent"}
        result = map_item(item, mapping)
        assert result == {"id": 1, "missing": None}


class TestMapItems:
    def test_map_multiple_items(self):
        items = [
            {"id": 1, "attrs": {"name": "a"}},
            {"id": 2, "attrs": {"name": "b"}}
        ]
        mapping = {"id": "id", "title": "attrs.name"}
        result = map_items(items, mapping)
        assert result == [
            {"id": 1, "title": "a"},
            {"id": 2, "title": "b"}
        ]

    def test_no_mapping(self):
        items = [{"id": 1}, {"id": 2}]
        assert map_items(items, None) == items
