#!/usr/bin/env python3
import logging
from datetime import datetime, timezone
import db
import scraper
import notifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def run():
    db.init_db()
    items = db.get_all_items()
    log.info("Checking %d item(s)", len(items))

    for item in items:
        url = item["url"]
        item_id = item["id"]
        log.info("  [%s] %s", item["item_name"], url)

        try:
            current_price = scraper.get_price(url)
        except Exception as e:
            log.error("  Failed to scrape %s: %s", url, e)
            continue

        now = datetime.now(timezone.utc).isoformat()
        db.update_item_price(item_id, current_price, now)
        log.info(
            "  $%.2f (notified at $%.2f)",
            current_price,
            item["last_notified_price"],
        )

        if current_price < item["last_notified_price"]:
            log.info("  Price drop detected — sending alert")
            success = notifier.send_price_alert(
                user_id=item["user_id"],
                item_name=item["item_name"],
                current_price=current_price,
                previous_price=item["last_notified_price"],
                url=url,
            )
            if success:
                db.update_notified_price(item_id, current_price)
                log.info("  Alert sent, notified_price → $%.2f", current_price)
            else:
                log.warning("  Alert failed — will retry next run")


if __name__ == "__main__":
    run()
