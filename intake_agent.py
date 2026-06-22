from typing import Optional

from langchain_core.language_models import LanguageModelLike
from langgraph.prebuilt import create_react_agent  # type: ignore[no-redef]
from langgraph.prebuilt.chat_agent_executor import AgentState

from cart import add_to_cart, remove_from_cart, update_cart_item, view_cart
from fetch_last_order import fetch_last_order
from menu_query import query_menu
from prompts import INTAKE_PROMPT
from save_order_details_to_graph import save_order_details_to_graph


class IntakeState(AgentState):
    """Agent state extended with the cart and order so the cart tools can read them
    via InjectedState and the values round-trip to the outer graph."""

    cart: Optional[list]
    order: Optional[dict]


def build_intake_agent(model: LanguageModelLike):
    """Build the intake agent that answers menu questions and builds the order cart."""
    tools = [
        query_menu,
        fetch_last_order,
        add_to_cart,
        update_cart_item,
        remove_from_cart,
        view_cart,
        save_order_details_to_graph,
    ]
    # Disable parallel tool calls: cart tools each replace the whole cart, so two in
    # one step would collide on the state channel and both read stale state. One per
    # step keeps every edit reading the latest cart.
    model_with_tools = model.bind_tools(tools, parallel_tool_calls=False)
    return create_react_agent(
        model_with_tools,
        tools=tools,
        prompt=INTAKE_PROMPT,
        state_schema=IntakeState,
    )


def intake_complete(result: dict) -> bool:
    """Return True once the order has been confirmed (snapshotted into state)."""
    return result.get("order") is not None
