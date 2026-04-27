import json
import pytest
from unittest.mock import patch
import db


@pytest.fixture
def client(temp_db):
    import app as flask_app
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c


# --- POST /add ---

def test_add_returns_201_with_price(client):
    with patch("scraper.get_price", return_value=89.99):
        resp = client.post(
            "/add",
            data=json.dumps({"url": "https://example.com/shoe", "name": "Air Max", "user": "fitz"}),
            content_type="application/json",
        )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["price"] == 89.99
    assert body["name"] == "Air Max"
    assert "id" in body


def test_add_persists_to_db(client):
    with patch("scraper.get_price", return_value=120.00):
        client.post(
            "/add",
            data=json.dumps({"url": "https://example.com/shoe", "name": "Jordan 1", "user": "sha"}),
            content_type="application/json",
        )
    items = db.get_all_items()
    assert len(items) == 1
    assert items[0]["item_name"] == "Jordan 1"
    assert items[0]["user_id"] == "sha"
    assert items[0]["initial_price"] == 120.00


def test_add_returns_400_missing_fields(client):
    resp = client.post(
        "/add",
        data=json.dumps({"url": "https://example.com"}),
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_add_returns_400_unknown_user(client):
    resp = client.post(
        "/add",
        data=json.dumps({"url": "https://example.com", "name": "Shoe", "user": "ghost"}),
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_add_returns_422_when_price_not_found(client):
    with patch("scraper.get_price", side_effect=ValueError("Could not extract price")):
        resp = client.post(
            "/add",
            data=json.dumps({"url": "https://example.com/shoe", "name": "Shoe", "user": "fitz"}),
            content_type="application/json",
        )
    assert resp.status_code == 422


# --- GET /status ---

def test_status_returns_200(client):
    resp = client.get("/status")
    assert resp.status_code == 200
    assert b"Price Tracker" in resp.data


def test_status_shows_item(client):
    with patch("scraper.get_price", return_value=100.00):
        client.post(
            "/add",
            data=json.dumps({"url": "https://example.com", "name": "Test Shoe", "user": "fitz"}),
            content_type="application/json",
        )
    resp = client.get("/status")
    assert b"Test Shoe" in resp.data
    assert b"100.00" in resp.data


# --- DELETE /remove ---

def test_remove_returns_200(client):
    with patch("scraper.get_price", return_value=100.00):
        add_resp = client.post(
            "/add",
            data=json.dumps({"url": "https://example.com", "name": "Shoe", "user": "fitz"}),
            content_type="application/json",
        )
    item_id = add_resp.get_json()["id"]
    resp = client.delete(f"/remove/{item_id}")
    assert resp.status_code == 200
    assert resp.get_json()["deleted"] == item_id


def test_remove_item_is_gone(client):
    with patch("scraper.get_price", return_value=100.00):
        add_resp = client.post(
            "/add",
            data=json.dumps({"url": "https://example.com", "name": "Shoe", "user": "fitz"}),
            content_type="application/json",
        )
    item_id = add_resp.get_json()["id"]
    client.delete(f"/remove/{item_id}")
    assert db.get_item(item_id) is None


def test_remove_returns_404_for_missing_item(client):
    resp = client.delete("/remove/99999")
    assert resp.status_code == 404
