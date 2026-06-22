from typing import Annotated, Optional

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from cart import cart_total


@tool
def save_order_details_to_graph(
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    special_instructions: Optional[str] = None,
) -> Command:
    """Confirm and place the order. Call this only after the customer has explicitly
    confirmed the cart. It snapshots the current cart as the final order, so build the
    cart with the cart tools first — do not pass items here.

    Args:
        special_instructions: Any special instructions or notes from the customer.
    """
    cart = state.get("cart") or []
    if not cart:
        # No cart yet — stay in intake (no graph=PARENT) so the agent can keep helping.
        return Command(
            update={"messages": [ToolMessage("The cart is empty — nothing to place.", tool_call_id=tool_call_id)]}
        )

    items = [
        {
            "name": line["name"],
            "quantity": line["quantity"],
            "spice_level": line["spice_level"],
            "price": line["price"],
        }
        for line in cart
    ]
    return Command(
        # graph=Command.PARENT propagates the order to the outer StateGraph (so the
        # fulfillment node sees it) and ends the intake agent — this is the handoff.
        graph=Command.PARENT,
        update={
            "order": {
                "items": items,
                "total": cart_total(cart),
                "special_instructions": special_instructions,
            },
            # Required by LangGraph: every tool call must have a matching ToolMessage.
            "messages": [ToolMessage("Order saved.", tool_call_id=tool_call_id)],
        },
    )
