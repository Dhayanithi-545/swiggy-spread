"""
execute_live.py - adds the approved plan to your REAL Swiggy cart.

Does NOT place an order. Does NOT spend money. A cart is free and
reversible - open the Swiggy app right after running this and the
items should be sitting there. Clear it anytime with flush_food_cart /
clear_instamart_cart.

ONE field was a guess in the previous version, since Swiggy's docs
list update_food_cart's cartItems as just "array, required" with no
published item shape. Four guessed keys (id, itemId, menuItemId,
productId) all silently matched nothing. The real shape was confirmed
by reading the tool's FULL schema (inspect_update_food_cart.py):
{menu_item_id, quantity} are required, snake_case. Nothing here is
guessed anymore.
"""

from __future__ import annotations

import agent
import live_tools as swiggy
from mcp_client import SwiggyMCP


async def add_plan_to_cart(mcp: SwiggyMCP, plan: agent.Plan, address_id: str) -> dict:
    """Returns Swiggy's raw response for each cart it touched, so you
    can see exactly what it said - success or the exact error."""
    results: dict = {}

    dinner = next((c for c in plan.courses if c.platform == "food" and c.items), None)
    if dinner:
        first_item = dinner.items[0][0]
        restaurant_id = first_item.ref.get("restaurant_id")
        restaurant_name = first_item.ref.get("restaurant_name")

        # Confirmed via inspect_update_food_cart.py's full schema dump:
        # required fields are menu_item_id + quantity. Every candidate
        # we guessed first (id, itemId, menuItemId, productId) silently
        # matched nothing - the real key is snake_case menu_item_id.
        # variants/addons exist in the schema too, in three different
        # shapes - irrelevant here because live_agent.py already filters
        # out anything with hasVariants/hasAddons before it reaches us.
        cart_items = [{"menu_item_id": item.id, "quantity": qty} for item, qty in dinner.items]

        try:
            results["food"] = await swiggy.update_food_cart(
                mcp,
                restaurant_id=restaurant_id,
                address_id=address_id,
                cart_items=cart_items,
                restaurant_name=restaurant_name,
            )
        except RuntimeError as e:
            results["food_error"] = str(e)

    # Instamart's update_cart REPLACES the whole cart on every call -
    # snacks and dessert MUST go in together, in one call, or the
    # second call wipes the first. This is why we gather across courses
    # before calling anything.
    instamart_lines = [
        (item, qty)
        for c in plan.courses if c.platform == "instamart"
        for item, qty in c.items
    ]
    if instamart_lines:
        # Fixed from Swiggy's own error message: "Each item must include
        # spinId from search_products" - it's spinId, not skuId.
        items_payload = [
            {"spinId": item.ref.get("spin_id"), "quantity": qty}
            for item, qty in instamart_lines
        ]
        try:
            results["instamart"] = await swiggy.update_instamart_cart(
                mcp, address_id=address_id, items=items_payload,
            )
        except RuntimeError as e:
            results["instamart_error"] = str(e)

    return results