import pytest
import db


def test_init_creates_users(temp_db):
    users = db.get_all_users()
    assert "fitz" in users
    assert "sha" in users
    assert users["fitz"]["phone"] == "15163026553"
    assert users["sha"]["phone"] == "13184369753"


def test_get_all_items_empty(temp_db):
    assert db.get_all_items() == []


def test_add_item_returns_id(temp_db):
    item_id = db.add_item("fitz", "https://example.com", "Test Shoe", 120.00)
    assert isinstance(item_id, int)
    assert item_id > 0


def test_add_item_sets_all_prices(temp_db):
    item_id = db.add_item("fitz", "https://example.com", "Test Shoe", 120.00)
    item = db.get_item(item_id)
    assert item["initial_price"] == 120.00
    assert item["last_price"] == 120.00
    assert item["last_notified_price"] == 120.00


def test_get_all_items_returns_added_item(temp_db):
    db.add_item("fitz", "https://example.com", "Test Shoe", 120.00)
    items = db.get_all_items()
    assert len(items) == 1
    assert items[0]["item_name"] == "Test Shoe"
    assert items[0]["user_id"] == "fitz"


def test_update_item_price(temp_db):
    item_id = db.add_item("fitz", "https://example.com", "Test Shoe", 120.00)
    db.update_item_price(item_id, 99.99, "2026-01-01T00:00:00+00:00")
    item = db.get_item(item_id)
    assert item["last_price"] == 99.99
    assert item["last_checked_at"] == "2026-01-01T00:00:00+00:00"


def test_update_notified_price(temp_db):
    item_id = db.add_item("fitz", "https://example.com", "Test Shoe", 120.00)
    db.update_notified_price(item_id, 99.99)
    item = db.get_item(item_id)
    assert item["last_notified_price"] == 99.99


def test_remove_item(temp_db):
    item_id = db.add_item("fitz", "https://example.com", "Test Shoe", 120.00)
    db.remove_item(item_id)
    assert db.get_item(item_id) is None


def test_get_item_returns_none_for_missing(temp_db):
    assert db.get_item(99999) is None
