from typing import Annotated, Optional
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list, add_messages]
    # In-progress order the intake agent builds via the cart tools; each line is
    # {name, quantity, spice_level, price}. Replaced wholesale on every cart edit.
    cart: Optional[list]
    # Snapshot of the cart taken at confirmation; its presence routes to fulfillment.
    order: Optional[dict]
