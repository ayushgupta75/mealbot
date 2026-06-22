"""Validate a confirmed order against the menu before it is dispatched.

The model assembles item prices and the order total during intake and can get
them wrong. This is the server-side check that a bad order never gets persisted
or sent: every item must be on the menu, quantities must be positive, and the
unit prices and total must match the menu — not whatever the model computed.
"""

from menu import load_menu

_PRICE_TOLERANCE = 0.01  # orders are whole-dollar priced; this absorbs float noise


class OrderValidationError(ValueError):
    """Raised when a confirmed order does not match the menu."""


def validate_order(items: list[dict], total: float) -> None:
    """Validate items and total against the menu. Raise OrderValidationError if anything is off."""
    if not items:
        raise OrderValidationError("Order has no items.")

    menu_prices = {item["name"]: item["price"] for item in load_menu()}
    expected_total = 0.0

    for item in items:
        name = item.get("name")
        if name not in menu_prices:
            raise OrderValidationError(f"'{name}' is not on the menu.")

        quantity = item.get("quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise OrderValidationError(f"Invalid quantity for {name}: {quantity!r}.")

        menu_price = menu_prices[name]
        if abs(item.get("price", 0) - menu_price) > _PRICE_TOLERANCE:
            raise OrderValidationError(
                f"Price for {name} is {item.get('price')!r}, menu price is {menu_price}."
            )
        expected_total += quantity * menu_price

    if abs(expected_total - total) > _PRICE_TOLERANCE:
        raise OrderValidationError(
            f"Total {total} does not match the item sum {expected_total}."
        )
