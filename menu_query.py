"""Menu lookup tool for the intake agent.

Lets the agent answer "what's vegetarian?", "what's under $5?", "what's
dairy-free / gluten-free?", or "what's not spicy?" from the menu data instead
of reasoning over the prompt text, which is less reliable.
"""

from typing import Optional, Union

from langchain_core.tools import tool

from menu import load_menu

# Each filter maps a customer-facing dietary request to a test over an item's tags.
_DIETARY_FILTERS = {
    "vegetarian": lambda tags: "veg" in tags,
    "vegan": lambda tags: "vegan" in tags,
    "dairy-free": lambda tags: "contains-dairy" not in tags,
    "gluten-free": lambda tags: "contains-gluten" not in tags,
    "mild": lambda tags: "mild" in tags,
}


@tool
def query_menu(
    dietary: Optional[list[str]] = None,
    max_price: Optional[float] = None,
) -> Union[list[dict], str]:
    """Look up menu items matching dietary needs and/or a price ceiling.

    Call this instead of guessing — e.g. "what's vegetarian?", "what's under $5?",
    "anything dairy-free / gluten-free?", "what's not spicy?" (use "mild").

    Args:
        dietary: any of "vegetarian", "vegan", "dairy-free", "gluten-free", "mild".
            All listed filters must match (AND).
        max_price: only include items priced at or below this.

    Returns:
        Matching items as {name, price, tags}, or an error string for an unknown filter.
    """
    requested = dietary or []
    unknown = [name for name in requested if name not in _DIETARY_FILTERS]
    if unknown:
        return f"Unknown dietary filter(s): {unknown}. Supported: {sorted(_DIETARY_FILTERS)}."

    matches = []
    for item in load_menu():
        if max_price is not None and item["price"] > max_price:
            continue
        if all(_DIETARY_FILTERS[name](item["tags"]) for name in requested):
            matches.append({"name": item["name"], "price": item["price"], "tags": item["tags"]})
    return matches
