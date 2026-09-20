"""
adapters.py - turns Swiggy's REAL response shapes into our own MenuItem.

Every field access below is copied from an actual response, captured by
inspect_shapes.py - not from docs, not guessed. If Swiggy changes a
field name tomorrow, this is the one file that breaks and the one file
that needs fixing. agent.py's planner never sees raw Swiggy JSON at all.

Confirmed shapes (2026-09-19):

  get_restaurant_menu ->
    { "restaurant": {"id","name",...},
      "categories": [{"items": [{"id","name","price","isVeg","inStock",
                                  "hasVariants","hasAddons"}]}] }

  search_products ->
    { "products": [{"displayName","variations": [{"skuId","spinId",
        "price":{"offerPrice"},"isInStockAndAvailable","vegClassifier",
        "quantityDescription"}]}] }
"""

from __future__ import annotations

from core.tools import MenuItem
from integrations import sanitize

# A cheap guard, not real understanding: a "biryani" search can return
# a restaurant whose menu also has desserts and drinks, and pick_items
# just grabs whatever's priciest-that-fits - it doesn't know "Gulab
# Jamun" isn't dinner. Excluding these category titles stops the
# obvious version of that mistake. It won't catch everything, and it's
# exactly the kind of judgment call an LLM-based picker (the Groq step)
# should replace properly.
DESSERT_LIKE_CATEGORY = ("dessert", "beverage", "drink", "ice cream", "shake", "juice", "sweet")


def adapt_food_menu(menu: dict, slot: str) -> list[MenuItem]:
    """One restaurant's real menu -> a list of MenuItems for one slot
    (e.g. all of it counts as 'dinner' options).

    Items with no price or no id are skipped rather than crashing -
    a live menu can have malformed or placeholder entries, and one bad
    entry shouldn't take down the whole plan.
    """
    restaurant = menu.get("restaurant") or {}
    restaurant_id = sanitize.clean_id(restaurant.get("id"))
    restaurant_name = sanitize.clean_name(restaurant.get("name"), fallback="")

    items: list[MenuItem] = []
    for category in menu.get("categories") or []:
        title = sanitize.clean_text(category.get("title")).lower()
        if slot == "dinner" and any(word in title for word in DESSERT_LIKE_CATEGORY):
            continue

        for raw in category.get("items") or []:
            item_id = sanitize.clean_id(raw.get("id"))
            price = sanitize.clean_price(raw.get("price"))
            if not item_id or price is None:
                continue

            items.append(MenuItem(
                id=item_id,
                # Names are written by restaurant partners and end up in
                # an LLM prompt and on the approval screen. See sanitize.py.
                name=sanitize.clean_name(raw.get("name")),
                price=price,
                veg=bool(raw.get("isVeg", False)),
                platform="food",
                slot=slot,
                available=bool(raw.get("inStock", 0)),
                ref={
                    "restaurant_id": restaurant_id,
                    "restaurant_name": restaurant_name,
                    # A real cart add needs to know this - an item with
                    # variants/addons can't just be added by id+qty,
                    # it needs a variant chosen first. Not handled yet -
                    # see the note in live_tools.update_food_cart.
                    "has_variants": raw.get("hasVariants", False),
                    "has_addons": raw.get("hasAddons", False),
                },
            ))
    return items


def adapt_instamart_products(result: dict, slot: str) -> list[MenuItem]:
    """Real product search -> MenuItems.

    Each product can come in several pack sizes (a small pack and a
    family pack of the same chips, at different prices) - we treat
    each pack size as its own option, since that's what actually gets
    added to a cart (by skuId), not the product as a whole.
    """
    items: list[MenuItem] = []
    for product in result.get("products") or []:
        name = sanitize.clean_name(product.get("displayName"),
                                   fallback="Unnamed product")

        for v in product.get("variations") or []:
            if not v.get("isInStockAndAvailable", False):
                continue
            price = sanitize.clean_price((v.get("price") or {}).get("offerPrice"))
            if price is None:
                continue

            sku = sanitize.clean_id(v.get("skuId")) or sanitize.clean_id(v.get("spinId"))
            if not sku:
                continue

            size = sanitize.clean_text(v.get("quantityDescription"), limit=24)
            items.append(MenuItem(
                id=sku,
                name=sanitize.clean_name(f"{name} ({size})" if size else name),
                price=price,
                veg=(v.get("vegClassifier") == "VEG_CLASSIFIER_VEG"),
                platform="instamart",
                slot=slot,
                available=True,
                # spin_id is what update_cart actually wants - keep both,
                # cleaned, because they go straight back to Swiggy.
                ref={
                    "sku_id": sanitize.clean_id(v.get("skuId")),
                    "spin_id": sanitize.clean_id(v.get("spinId")),
                },
            ))
    return items