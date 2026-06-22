"""The tools the agents call: order handoff, dispatch, and reorder lookup."""

import urllib.error
from unittest.mock import patch

from langchain_core.messages import ToolMessage
from langgraph.types import Command

import orders_store
import send_order as send_order_module
from fetch_last_order import fetch_last_order
from save_order_details_to_graph import save_order_details_to_graph
from send_order import send_order


def test_save_order_details_propagates_to_parent_graph():
    # InjectedToolCallId means the tool must be invoked with a full ToolCall;
    # the tool_call_id is taken from the call's "id", not from args.
    command = save_order_details_to_graph.invoke(
        {
            "name": "save_order_details_to_graph",
            "args": {
                "items": [{"name": "Chana Masala", "quantity": 1, "price": 10, "spice_level": 4}],
                "total": 10.0,
            },
            "id": "call-1",
            "type": "tool_call",
        }
    )

    assert isinstance(command, Command)
    # Without graph=PARENT the order would never reach the fulfillment node.
    assert command.graph == Command.PARENT
    assert command.update["order"]["total"] == 10.0
    # Every tool call needs a matching ToolMessage or LangGraph rejects the turn.
    assert any(isinstance(m, ToolMessage) for m in command.update["messages"])


def test_send_order_persists_and_returns_receipt(temp_orders_db):
    result = send_order.invoke(
        {
            "items": [{"name": "Dal Makhani", "quantity": 1, "price": 10}],
            "total": 10.0,
        }
    )

    assert result == "Order received."
    assert orders_store.get_last_order()["total"] == 10.0


def test_send_order_skips_webhook_when_unset(temp_orders_db, monkeypatch):
    monkeypatch.delenv("ORDER_WEBHOOK_URL", raising=False)
    with patch("send_order.urllib.request.urlopen") as mock_urlopen:
        send_order.invoke(
            {"items": [{"name": "Butter Roti", "quantity": 1, "price": 3}], "total": 3.0}
        )
    mock_urlopen.assert_not_called()


def test_send_order_posts_to_webhook_when_set(temp_orders_db, monkeypatch):
    monkeypatch.setenv("ORDER_WEBHOOK_URL", "https://example.test/orders")
    with patch("send_order.urllib.request.urlopen") as mock_urlopen:
        send_order.invoke(
            {"items": [{"name": "Garlic Naan", "quantity": 2, "price": 4}], "total": 8.0}
        )
    mock_urlopen.assert_called_once()


def test_send_order_survives_webhook_failure(temp_orders_db, monkeypatch):
    # A failing webhook must not break the order — it's already persisted.
    monkeypatch.setenv("ORDER_WEBHOOK_URL", "https://example.test/orders")
    monkeypatch.setattr(send_order_module.time, "sleep", lambda _seconds: None)  # no real backoff wait
    with patch(
        "send_order.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ) as mock_urlopen:
        result = send_order.invoke(
            {"items": [{"name": "Mango Lassi", "quantity": 1, "price": 5}], "total": 5.0}
        )

    assert result == "Order received."
    assert orders_store.get_last_order()["total"] == 5.0
    # Retried up to the configured limit before giving up.
    assert mock_urlopen.call_count == send_order_module._WEBHOOK_MAX_ATTEMPTS


def test_send_order_stops_retrying_after_first_success(temp_orders_db, monkeypatch):
    monkeypatch.setenv("ORDER_WEBHOOK_URL", "https://example.test/orders")
    with patch("send_order.urllib.request.urlopen") as mock_urlopen:
        send_order.invoke(
            {"items": [{"name": "Mango Lassi", "quantity": 1, "price": 5}], "total": 5.0}
        )
    # Succeeds on the first attempt, so no retries.
    assert mock_urlopen.call_count == 1


def test_send_order_rejects_invalid_order_without_persisting(temp_orders_db):
    # Off-menu item: must be refused, and nothing should be written to the store.
    result = send_order.invoke(
        {"items": [{"name": "Cheeseburger", "quantity": 1, "price": 10}], "total": 10.0}
    )

    assert result.startswith("Order could not be placed")
    assert orders_store.get_last_order() is None


def test_fetch_last_order_message_when_empty(temp_orders_db):
    assert fetch_last_order.invoke({}) == "No previous orders found for this customer."


def test_fetch_last_order_returns_previous_order(temp_orders_db):
    orders_store.save_order(
        [{"name": "Palak Paneer", "quantity": 1, "price": 10}], total=10.0, special_instructions="mild"
    )

    result = fetch_last_order.invoke({})

    assert result["total"] == 10.0
    assert result["special_instructions"] == "mild"
    assert result["placed_at"]
