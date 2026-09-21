"""
run_live.py - proves the whole wire actually works, against your real
Swiggy account.

    python -m app.run_live

What it does, for real:
  1. Loads your token (run auth.py first if this complains).
  2. Fetches YOUR saved addresses.
  3. Lets you pick one.
  4. Searches real restaurants near that address for a real dish.
  5. Shows you real prices from real restaurants.

What it does NOT do:
  - Add anything to a cart
  - Place any order
  - Spend any money

This is deliberately the boundary for today. Once this prints real
restaurants near your real address, the connection to Swiggy is proven.
Wiring this into agent.py's planner (replacing tools.py's mock catalog)
is the next step, and placing a real order is a separate, deliberate
decision - see PROJECT.md section 6.
"""

import asyncio
import sys

# so this runs both as `python -m <pkg>.<mod>` and as `python <pkg>/<mod>.py`
if __package__ in (None, ""):
    import pathlib
    import sys as _sys
    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# Real Swiggy data contains ₹ and other non-ASCII characters. On Windows,
# stdout defaults to cp1252 (especially when piped), which cannot encode
# them - the first real restaurant list crashed the print. Force UTF-8 and
# never crash on an unprintable character again.
if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from integrations.auth import load_token
from integrations.mcp_client import SwiggyMCP
from integrations import live_tools as swiggy


async def main() -> None:
    token = load_token()
    if not token:
        print("No token yet. Run: python -m integrations.auth")
        return

    async with SwiggyMCP(token, servers=("food",)) as mcp:
        print("Fetching your saved addresses...")
        addresses = await swiggy.get_addresses(mcp)

        if not addresses:
            print("No saved addresses on this account. Add one in the Swiggy app first.")
            return

        from app.run_live_plan import pick_address

        address = pick_address(addresses)
        if not address:
            print("No address chosen - stopping rather than guessing one.")
            return
        address_id = address["id"]

        try:
            query = input("What do you want to search for (e.g. 'biryani')? ").strip()
        except EOFError:
            query = ""
        query = query or "biryani"

        print(f"\nSearching real restaurants for '{query}'...")
        result = await swiggy.search_restaurants(mcp, address_id, query)

        restaurants = [r for r in result.get("restaurants", [])
                       if r.get("availabilityStatus") == "OPEN"]

        if not restaurants:
            print("No open restaurants found for that search right now.")
            return

        print(f"\nFound {len(restaurants)} open restaurants:\n")
        for r in restaurants[:8]:
            print(f"  {r['name']:<30} {r.get('costForTwo', '?'):<12} "
                  f"{r.get('deliveryTimeMinutes', '?')}min  "
                  f"{r.get('avgRating', '?')} stars")

        print("\nThat's real data from your real Swiggy account.")
        print("Nothing was added to a cart. Nothing was ordered.")


if __name__ == "__main__":
    asyncio.run(main())