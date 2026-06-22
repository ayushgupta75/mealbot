"""SQLite-backed order history.

Each placed order is persisted here by `send_order`, which makes the store double
as the dispatch record and as the source for the reorder flow (`fetch_last_order`).
The DB path defaults to `orders.db` next to this file; override with ORDERS_DB_PATH.
"""

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_DEFAULT_DB_PATH = Path(__file__).parent / "orders.db"
_CONNECT_TIMEOUT_SECONDS = 5


def _db_path() -> Path:
    return Path(os.environ.get("ORDERS_DB_PATH", _DEFAULT_DB_PATH))


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_db_path(), timeout=_CONNECT_TIMEOUT_SECONDS)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            items_json TEXT NOT NULL,
            total REAL NOT NULL,
            special_instructions TEXT
        )
        """
    )
    return connection


def save_order(
    items: list[dict],
    total: float,
    special_instructions: Optional[str] = None,
) -> int:
    """Persist a placed order and return its row id."""
    with closing(_connect()) as connection, connection:
        cursor = connection.execute(
            "INSERT INTO orders (created_at, items_json, total, special_instructions)"
            " VALUES (?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                json.dumps(items),
                total,
                special_instructions,
            ),
        )
        return cursor.lastrowid


def get_last_order() -> Optional[dict]:
    """Return the most recently placed order, or None if there are none yet."""
    with closing(_connect()) as connection, connection:
        row = connection.execute(
            "SELECT id, created_at, items_json, total, special_instructions"
            " FROM orders ORDER BY id DESC LIMIT 1"
        ).fetchone()

    if row is None:
        return None
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "items": json.loads(row["items_json"]),
        "total": row["total"],
        "special_instructions": row["special_instructions"],
    }
