"""Menu lookup tool — the reliable answer to dietary/price questions."""

from menu_query import query_menu


def _names(results):
    return {item["name"] for item in results}


def test_no_filters_returns_full_menu():
    assert len(query_menu.invoke({})) == 10


def test_max_price_filters_to_cheaper_items():
    results = query_menu.invoke({"max_price": 5})
    assert _names(results) == {"Garlic Naan", "Butter Roti", "Mango Lassi"}


def test_vegan_filter():
    # Only the dairy-free, plant-based mains are tagged vegan.
    assert _names(query_menu.invoke({"dietary": ["vegan"]})) == {"Steamed Rice", "Chana Masala"}


def test_gluten_free_excludes_breads_and_gulab_jamun():
    results = _names(query_menu.invoke({"dietary": ["gluten-free"]}))
    assert "Garlic Naan" not in results
    assert "Butter Roti" not in results
    assert "Gulab Jamun (2 pcs)" not in results
    assert "Steamed Rice" in results


def test_mild_answers_not_spicy():
    results = _names(query_menu.invoke({"dietary": ["mild"]}))
    assert "Chana Masala" not in results  # the one dish not tagged mild
    assert "Shahi Paneer" in results


def test_combined_filters_are_anded():
    # vegan AND under $11 still includes both vegan mains (both are $10).
    results = _names(query_menu.invoke({"dietary": ["vegan"], "max_price": 11}))
    assert results == {"Steamed Rice", "Chana Masala"}


def test_unknown_filter_returns_error_string():
    result = query_menu.invoke({"dietary": ["keto"]})
    assert isinstance(result, str)
    assert "keto" in result
