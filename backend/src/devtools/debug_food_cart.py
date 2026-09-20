"""
debug_food_cart.py - finds the real field name update_food_cart needs.

Last run: update_food_cart returned success with data: null - no error,
but get_food_cart right after came back empty too. That means our
guessed key ("id") was syntactically fine (it's an array of objects,
matches the schema) but wasn't recognized as the item's identity, so
it silently matched nothing.

This tries a few real candidates against ONE cheap item, one at a time,
flushing between each, and shows exactly what happens. Free and
reversible - it's a cart, not an order.

    python -m devtools.debug_food_cart
"""

import asyncio

# so this runs both as `python -m <pkg>.<mod>` and as `python <pkg>/<mod>.py`
if __package__ in (None, ""):
    import pathlib
    import sys as _sys
    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from integrations.adapters import adapt_food_menu
from integrations.auth import load_token
from integrations.mcp_client import SwiggyMCP
from integrations import live_tools as swiggy

CANDIDATE_KEYS = ["itemId", "menuItemId", "id", "productId"]


async def try_key(mcp, key, address_id, restaurant_id, restaurant_name, item):
    await swiggy.flush_food_cart(mcp)

    cart_items = [{key: item.id, "quantity": 1}]
    print(f"\nTrying key '{key}' -> {cart_items}")

    try:
        result = await swiggy.update_food_cart(
            mcp, restaurant_id=restaurant_id, address_id=address_id,
            cart_items=cart_items, restaurant_name=restaurant_name,
        )
        print(f"  update_food_cart said: {result}")
    except RuntimeError as e:
        print(f"  update_food_cart FAILED: {e}")
        return False

    cart = await swiggy.get_food_cart(mcp, address_id)
    print(f"  get_food_cart says: {cart}")
    return bool(cart and isinstance(cart, dict) and cart.get("items"))


async def main() -> None:
    token = load_token()
    if not token:
        print("No token yet. Run: python -m integrations.auth")
        return

    async with SwiggyMCP(token, servers=("food",)) as mcp:
        addresses = await swiggy.get_addresses(mcp)
        address_id = addresses[0]["id"]

        result = await swiggy.search_restaurants(mcp, address_id, "biryani")
        restaurants = [r for r in result.get("restaurants", [])
                       if r.get("availabilityStatus") == "OPEN"]
        r = restaurants[0]
        rid = r.get("id") or r.get("restaurantId")
        rname = r.get("name")

        menu = await swiggy.get_restaurant_menu(mcp, address_id, rid)
        items = adapt_food_menu(menu, slot="dinner")
        items = [i for i in items
                 if not i.ref.get("has_variants") and not i.ref.get("has_addons")]
        if not items:
            print("No simple (no-variant, no-addon) item found to test with.")
            return

        item = min(items, key=lambda i: i.price)
        print(f"Testing with: {item.name} (id={item.id}) from {rname}")

        for key in CANDIDATE_KEYS:
            if await try_key(mcp, key, address_id, rid, rname, item):
                print(f"\n*** '{key}' WORKED. Update live_tools.py/execute_live.py to use this key. ***")
                await swiggy.flush_food_cart(mcp)
                return

        print("\nNone of these keys worked. Send me every 'update_food_cart said' and")
        print("'get_food_cart says' line above - the real shape might need more than")
        print("one field, e.g. an explicit variantId alongside the item key.")
        await swiggy.flush_food_cart(mcp)


if __name__ == "__main__":
    asyncio.run(main())