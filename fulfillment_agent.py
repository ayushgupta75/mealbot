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
        # Extract order from save_order_details_to_graph tool call args in messages
        order = None
        for msg in reversed(state["messages"]):
            if hasattr(msg, "tool_calls"):
                for tc in msg.tool_calls:
                    if tc["name"] == "save_order_details_to_graph":
                        order = tc["args"]
                        break
            if order:
                break

        result = agent.invoke({
            "messages": [HumanMessage(content=f"Place this order:\n{order}")]
        })
        return {"messages": result["messages"]}

    return fulfillment_node
