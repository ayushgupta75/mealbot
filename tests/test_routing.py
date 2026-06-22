"""Outer-graph routing and the REPL exit condition.

Both decide control flow from whether an order has been confirmed into state,
so they're tested directly rather than through the live model.
"""

from langgraph.graph import END

from agent import route_after_intake
from intake_agent import intake_complete

_AN_ORDER = {"items": [{"name": "Garlic Naan", "quantity": 1, "price": 4}], "total": 4}


def test_route_to_fulfillment_when_order_confirmed():
    assert route_after_intake({"order": _AN_ORDER}) == "fulfillment"


def test_route_to_end_when_no_order():
    assert route_after_intake({"order": None}) == END


def test_route_to_end_when_order_absent():
    assert route_after_intake({}) == END


def test_intake_complete_true_with_order():
    assert intake_complete({"order": _AN_ORDER}) is True


def test_intake_complete_false_without_order():
    assert intake_complete({"order": None}) is False
