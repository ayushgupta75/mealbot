from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, START

from fulfillment_agent import build_fulfillment_agent
from intake_agent import build_intake_agent
from state import State


def build_graph() -> tuple:
    """Wire the intake and fulfillment agents into a LangGraph and return it with config."""
    model = ChatAnthropic(model="claude-sonnet-4-6")

    def route_after_intake(state: State) -> str:
        # Route to fulfillment if save_order_details_to_graph was called this turn
        for msg in reversed(state["messages"]):
            if getattr(msg, "name", None) == "save_order_details_to_graph":
                return "fulfillment"
        return END

    graph_builder = StateGraph(State)
    graph_builder.add_node("intake", build_intake_agent(model))
    graph_builder.add_node("fulfillment", build_fulfillment_agent(model))
    graph_builder.add_edge(START, "intake")
    graph_builder.add_conditional_edges("intake", route_after_intake)
    graph_builder.add_edge("fulfillment", END)

    graph = graph_builder.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "session-1"}}
    return graph, config
