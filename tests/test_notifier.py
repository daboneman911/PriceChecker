import sys
import pytest
from unittest.mock import patch, MagicMock
import notifier


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.BLUEBUBBLES_URL = "http://192.168.1.100:1234"
    cfg.BLUEBUBBLES_PASSWORD = "testpass"
    cfg.USERS = {
        "fitz": {"name": "Fitz", "phone": "+15163026553"},
        "sha": {"name": "Sha", "phone": "+13184369753"},
    }
    with patch.dict(sys.modules, {"config": cfg}):
        yield cfg


def test_send_alert_returns_true_on_success(mock_config):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        result = notifier.send_price_alert(
            user_id="fitz",
            item_name="Air Max 90",
            current_price=89.99,
            previous_price=120.00,
            url="https://example.com/airmax",
        )

    assert result is True
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    payload = call_kwargs.kwargs["json"]
    assert payload["chatGuid"] == "iMessage;-;+15163026553"
    assert "89.99" in payload["message"]
    assert "120.00" in payload["message"]
    assert "https://example.com/airmax" in payload["message"]
    assert call_kwargs.kwargs["params"]["password"] == "testpass"


def test_send_alert_includes_savings(mock_config):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        notifier.send_price_alert(
            user_id="fitz",
            item_name="Air Max 90",
            current_price=89.99,
            previous_price=120.00,
            url="https://example.com/airmax",
        )

    payload = mock_post.call_args.kwargs["json"]
    assert "30.01" in payload["message"]   # savings amount: 120.00 - 89.99
    assert "25.0%" in payload["message"]   # percentage off


def test_send_alert_returns_false_on_http_error(mock_config):
    with patch("httpx.post", side_effect=Exception("connection refused")):
        result = notifier.send_price_alert(
            user_id="fitz",
            item_name="Air Max 90",
            current_price=89.99,
            previous_price=120.00,
            url="https://example.com/airmax",
        )

    assert result is False


def test_send_alert_raises_for_unknown_user(mock_config):
    with pytest.raises(ValueError, match="Unknown user"):
        notifier.send_price_alert(
            user_id="unknown",
            item_name="Shoe",
            current_price=50.00,
            previous_price=100.00,
            url="https://example.com",
        )


def test_send_alert_targets_sha(mock_config):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        notifier.send_price_alert(
            user_id="sha",
            item_name="Yeezy",
            current_price=200.00,
            previous_price=250.00,
            url="https://example.com/yeezy",
        )

    payload = mock_post.call_args.kwargs["json"]
    assert payload["chatGuid"] == "iMessage;-;+13184369753"
    assert "Sha" in payload["message"]
