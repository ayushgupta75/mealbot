"""The order cart and the tools the intake agent uses to build it.

The cart lives in graph state (`state["cart"]`) so it survives across REPL turns
and is the single source of truth for the order — quantities and the running
total come from here, not from the model re-deriving them from the conversation.
Each line is {name, quantity, spice_level, price}; price is the menu price, looked
up here rather than supplied by the model.
"""

from typing import Annotated, Optional

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from menu import load_menu

MIN_SPICE_LEVEL = 1
MAX_SPICE_LEVEL = 5


def _menu_index() -> dict:
    return {item["name"]: item for item in load_menu()}


def cart_total(cart: list[dict]) -> float:
    """Running total of the cart from menu prices."""
    return sum(line["quantity"] * line["price"] for line in cart)


def format_cart(cart: list[dict]) -> str:
    """Human-readable cart with a running total, used in tool confirmations."""
    if not cart:
        return "The cart is empty."
    lines = [
        f"- {line['quantity']}x {line['name']} (spice {line['spice_level']}) "
        f"@ ${line['price']:g} = ${line['quantity'] * line['price']:g}"
        for line in cart
    ]
    lines.append(f"Total: ${cart_total(cart):g}")
    return "\n".join(lines)


def _is_positive_int(value) -> bool:
    # bool is a subclass of int; reject True/False as quantities.
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _current_cart(state: dict) -> list[dict]:
    # Copy so we never mutate the existing state value in place.
    return [dict(line) for line in (state.get("cart") or [])]


def _updated(cart: list[dict], message: str, tool_call_id: str) -> Command:
    return Command(
        update={
            "cart": cart,
            "messages": [ToolMessage(f"{message}\n{format_cart(cart)}", tool_call_id=tool_call_id)],
        }
    )


def _rejected(message: str, tool_call_id: str) -> Command:
    # No cart change; just tell the agent why so it can ask the customer.
    return Command(update={"messages": [ToolMessage(message, tool_call_id=tool_call_id)]})


@tool
def add_to_cart(
    name: str,
    quantity: int,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    spice_level: int = 1,
) -> Command:
    """Add a menu item to the cart, or increase its quantity if the same item and
    spice level are already there. Use the exact menu name (check with query_menu if unsure).
    spice_level is 1 (no spice) to 5 (spiciest); default 1 for items where spice doesn't apply.
    """
    menu = _menu_index()
    if name not in menu:
        return _rejected(f"'{name}' is not on the menu.", tool_call_id)
    if not _is_positive_int(quantity):
        return _rejected(f"Quantity must be a positive whole number, got {quantity!r}.", tool_call_id)
    if not MIN_SPICE_LEVEL <= spice_level <= MAX_SPICE_LEVEL:
        return _rejected(
            f"Spice level must be {MIN_SPICE_LEVEL}-{MAX_SPICE_LEVEL}, got {spice_level!r}.",
            tool_call_id,
        )

    cart = _current_cart(state)
    for line in cart:
        if line["name"] == name and line["spice_level"] == spice_level:
            line["quantity"] += quantity
            break
    else:
        cart.append(
            {"name": name, "quantity": quantity, "spice_level": spice_level, "price": menu[name]["price"]}
        )
    return _updated(cart, f"Added {quantity}x {name}.", tool_call_id)


@tool
def update_cart_item(
    name: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    quantity: Optional[int] = None,
    spice_level: Optional[int] = None,
) -> Command:
    """Change the quantity and/or spice level of an item already in the cart.
    To take an item out entirely, use remove_from_cart instead of setting quantity to 0.
    """
    if quantity is not None and not _is_positive_int(quantity):
        return _rejected(
            f"Quantity must be a positive whole number, got {quantity!r} "
            "(use remove_from_cart to delete an item).",
            tool_call_id,
        )
    if spice_level is not None and not MIN_SPICE_LEVEL <= spice_level <= MAX_SPICE_LEVEL:
        return _rejected(
            f"Spice level must be {MIN_SPICE_LEVEL}-{MAX_SPICE_LEVEL}, got {spice_level!r}.",
            tool_call_id,
        )

    cart = _current_cart(state)
    matching = [line for line in cart if line["name"] == name]
    if not matching:
        return _rejected(f"{name} is not in the cart.", tool_call_id)
    for line in matching:
        if quantity is not None:
            line["quantity"] = quantity
        if spice_level is not None:
            line["spice_level"] = spice_level
    return _updated(cart, f"Updated {name}.", tool_call_id)


@tool
def remove_from_cart(
    name: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Remove an item from the cart entirely."""
    cart = _current_cart(state)
    remaining = [line for line in cart if line["name"] != name]
    if len(remaining) == len(cart):
        return _rejected(f"{name} is not in the cart.", tool_call_id)
    return _updated(remaining, f"Removed {name}.", tool_call_id)


@tool
def view_cart(state: Annotated[dict, InjectedState]) -> str:
    """Show the current cart contents and running total."""
    return format_cart(state.get("cart") or [])
