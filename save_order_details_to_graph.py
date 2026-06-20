from typing import Annotated, Optional

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command


@tool
def save_order_details_to_graph(
    items: list[dict],
    total: float,
    tool_call_id: Annotated[str, InjectedToolCallId],
    special_instructions: Optional[str] = None,
) -> Command:
    """Save the confirmed order to state so the fulfillment agent can place it.
    Only call this after the user has explicitly confirmed the order.

    Args:
        items: List of ordered items, each with 'name', 'quantity', 'spice_level', and 'price' (unit price).
        total: Total price of the entire order.
        special_instructions: Any special instructions from the customer.
    """
    return Command(
        update={
            "order": {
                "items": items,
                "total": total,
                "special_instructions": special_instructions,
            },
            # Required by LangGraph: every tool call must have a matching ToolMessage
            "messages": [ToolMessage("Order saved.", tool_call_id=tool_call_id)],
        },
    )
