import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(__file__), "watchlist.db"),
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id    TEXT PRIMARY KEY,
    name  TEXT NOT NULL,
    phone TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             TEXT    NOT NULL REFERENCES users(id),
    url                 TEXT    NOT NULL,
    item_name           TEXT    NOT NULL,
    initial_price       REAL    NOT NULL,
    last_price          REAL    NOT NULL,
    last_notified_price REAL    NOT NULL,
    added_at            TEXT    NOT NULL,
    last_checked_at     TEXT
);

INSERT OR IGNORE INTO users (id, name, phone) VALUES
    ('fitz', 'Fitz', '15163026553'),
    ('sha',  'Sha',  '13184369753');
"""


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as conn:
        conn.executescript(_SCHEMA)


def add_item(user_id, url, item_name, price):
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO items
               (user_id, url, item_name, initial_price, last_price, last_notified_price, added_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, url, item_name, price, price, price, now),
        )
        return cur.lastrowid


def get_all_items():
    with _conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM items").fetchall()]


def get_all_users():
    with _conn() as conn:
        return {r["id"]: dict(r) for r in conn.execute("SELECT * FROM users").fetchall()}


def get_item(item_id):
    with _conn() as conn:
        row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        return dict(row) if row else None


def update_item_price(item_id, last_price, last_checked_at):
    with _conn() as conn:
        conn.execute(
            "UPDATE items SET last_price=?, last_checked_at=? WHERE id=?",
            (last_price, last_checked_at, item_id),
        )


def update_notified_price(item_id, price):
    with _conn() as conn:
        conn.execute(
            "UPDATE items SET last_notified_price=? WHERE id=?",
            (price, item_id),
        )


def remove_item(item_id):
    with _conn() as conn:
        conn.execute("DELETE FROM items WHERE id=?", (item_id,))
