"""The menu data file is the single source for the prompt and the voice vocabulary hint."""

from menu import format_menu_for_prompt, load_menu, menu_item_names


def test_load_menu_items_have_required_fields():
    menu = load_menu()
    assert menu  # non-empty
    for item in menu:
        assert item["name"]
        assert isinstance(item["price"], (int, float))
        assert isinstance(item["tags"], list)


def test_menu_item_names_match_loaded_menu():
    assert menu_item_names() == [item["name"] for item in load_menu()]


def test_prompt_block_lists_every_item_with_price():
    block = format_menu_for_prompt()
    for item in load_menu():
        assert item["name"] in block
    # prices render without trailing .0 (e.g. "$10", not "$10.0")
    assert "$10" in block
    assert "$10.0" not in block
