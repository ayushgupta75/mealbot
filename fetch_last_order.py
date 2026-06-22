from typing import Union

from langchain_core.tools import tool

import orders_store


@tool
def fetch_last_order() -> Union[dict, str]:
    """Look up the customer's most recent previous order so it can be offered as a quick reorder.

    Call this when the customer wants to repeat a previous order, asks for "the usual",
    or says "same as last time". Read the result back to the customer and let them confirm
    or adjust it before handing off — do not place it automatically.
    """
    last_order = orders_store.get_last_order()
    if last_order is None:
        return "No previous orders found for this customer."
    return {
        "items": last_order["items"],
        "total": last_order["total"],
        "special_instructions": last_order["special_instructions"],
        "placed_at": last_order["created_at"],
    }
