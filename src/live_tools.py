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

from mcp_client import SwiggyMCP


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
# NOT wired into run_live.py's default path. Calling this places a real
# order with real money on the logged-in Swiggy account. Read the
# PROJECT.md section on scope before ever calling this outside a
# deliberate, manual test.


async def place_food_order(
    mcp: SwiggyMCP,
    address_id: str,
    payment_method: str | None = None,
    note_to_restaurant: str | None = None,
) -> dict:
    """Places the order that's currently in the cart. COD only unless
    you've built the UPI polling loop (check_payment_status ->
    confirm_order) described in Swiggy's docs - this function does not
    do that polling for you."""
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
    set out. items look like [{"product_id": "...", "quantity": 2}] -
    confirm exact keys once you've seen a real search_products result."""
    return await mcp.call("instamart", "update_cart", {
        "selectedAddressId": address_id,
        "items": items,
    })


async def clear_instamart_cart(mcp: SwiggyMCP) -> dict:
    return await mcp.call("instamart", "clear_cart", {})


async def checkout_instamart(
    mcp: SwiggyMCP, address_id: str, payment_method: str | None = None
) -> dict:
    """Places the real Instamart order. Same caution as
    place_food_order - not wired into any default path."""
    args = {"addressId": address_id}
    if payment_method:
        args["paymentMethod"] = payment_method
    return await mcp.call("instamart", "checkout", args)


# ---------------------------------------------------------------- fallback


async def call_instamart_tool(mcp: SwiggyMCP, tool_name: str, arguments: dict) -> dict:
    """Passthrough for the less-common Instamart tools (your_go_to_items,
    get_orders, track_order, get_delivery_status) that don't need a
    typed wrapper yet - the ones above cover the main planning flow."""
    return await mcp.call("instamart", tool_name, arguments)