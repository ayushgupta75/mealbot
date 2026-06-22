"""Server-side order validation against the menu — the guard before dispatch."""

import pytest

from order_validation import OrderValidationError, validate_order

# Real menu items/prices (see menu.json): Shahi Paneer $10, Garlic Naan $4.


def test_valid_order_passes():
    items = [
        {"name": "Shahi Paneer", "quantity": 2, "price": 10},
        {"name": "Garlic Naan", "quantity": 1, "price": 4},
    ]
    validate_order(items, total=24)  # does not raise


def test_empty_order_rejected():
    with pytest.raises(OrderValidationError, match="no items"):
        validate_order([], total=0)


def test_off_menu_item_rejected():
    with pytest.raises(OrderValidationError, match="not on the menu"):
        validate_order([{"name": "Cheeseburger", "quantity": 1, "price": 10}], total=10)


@pytest.mark.parametrize("bad_quantity", [0, -1, 1.5, True])
def test_non_positive_or_non_integer_quantity_rejected(bad_quantity):
    with pytest.raises(OrderValidationError, match="quantity"):
        validate_order([{"name": "Garlic Naan", "quantity": bad_quantity, "price": 4}], total=4)


def test_wrong_unit_price_rejected():
    with pytest.raises(OrderValidationError, match="Price for Garlic Naan"):
        validate_order([{"name": "Garlic Naan", "quantity": 1, "price": 99}], total=99)


def test_total_mismatch_rejected():
    items = [{"name": "Shahi Paneer", "quantity": 2, "price": 10}]
    with pytest.raises(OrderValidationError, match="does not match"):
        validate_order(items, total=15)  # real sum is 20
