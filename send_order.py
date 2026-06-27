import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Optional

from langchain_core.tools import tool

import orders_store
from order_validation import OrderValidationError, validate_order

logger = logging.getLogger(__name__)

_WEBHOOK_TIMEOUT_SECONDS = 5
_WEBHOOK_MAX_ATTEMPTS = 3
_WEBHOOK_BACKOFF_SECONDS = 1.0


def _post_to_webhook(payload: dict) -> None:
    """POST the order to ORDER_WEBHOOK_URL if configured. No-op when unset.

    Webhook delivery is best-effort: the order is already persisted, so a failed
    POST is logged and swallowed rather than failing the whole order.
    """
    url = os.environ.get("ORDER_WEBHOOK_URL")
    if not url:
        return

    body = json.dumps(payload).encode("utf-8")
    for attempt in range(1, _WEBHOOK_MAX_ATTEMPTS + 1):
        request = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=_WEBHOOK_TIMEOUT_SECONDS):
                return
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == _WEBHOOK_MAX_ATTEMPTS:
                logger.warning("Webhook delivery failed after %d attempts: %s", attempt, error)
                return
            time.sleep(_WEBHOOK_BACKOFF_SECONDS * attempt)


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
    try:
        validate_order(items, total)
    except OrderValidationError as error:
        logger.error("Rejected invalid order: %s", error)
        return f"Order could not be placed: {error}"

    order_id = orders_store.save_order(items, total, special_instructions)
    _post_to_webhook(
        {
            "id": order_id,
            "items": items,
            "total": total,
            "special_instructions": special_instructions,
        }
    )

    print("\n" + "=" * 40)
    print(f"ORDER PLACED  (#{order_id})")
    print("=" * 40)
    for item in items:
        line_total = item["quantity"] * item["price"]
        print(f"  {item['quantity']}x {item['name']} @ ${item['price']:.2f} = ${line_total:.2f}")
    print(f"  {'TOTAL':<30} ${total:.2f}")
    if special_instructions:
        print(f"  Notes: {special_instructions}")
    print("=" * 40 + "\n")

    return "Order received."
