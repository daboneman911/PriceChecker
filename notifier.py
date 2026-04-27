import logging
import httpx

log = logging.getLogger(__name__)


def send_price_alert(user_id, item_name, current_price, previous_price, url):
    """Send iMessage via BlueBubbles. Returns True on success, False on failure."""
    import config

    user = config.USERS.get(user_id)
    if not user:
        raise ValueError(f"Unknown user: {user_id}")

    savings = round(previous_price - current_price, 2)
    pct = round((savings / previous_price) * 100, 1)

    message = (
        f"Price Drop for {user['name']}! 👟\n"
        f"{item_name} is now ${current_price:.2f} (was ${previous_price:.2f})\n"
        f"Save ${savings:.2f} ({pct}% off)\n"
        f"Buy here: {url}"
    )

    payload = {
        "chatGuid": f"iMessage;-;{user['phone']}",
        "message": message,
        "method": "apple-script",
        "password": config.BLUEBUBBLES_PASSWORD,
    }

    try:
        resp = httpx.post(
            f"{config.BLUEBUBBLES_URL}/api/v1/message/text",
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        log.error("Failed to send alert for %s: %s", item_name, e)
        return False
