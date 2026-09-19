"""
inspect_shapes.py - see the REAL response shape before we build
adapters.py against it.

We already know search_restaurants's real shape (run_live.py printed
it: name, costForTwo, deliveryTimeMinutes, avgRating, availabilityStatus).
We do NOT yet know get_restaurant_menu's or search_products's real
shape - Swiggy's docs give input parameters, not output structure.

Run this once:

    python inspect_shapes.py

It fetches one real restaurant's menu and one real product search, and
pretty-prints the raw JSON. Paste that output back and adapters.py gets
written against confirmed field names - not guesses.
"""

import asyncio
import json

from auth import load_token
from mcp_client import SwiggyMCP
import live_tools as swiggy


async def main() -> None:
    token = load_token()
    if not token:
        print("No token yet. Run: python auth.py")
        return

    async with SwiggyMCP(token, servers=("food", "instamart")) as mcp:
        addresses = await swiggy.get_addresses(mcp)
        if not addresses:
            print("No saved addresses. Add one in the Swiggy app first.")
            return

        for i, a in enumerate(addresses):
            print(f"  [{i}] {a.get('addressLine')}")
        idx = int(input("Pick an address number: ").strip() or "0")
        address_id = addresses[idx]["id"]

        # --- Food: one restaurant's real menu shape ---
        print("\nSearching restaurants for 'biryani' to pick one for menu inspection...")
        rest_result = await swiggy.search_restaurants(mcp, address_id, "biryani")
        restaurants = rest_result.get("restaurants", [])
        if restaurants:
            target = restaurants[0]
            rid = target.get("id") or target.get("restaurantId")
            print(f"Fetching real menu for: {target.get('name')} (id={rid})")
            menu = await swiggy.get_restaurant_menu(mcp, address_id, rid)
            print("\n" + "=" * 60)
            print("  RAW get_restaurant_menu RESPONSE (first 2000 chars)")
            print("=" * 60)
            print(json.dumps(menu, indent=2)[:2000])
        else:
            print("No restaurants found to inspect a menu from.")

        # --- Instamart: real product search shape ---
        print("\nSearching Instamart products for 'chips'...")
        products = await swiggy.search_products(mcp, address_id, "chips")
        print("\n" + "=" * 60)
        print("  RAW search_products RESPONSE (first 2000 chars)")
        print("=" * 60)
        print(json.dumps(products, indent=2)[:2000])


if __name__ == "__main__":
    asyncio.run(main())