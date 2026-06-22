"""Single source of truth for the menu.

The menu lives in `menu.json` and is loaded here so that both the intake prompt
(`prompts.py`) and the voice transcription hint (`voice.py`) stay in sync — change
the menu in one place, not three.
"""

import json
from pathlib import Path
from typing import TypedDict

_MENU_PATH = Path(__file__).parent / "menu.json"


class MenuItem(TypedDict):
    name: str
    price: float
    tags: list[str]


def load_menu() -> list[MenuItem]:
    """Load the menu from menu.json."""
    with _MENU_PATH.open(encoding="utf-8") as menu_file:
        return json.load(menu_file)


def menu_item_names() -> list[str]:
    """Return just the item names, e.g. for the speech-to-text vocabulary hint."""
    return [item["name"] for item in load_menu()]


def format_menu_for_prompt() -> str:
    """Render the menu as aligned `- Name   $Price` lines for the intake prompt."""
    items = load_menu()
    name_width = max(len(item["name"]) for item in items)
    return "\n".join(
        f"- {item['name']:<{name_width}}   ${item['price']:g}" for item in items
    )
