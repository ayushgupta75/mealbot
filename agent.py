from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from prompts import SYSTEM_PROMPT
from send_order import send_order


def build_agent() -> tuple:
    """Build and return the LangGraph agent and its config."""
    model = ChatAnthropic(model="claude-sonnet-4-6")
    checkpointer = MemorySaver()
    graph = create_react_agent(
        model,
        tools=[send_order],
        checkpointer=checkpointer,
        prompt=SYSTEM_PROMPT,
    )
    config = {"configurable": {"thread_id": "session-1"}}
    return graph, config
