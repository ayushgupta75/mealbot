"""Outer-graph routing and the REPL exit condition.

Both decide control flow purely from message metadata, so they're tested with
lightweight fakes rather than the live model.
"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END

from agent import route_after_intake
from intake_agent import intake_complete


def _saved_order_message():
    return ToolMessage("Order saved.", name="save_order_details_to_graph", tool_call_id="call-1")


def test_route_to_fulfillment_when_order_saved():
    state = {"messages": [HumanMessage("two naan please"), _saved_order_message()]}
    assert route_after_intake(state) == "fulfillment"


def test_route_to_end_when_order_not_saved():
    state = {"messages": [HumanMessage("hi"), AIMessage("What would you like?")]}
    assert route_after_intake(state) == END


def test_intake_complete_detects_saved_order():
    assert intake_complete({"messages": [_saved_order_message()]}) is True


def test_intake_complete_false_without_saved_order():
    assert intake_complete({"messages": [AIMessage("How spicy, 1 to 5?")]}) is False


def test_route_to_end_on_empty_messages():
    assert route_after_intake({"messages": []}) == END


def test_intake_complete_false_on_empty_messages():
    assert intake_complete({"messages": []}) is False
