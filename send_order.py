import json
from typing import Optional

from langchain_core.tools import tool


@tool
def send_order(
    items: list[dict],
    total: float,
    special_instructions: Optional[str] = None,
) -> str:
    """Place a confirmed food order. Only call this after the user has explicitly confirmed.

    Args:
        items: List of ordered items, each with 'name', 'quantity', and 'price' (unit price per item, not line total).
        total: Total price of the entire order.
        special_instructions: Any special instructions or notes from the customer.
    """
    print("\n" + "=" * 40)
    print("ORDER PLACED")
    print("=" * 40)
    for item in items:
        line_total = item["quantity"] * item["price"]
        print(f"  {item['quantity']}x {item['name']} @ ${item['price']:.2f} = ${line_total:.2f}")
    print(f"  {'TOTAL':<30} ${total:.2f}")
    if special_instructions:
        print(f"  Notes: {special_instructions}")
    print("=" * 40 + "\n")

    return "Order received."
