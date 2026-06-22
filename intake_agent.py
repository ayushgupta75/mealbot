from langchain_core.language_models import LanguageModelLike
from langgraph.prebuilt import create_react_agent  # type: ignore[no-redef]

from fetch_last_order import fetch_last_order
from prompts import INTAKE_PROMPT
from save_order_details_to_graph import save_order_details_to_graph


def build_intake_agent(model: LanguageModelLike):
    """Build the intake agent that collects order details from the customer."""
    return create_react_agent(
        model,
        tools=[fetch_last_order, save_order_details_to_graph],
        prompt=INTAKE_PROMPT,
    )


def intake_complete(result: dict) -> bool:
    """Return True if the intake agent has finished collecting the order."""
    return any(
        getattr(m, "name", None) == "save_order_details_to_graph"
        for m in result["messages"]
    )
