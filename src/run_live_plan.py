"""
run_live_plan.py - the actual product, running for real.

    python run_live_plan.py "6 friends Saturday 8pm, budget 3000, 2 are vegetarian"

Same guardrail, same planner, same budget/veg/timing rules as the mock
version - just pointed at real restaurants and real products near your
real address. Still a dry run: nothing is added to a cart, nothing is
ordered. That's the next step after this one works.
"""

import asyncio
import sys

import agent
import guardrail
from auth import load_token
from live_agent import build_plan_live
from mcp_client import SwiggyMCP
import live_tools as swiggy


async def main() -> None:
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        text = input("What's the plan? > ").strip()

    verdict = guardrail.check(text)
    if not verdict:
        print("\n" + verdict.reason + "\n")
        return

    token = load_token()
    if not token:
        print("No token yet. Run: python auth.py")
        return

    req = agent.parse_request(text)

    async with SwiggyMCP(token, servers=("food", "instamart")) as mcp:
        addresses = await swiggy.get_addresses(mcp)
        if not addresses:
            print("No saved addresses on this account. Add one in the Swiggy app first.")
            return

        print("\nYour addresses:")
        for i, a in enumerate(addresses):
            print(f"  [{i}] {a.get('addressLine')}")
        choice = input("\nPick an address number: ").strip() or "0"
        address_id = addresses[int(choice)]["id"]

        print("\nSearching real restaurants and products - this takes a few seconds...")
        plan = await build_plan_live(req, mcp, address_id)

    print(agent.render(plan))

    answer = input("\nAdd these to your REAL cart? (yes/no) - this will NOT place an order > ")
    if answer.strip().lower() not in {"y", "yes"}:
        print("\nCancelled. Nothing added to any cart.")
        return

    from execute_live import add_plan_to_cart

    print("\nAdding to your real cart...")
    async with SwiggyMCP(token, servers=("food", "instamart")) as mcp:
        results = await add_plan_to_cart(mcp, plan, address_id)

        print("\nRaw response from Swiggy for each cart touched:")
        for key, r in results.items():
            print(f"  {key}: {r}")

        print("\nFetching your real carts back, to prove it actually landed...")
        if "food" in results:
            cart = await swiggy.get_food_cart(mcp, address_id)
            print(f"  Food cart now: {cart}")
        if "instamart" in results:
            cart = await swiggy.get_instamart_cart(mcp)
            print(f"  Instamart cart now: {cart}")

        removed = (results.get("instamart") or {}).get("removedOutOfStockItems") or []
        if removed:
            print("\n" + "!" * 60)
            print("  Swiggy just did what evals.py tests for on fake data - for real:")
            for r in removed:
                print(f"    '{r.get('itemName')}' went out of stock and was dropped.")
            print("  We aren't reacting to this yet - it just went silently missing")
            print("  from the cart. Next step: call agent.replace_unavailable() when")
            print("  this happens, so Spread fixes it instead of Swiggy silently doing so.")
            print("!" * 60)

    print("\nOpen the Swiggy app now - these items should be sitting in your cart.")
    print("NOTHING has been ordered. NOTHING has been paid for.")
    print("Clear it in the app, or with flush_food_cart / clear_instamart_cart, anytime.")


if __name__ == "__main__":
    asyncio.run(main())