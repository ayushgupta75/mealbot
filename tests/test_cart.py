"""The order cart: add, modify, remove, and the running total.

Cart tools read current state via InjectedState, so they're tested by calling the
wrapped func directly with an explicit state dict.
"""

from cart import (
    add_to_cart,
    cart_total,
    format_cart,
    remove_from_cart,
    update_cart_item,
    view_cart,
)


def _add(state, name, quantity, spice_level=1):
    command = add_to_cart.func(
        name=name, quantity=quantity, spice_level=spice_level, state=state, tool_call_id="t"
    )
    return command.update.get("cart", state.get("cart"))


def test_add_looks_up_price_and_sets_line():
    cart = _add({}, "Mango Lassi", 2)
    assert cart == [{"name": "Mango Lassi", "quantity": 2, "spice_level": 1, "price": 5}]


def test_adding_same_item_and_spice_merges_quantity():
    state = {"cart": [{"name": "Garlic Naan", "quantity": 1, "spice_level": 1, "price": 4}]}
    cart = _add(state, "Garlic Naan", 2)
    assert len(cart) == 1
    assert cart[0]["quantity"] == 3


def test_same_item_different_spice_is_a_separate_line():
    state = {"cart": [{"name": "Chana Masala", "quantity": 1, "spice_level": 1, "price": 10}]}
    cart = _add(state, "Chana Masala", 1, spice_level=5)
    assert len(cart) == 2


def test_add_rejects_off_menu_item():
    command = add_to_cart.func(name="Pizza", quantity=1, spice_level=1, state={}, tool_call_id="t")
    assert "cart" not in command.update  # nothing added
    assert "not on the menu" in command.update["messages"][0].content


def test_add_rejects_non_positive_quantity():
    command = add_to_cart.func(name="Garlic Naan", quantity=0, spice_level=1, state={}, tool_call_id="t")
    assert "cart" not in command.update


def test_add_rejects_out_of_range_spice():
    command = add_to_cart.func(name="Shahi Paneer", quantity=1, spice_level=9, state={}, tool_call_id="t")
    assert "cart" not in command.update


def test_update_changes_quantity_and_spice():
    state = {"cart": [{"name": "Shahi Paneer", "quantity": 1, "spice_level": 1, "price": 10}]}
    command = update_cart_item.func(name="Shahi Paneer", state=state, tool_call_id="t", quantity=3, spice_level=4)
    line = command.update["cart"][0]
    assert line["quantity"] == 3
    assert line["spice_level"] == 4


def test_update_missing_item_is_rejected():
    command = update_cart_item.func(name="Palak Paneer", state={"cart": []}, tool_call_id="t", quantity=2)
    assert "cart" not in command.update
    assert "not in the cart" in command.update["messages"][0].content


def test_update_quantity_zero_is_rejected():
    state = {"cart": [{"name": "Butter Roti", "quantity": 2, "spice_level": 1, "price": 3}]}
    command = update_cart_item.func(name="Butter Roti", state=state, tool_call_id="t", quantity=0)
    assert "cart" not in command.update


def test_remove_deletes_the_line():
    state = {"cart": [{"name": "Mango Lassi", "quantity": 1, "spice_level": 1, "price": 5}]}
    command = remove_from_cart.func(name="Mango Lassi", state=state, tool_call_id="t")
    assert command.update["cart"] == []


def test_remove_missing_item_is_rejected():
    command = remove_from_cart.func(name="Mango Lassi", state={"cart": []}, tool_call_id="t")
    assert "cart" not in command.update


def test_running_total_sums_line_totals():
    cart = [
        {"name": "Shahi Paneer", "quantity": 2, "spice_level": 3, "price": 10},
        {"name": "Garlic Naan", "quantity": 1, "spice_level": 1, "price": 4},
    ]
    assert cart_total(cart) == 24


def test_view_cart_reports_total():
    state = {"cart": [{"name": "Garlic Naan", "quantity": 2, "spice_level": 1, "price": 4}]}
    assert "Total: $8" in view_cart.invoke({"state": state})


def test_format_empty_cart():
    assert format_cart([]) == "The cart is empty."
