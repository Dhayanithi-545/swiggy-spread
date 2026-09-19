"""
execute_live.py - adds the approved plan to your REAL Swiggy cart.

Does NOT place an order. Does NOT spend money. A cart is free and
reversible - open the Swiggy app right after running this and the
items should be sitting there. Clear it anytime with flush_food_cart /
clear_instamart_cart.

ONE guessed field, clearly marked below: Swiggy's docs list
update_food_cart's cartItems as just "array, required" - they don't
publish what fields go INSIDE each item. This uses {"id": ...,
"quantity": ...} because "id" is the exact key Swiggy's own menu
response used for that item's identity. If it's wrong, the tool's
error message will very likely say so directly - run it, read the raw
result this prints, and we fix the key name the same way we found
Instamart's real tool names: by asking the server, not by guessing
twice.
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

        # <-- the one guessed field: "id". See module docstring.
        cart_items = [{"id": item.id, "quantity": qty} for item, qty in dinner.items]

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