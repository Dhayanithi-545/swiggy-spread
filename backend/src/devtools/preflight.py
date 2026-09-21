"""
preflight.py - checks the whole live wire, read-only, before you trust it.

    python -m devtools.preflight

Run this ONCE after auth, before run_live_plan. It answers, in order,
every question that would otherwise fail confusingly in the middle of a
real plan:

  1. Is there a token, and does Swiggy accept it?
  2. Do both servers (food, instamart) open a session?
  3. Do the tool names this project calls actually exist on the server?
     (They were confirmed against Swiggy's published docs, but docs and
     production drift - this asks the server itself.)
  4. Does get_addresses return your real addresses?
  5. Does one real restaurant search and one real product search come
     back in the shape adapters.py expects?

Nothing here writes to a cart. Nothing here can order - the same
safety.py deny-list sits under every call this script makes.
"""

import asyncio
import sys

# so this runs both as `python -m <pkg>.<mod>` and as `python <pkg>/<mod>.py`
if __package__ in (None, ""):
    import pathlib
    import sys as _sys
    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# Real Swiggy data contains ₹ etc.; Windows' cp1252 stdout crashes on them.
if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from integrations import live_tools as swiggy
from integrations.adapters import adapt_food_menu, adapt_instamart_products
from integrations.auth import load_token
from integrations.mcp_client import SwiggyMCP

# Every tool the live path actually calls, per server. If one of these is
# missing on the real server, run_live_plan WILL fail - better to hear it
# here, named, than as a RuntimeError mid-plan.
EXPECTED_TOOLS = {
    "food": ("get_addresses", "search_restaurants", "get_restaurant_menu",
             "update_food_cart", "get_food_cart", "flush_food_cart"),
    "instamart": ("search_products", "update_cart", "get_cart", "clear_cart"),
}

OK = "  [ok]  "
BAD = "  [FAIL]"


def report(ok: bool, label: str, detail: str = "") -> bool:
    print(f"{OK if ok else BAD} {label}" + (f"  -> {detail}" if detail else ""))
    return ok


async def main() -> None:
    print("\nSpread preflight - read-only, touches nothing.\n")
    failures = 0

    # 1. token
    token = load_token()
    if not report(bool(token), "token file exists",
                  "" if token else "run: python -m integrations.auth"):
        return

    # 2. sessions
    try:
        async with SwiggyMCP(token, servers=("food", "instamart")) as mcp:
            report(True, "sessions open on food + instamart")

            # 3. tool names, asked of the server itself
            for server, expected in EXPECTED_TOOLS.items():
                tools = await mcp.list_tools(server)
                names = {t["name"] for t in tools}
                missing = [t for t in expected if t not in names]
                if not report(not missing, f"{server}: all expected tools exist",
                              f"missing {missing}; server has {sorted(names)}"
                              if missing else f"{len(names)} tools"):
                    failures += 1

            # 4. addresses
            addresses = await swiggy.get_addresses(mcp)
            if not report(bool(addresses), "get_addresses returns addresses",
                          f"{len(addresses)} found" if addresses
                          else "none - add one in the Swiggy app first"):
                failures += 1
                print("\nCan't go further without an address.")
                return
            address_id = addresses[0].get("id")
            if not report(bool(address_id), "address rows carry an 'id' field",
                          str(sorted(addresses[0])) if not address_id else ""):
                failures += 1
                return

            # 5. one real search each way, through the real adapters
            result = await swiggy.search_restaurants(mcp, address_id, "biryani")
            open_ones = [r for r in (result.get("restaurants") or [])
                         if r.get("availabilityStatus") == "OPEN"]
            if not report(bool(open_ones), "restaurant search returns OPEN restaurants",
                          f"{len(open_ones)} open" if open_ones
                          else f"keys seen: {sorted(result)[:8]}"):
                failures += 1

            if open_ones:
                rid = open_ones[0].get("id") or open_ones[0].get("restaurantId")
                menu = await swiggy.get_restaurant_menu(mcp, address_id, rid)
                items = adapt_food_menu(menu, slot="dinner")
                usable = [i for i in items
                          if not i.ref.get("has_variants") and not i.ref.get("has_addons")]
                if not report(bool(items), "menu adapts to MenuItems",
                              f"{len(items)} items, {len(usable)} cart-ready"
                              if items else f"menu keys: {sorted(menu)[:8]}"):
                    failures += 1

            result = await swiggy.search_products(mcp, address_id, "chips")
            products = adapt_instamart_products(result, slot="snacks")
            if not report(bool(products), "product search adapts to MenuItems",
                          f"{len(products)} in-stock options" if products
                          else f"keys seen: {sorted(result)[:8]}"):
                failures += 1
            if products and not report(all(p.ref.get("spin_id") for p in products),
                                       "products carry spin_id (update_cart needs it)"):
                failures += 1

    except Exception as e:
        report(False, "live connection", f"{type(e).__name__}: {e}")
        print("\nIf this is an auth error, the token may have expired (5 days) -")
        print("run: python -m integrations.auth")
        return

    print()
    if failures:
        print(f"{failures} check(s) failed. Fix those before run_live_plan -")
        print("each failure above names the exact call and what came back.")
    else:
        print("All clear. The full flow is:")
        print('  python -m app.run_live_plan "dinner for 4 at 8pm, budget 1500"')
        print("It fills your cart only after you approve, and it cannot place an order.")


if __name__ == "__main__":
    asyncio.run(main())
