"""
live_tools.py - the real Swiggy calls, wrapped in plain functions.

FOOD functions below match Swiggy's published schemas exactly:
https://mcp.swiggy.com/builders/docs/reference/food/

INSTAMART is deliberately left as a thin passthrough (call_instamart_tool)
because this project has not fabricated Instamart's tool names - run
discover_tools.py once, read the real names, then fill in typed wrappers
here the same way the Food ones are done. Don't guess API shapes for a
service that touches real orders.

This file has ONE job: talk to Swiggy correctly. It doesn't decide
what to order - agent.py's planner does that. Keeping this boundary
means the planner never needs to know it's talking to Swiggy at all.
"""

from __future__ import annotations

from integrations.mcp_client import SwiggyMCP
from integrations.safety import refuse_if_spending


# ---------------------------------------------------------------- addresses


async def get_addresses(mcp: SwiggyMCP) -> list[dict]:
    """Returns the user's saved delivery addresses. ALWAYS call this
    first and let the user pick - never assume an address."""
    data = await mcp.call("food", "get_addresses", {})
    return data.get("addresses", [])


# ---------------------------------------------------------------- discover


async def search_restaurants(mcp: SwiggyMCP, address_id: str, query: str) -> dict:
    """query is a cuisine or dish, e.g. 'biryani', 'italian', 'desserts'."""
    return await mcp.call("food", "search_restaurants", {
        "addressId": address_id,
        "query": query,
    })


async def get_restaurant_menu(mcp: SwiggyMCP, address_id: str, restaurant_id: str) -> dict:
    return await mcp.call("food", "get_restaurant_menu", {
        "addressId": address_id,
        "restaurantId": restaurant_id,
    })


async def search_menu(mcp: SwiggyMCP, address_id: str, query: str) -> dict:
    """Searches DISHES across restaurants - one call answers "who near me
    serves parotta?". Much better for dish hints than pulling whole menus
    restaurant by restaurant.

    Confirmed live (2026-09-21): required param is just `query`; returns
    { "items": [{name, price, isVeg, menu_item_id, inStock,
                 restaurant_id, restaurant_name, rating?, hasAddons?}],
      "total", "hasMore", "nextOffset" }.
    A vegFilter param exists but its values are undocumented - we filter
    veg on our side instead of guessing.
    """
    return await mcp.call("food", "search_menu", {
        "addressId": address_id,
        "query": query,
    })


async def fetch_food_coupons(mcp: SwiggyMCP, restaurant_id: str, address_id: str) -> dict:
    """Available coupons for one restaurant. Read-only - listing an offer
    costs nothing. Confirmed live (2026-09-21): requires restaurantId +
    addressId; returns { status_message, coupon_sections: [...],
    summary: {total_coupons, applicable_coupons, filter_applied} }.
    Note: agent traffic is filtered to COD-compatible coupons."""
    return await mcp.call("food", "fetch_food_coupons", {
        "restaurantId": str(restaurant_id),
        "addressId": address_id,
    })


# ---------------------------------------------------------------- cart


async def update_food_cart(
    mcp: SwiggyMCP,
    restaurant_id: str,
    address_id: str,
    cart_items: list[dict],
    restaurant_name: str | None = None,
) -> dict:
    """cart_items looks like [{"menu_item_id": "...", "quantity": 2}].
    Add variants/addons only if the item actually has them - check
    get_restaurant_menu's hasVariants/hasAddons fields first."""
    args = {
        "restaurantId": restaurant_id,
        "addressId": address_id,
        "cartItems": cart_items,
    }
    if restaurant_name:
        args["restaurantName"] = restaurant_name
    return await mcp.call("food", "update_food_cart", args)


async def get_food_cart(mcp: SwiggyMCP, address_id: str) -> dict:
    return await mcp.call("food", "get_food_cart", {"addressId": address_id})


async def flush_food_cart(mcp: SwiggyMCP) -> dict:
    """Empties the cart. Call this before switching to a different
    restaurant - Food carts are per-restaurant, switching without
    flushing silently drops the old items."""
    return await mcp.call("food", "flush_food_cart", {})


# ---------------------------------------------------------------- order
#
# These two spend real money. Both refuse to run unless the unlock env
# var in safety.py is set, and mcp_client.call() refuses them again on
# the wire even if this check were removed. No path in this project
# calls either of them.


async def place_food_order(
    mcp: SwiggyMCP,
    address_id: str,
    payment_method: str | None = None,
    note_to_restaurant: str | None = None,
) -> dict:
    """Places the order that's currently in the cart.

    Disabled. Raises safety.OrderingDisabled unless explicitly unlocked -
    Spread's job ends at a filled cart.

    If you ever do unlock it: COD only, unless you've built the UPI
    polling loop (check_payment_status -> confirm_order) described in
    Swiggy's docs. This function does not do that polling for you.
    """
    refuse_if_spending("place_food_order", context="live_tools")
    args = {"addressId": address_id}
    if payment_method:
        args["paymentMethod"] = payment_method
    if note_to_restaurant:
        args["noteToRestaurant"] = note_to_restaurant
    return await mcp.call("food", "place_food_order", args)


# ---------------------------------------------------------------- instamart


async def search_products(mcp: SwiggyMCP, address_id: str, query: str) -> dict:
    """query is a product name, e.g. 'chips', 'ice cream', 'paneer'."""
    return await mcp.call("instamart", "search_products", {
        "addressId": address_id,
        "query": query,
    })


async def get_instamart_cart(mcp: SwiggyMCP) -> dict:
    return await mcp.call("instamart", "get_cart", {})


async def update_instamart_cart(
    mcp: SwiggyMCP, address_id: str, items: list[dict]
) -> dict:
    """IMPORTANT: unlike Food's update_food_cart (which adds/merges),
    Instamart's update_cart REPLACES the entire cart every time. If
    you're adding snacks AND dessert from Instamart, send both sets of
    items together in one call - calling it twice will wipe the first
    set out. items look like [{"spinId": "...", "quantity": 2}]; the key
    is spinId, not skuId, per Swiggy's own error message ("Each item must
    include spinId from search_products")."""
    return await mcp.call("instamart", "update_cart", {
        "selectedAddressId": address_id,
        "items": items,
    })


async def clear_instamart_cart(mcp: SwiggyMCP) -> dict:
    return await mcp.call("instamart", "clear_cart", {})


async def checkout_instamart(
    mcp: SwiggyMCP, address_id: str, payment_method: str | None = None
) -> dict:
    """Places the real Instamart order.

    Disabled, exactly like place_food_order. Same reason.
    """
    refuse_if_spending("checkout", context="live_tools")
    args = {"addressId": address_id}
    if payment_method:
        args["paymentMethod"] = payment_method
    return await mcp.call("instamart", "checkout", args)


# ---------------------------------------------------------------- fallback


async def call_instamart_tool(mcp: SwiggyMCP, tool_name: str, arguments: dict) -> dict:
    """Passthrough for the less-common Instamart tools (your_go_to_items,
    get_orders, track_order, get_delivery_status) that don't need a
    typed wrapper yet - the ones above cover the main planning flow.

    A hand-typed tool name gets no special trust: mcp.call() still runs
    it past safety.refuse_if_spending(), so 'checkout' typed in here is
    refused exactly like the typed wrapper would refuse it.
    """
    return await mcp.call("instamart", tool_name, arguments)