import json
import sys
import pytest
from unittest.mock import patch, MagicMock
import db


@pytest.fixture
def client(temp_db):
    import app as flask_app
    flask_app.app.config["TESTING"] = True
    flask_app.app.secret_key = "test-secret-key"
    with flask_app.app.test_client() as c:
        with c.session_transaction() as sess:
            sess["logged_in"] = True
        yield c


@pytest.fixture
def unauthed_client(temp_db):
    import app as flask_app
    flask_app.app.config["TESTING"] = True
    flask_app.app.secret_key = "test-secret-key"
    with flask_app.app.test_client() as c:
        yield c


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.APP_PIN = "0506"
    cfg.SECRET_KEY = "test-secret-key"
    with patch.dict(sys.modules, {"config": cfg}):
        yield cfg


# --- Login ---

def test_login_page_renders(unauthed_client):
    resp = unauthed_client.get("/login")
    assert resp.status_code == 200
    assert b"PIN" in resp.data


def test_login_correct_pin_redirects(unauthed_client, mock_config):
    resp = unauthed_client.post("/login", data={"pin": "0506"})
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/"


def test_login_wrong_pin_shows_error(unauthed_client, mock_config):
    resp = unauthed_client.post("/login", data={"pin": "9999"})
    assert resp.status_code == 200
    assert b"Wrong PIN" in resp.data


def test_unauthenticated_redirects_to_login(unauthed_client):
    resp = unauthed_client.get("/")
    assert resp.status_code == 302
    assert "login" in resp.headers["Location"]


def test_unauthenticated_api_returns_401(unauthed_client):
    resp = unauthed_client.post(
        "/add",
        data=json.dumps({"url": "https://example.com", "name": "Shoe", "user": "fitz"}),
        content_type="application/json",
    )
    assert resp.status_code == 401


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


# --- GET / (web form) ---

def test_index_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Track a Price" in resp.data


# --- POST /track ---

def test_track_adds_item_and_shows_success(client):
    with patch("scraper.get_price", return_value=89.99):
        resp = client.post("/track", data={"url": "https://example.com", "name": "Air Max", "user": "fitz"})
    assert resp.status_code == 200
    assert b"added at" in resp.data
    assert len(db.get_all_items()) == 1


def test_track_shows_error_on_missing_fields(client):
    resp = client.post("/track", data={"url": "https://example.com"})
    assert resp.status_code == 200
    assert b"required" in resp.data


def test_track_shows_error_when_price_not_found(client):
    with patch("scraper.get_price", side_effect=ValueError("Could not extract price")):
        resp = client.post("/track", data={"url": "https://example.com", "name": "Shoe", "user": "fitz"})
    assert resp.status_code == 200
    assert b"Couldn" in resp.data


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
