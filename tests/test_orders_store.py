"""Order persistence and history — the contract send_order and the reorder flow rely on."""

import orders_store


def test_get_last_order_is_none_when_empty(temp_orders_db):
    assert orders_store.get_last_order() is None


def test_save_order_returns_id_and_round_trips(temp_orders_db):
    items = [{"name": "Shahi Paneer", "quantity": 2, "price": 10, "spice_level": 3}]

    order_id = orders_store.save_order(items, total=20.0, special_instructions="extra napkins")

    assert isinstance(order_id, int)
    last = orders_store.get_last_order()
    assert last["id"] == order_id
    assert last["items"] == items
    assert last["total"] == 20.0
    assert last["special_instructions"] == "extra napkins"
    assert last["created_at"]  # timestamp is recorded


def test_special_instructions_default_to_none(temp_orders_db):
    orders_store.save_order([{"name": "Garlic Naan", "quantity": 1, "price": 4}], total=4.0)

    assert orders_store.get_last_order()["special_instructions"] is None


def test_get_last_order_returns_most_recent(temp_orders_db):
    orders_store.save_order([{"name": "Butter Roti", "quantity": 1, "price": 3}], total=3.0)
    second_id = orders_store.save_order(
        [{"name": "Mango Lassi", "quantity": 2, "price": 5}], total=10.0
    )

    last = orders_store.get_last_order()
    assert last["id"] == second_id
    assert last["total"] == 10.0
