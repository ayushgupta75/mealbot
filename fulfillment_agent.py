from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent  # type: ignore[no-redef]

from prompts import FULFILLMENT_PROMPT
from send_order import send_order
from state import State


def build_fulfillment_agent(model: LanguageModelLike):
    """Build the fulfillment agent that executes the confirmed order."""
    agent = create_react_agent(model, tools=[send_order], prompt=FULFILLMENT_PROMPT)

    def fulfillment_node(state: State) -> dict:
        # Set by the save_order_details_to_graph tool (via graph=Command.PARENT)
        order = state["order"]

        result = agent.invoke({
            "messages": [HumanMessage(content=f"Place this order:\n{order}")]
        })
        return {"messages": result["messages"]}

    return fulfillment_node
