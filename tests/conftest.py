"""Shared fixtures.

`orders_store` reads ORDERS_DB_PATH at call time, so pointing it at a fresh temp
file per test gives every test an isolated, empty database with no cleanup needed.
"""

import pytest


@pytest.fixture
def temp_orders_db(tmp_path, monkeypatch):
    """Point the order store at an isolated, empty SQLite file for the test."""
    db_path = tmp_path / "orders.db"
    monkeypatch.setenv("ORDERS_DB_PATH", str(db_path))
    return db_path
