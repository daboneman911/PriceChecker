import sys
import pytest
from unittest.mock import patch, MagicMock, call
import db
import monitor


@pytest.fixture
def seeded_db(temp_db):
    """DB with one item for Fitz at $120."""
    item_id = db.add_item("fitz", "https://example.com/shoe", "Air Max 90", 120.00)
    return item_id


def test_monitor_sends_alert_on_price_drop(seeded_db):
    item_id = seeded_db
    with patch("scraper.get_price", return_value=89.99):
        with patch("notifier.send_price_alert", return_value=True) as mock_notify:
            monitor.run()

    mock_notify.assert_called_once_with(
        user_id="fitz",
        item_name="Air Max 90",
        current_price=89.99,
        previous_price=120.00,
        url="https://example.com/shoe",
    )
    item = db.get_item(item_id)
    assert item["last_notified_price"] == 89.99


def test_monitor_updates_last_price_always(seeded_db):
    item_id = seeded_db
    with patch("scraper.get_price", return_value=130.00):
        with patch("notifier.send_price_alert", return_value=True):
            monitor.run()

    item = db.get_item(item_id)
    assert item["last_price"] == 130.00
    assert item["last_checked_at"] is not None


def test_monitor_no_alert_if_price_unchanged(seeded_db):
    item_id = seeded_db
    with patch("scraper.get_price", return_value=120.00):
        with patch("notifier.send_price_alert") as mock_notify:
            monitor.run()

    mock_notify.assert_not_called()
    item = db.get_item(item_id)
    assert item["last_notified_price"] == 120.00


def test_monitor_no_alert_if_price_rises(seeded_db):
    item_id = seeded_db
    with patch("scraper.get_price", return_value=150.00):
        with patch("notifier.send_price_alert") as mock_notify:
            monitor.run()

    mock_notify.assert_not_called()


def test_monitor_does_not_update_notified_price_on_failed_send(seeded_db):
    item_id = seeded_db
    with patch("scraper.get_price", return_value=89.99):
        with patch("notifier.send_price_alert", return_value=False):
            monitor.run()

    item = db.get_item(item_id)
    assert item["last_notified_price"] == 120.00


def test_monitor_skips_item_on_scrape_error(seeded_db):
    item_id = seeded_db
    with patch("scraper.get_price", side_effect=ValueError("Could not extract price")):
        with patch("notifier.send_price_alert") as mock_notify:
            monitor.run()

    mock_notify.assert_not_called()
    item = db.get_item(item_id)
    assert item["last_checked_at"] is None


def test_monitor_subsequent_drop_triggers_new_alert(seeded_db):
    item_id = seeded_db
    # First drop: 120 → 89.99
    with patch("scraper.get_price", return_value=89.99):
        with patch("notifier.send_price_alert", return_value=True):
            monitor.run()

    # Second drop: 89.99 → 70.00
    with patch("scraper.get_price", return_value=70.00):
        with patch("notifier.send_price_alert", return_value=True) as mock_notify:
            monitor.run()

    mock_notify.assert_called_once_with(
        user_id="fitz",
        item_name="Air Max 90",
        current_price=70.00,
        previous_price=89.99,
        url="https://example.com/shoe",
    )


def test_monitor_same_low_price_no_repeat_alert(seeded_db):
    # First drop: 120 → 89.99
    with patch("scraper.get_price", return_value=89.99):
        with patch("notifier.send_price_alert", return_value=True):
            monitor.run()

    # Price stays at 89.99 — no second alert
    with patch("scraper.get_price", return_value=89.99):
        with patch("notifier.send_price_alert") as mock_notify:
            monitor.run()

    mock_notify.assert_not_called()
