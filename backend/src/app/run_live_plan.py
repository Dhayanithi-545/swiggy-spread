"""
run_live_plan.py - the actual product, running for real.

    python -m app.run_live_plan "6 friends Saturday 8pm, budget 3000, 2 are vegetarian"

Same guardrail, same questions, same planner, same budget/veg/timing
rules as the mock version - just pointed at real restaurants and real
products near your real address.

It ends by filling your REAL Swiggy cart, after you approve the plan.
**It does not place an order and it cannot.** See integrations/safety.py:
every tool call is checked against a deny-list before it reaches the
wire, so neither this file nor a future edit to it can spend your money.
Open the app afterwards and the items are sitting in the cart, waiting
for you to decide.
"""

import asyncio
import sys

# so this runs both as `python -m <pkg>.<mod>` and as `python <pkg>/<mod>.py`
if __package__ in (None, ""):
    import pathlib
    import sys as _sys
    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from core import agent, conversation, guardrail
from integrations import live_tools as swiggy
from integrations.auth import load_token
from integrations.mcp_client import SwiggyMCP


def ask_in_terminal(question) -> str:
    """Render one Question and read the reply. Pressing enter takes the
    default the question already offered."""
    print()
    print(question.prompt())
    if question.why:
        print(f"  ({question.why})")
    try:
        return input("  > ").strip()
    except EOFError:
        print("  (no input - using the default)")
        return ""


def pick_address(addresses: list[dict]) -> dict | None:
    """Never assume an address. An out-of-range or non-numeric answer
    re-asks instead of crashing on int('abc') or addresses[99]."""
    print("\nYour saved addresses:")
    for i, a in enumerate(addresses):
        tag = a.get("addressTag") or a.get("addressCategory") or ""
        print(f"  [{i}] {tag}  {a.get('addressLine', '(no label)')}")

    for _ in range(3):
        try:
            raw = input("\nDeliver to which one? (number) > ").strip()
        except EOFError:
            raw = ""
        if not raw:
            return addresses[0]
        if raw.isdigit() and 0 <= int(raw) < len(addresses):
            return addresses[int(raw)]
        print(f"  Pick a number between 0 and {len(addresses) - 1}.")
    return None


def confirm(prompt: str) -> bool:
    try:
        return input(prompt).strip().lower() in {"y", "yes", "ok", "confirm", "go"}
    except EOFError:
        return False


async def main() -> None:
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        try:
            text = input("What's the plan? > ").strip()
        except EOFError:
            return

    verdict = guardrail.check(text)
    if not verdict:
        print("\n" + verdict.reason + "\n")
        return

    token = load_token()
    if not token:
        print("No token yet. Run: python -m integrations.auth")
        return

    req = agent.parse_request(text)

    # Ask for what we genuinely don't know - courses, headcount, time,
    # budget - before spending anyone's time on network calls. Identical
    # questions, in the identical order, to the mock CLI.
    req, blocked = conversation.run_clarify_loop(req, ask_in_terminal)
    if blocked:
        print("\n" + blocked + "\n")
        return
    if req.budget is None:
        print("\nI won't guess a budget - it's your money. Run again with a "
              "number, e.g. 'dinner for 6, budget 2000'.\n")
        return

    # One session for the whole run. The previous version opened a second
    # connection just to fill the cart, which doubled the handshake cost
    # and could pick a different session than the one that priced the plan.
    async with SwiggyMCP(token, servers=("food", "instamart")) as mcp:
        addresses = await swiggy.get_addresses(mcp)
        if not addresses:
            print("No saved addresses on this account. Add one in the Swiggy app first.")
            return

        address = pick_address(addresses)
        if not address:
            print("No address chosen - stopping rather than guessing one.")
            return
        address_id = address["id"]

        print("\nSearching real restaurants and products - this takes a few seconds...")
        from app.live_agent import build_plan_live

        plan = await build_plan_live(req, mcp, address_id)
        print(agent.render(plan))

        problems = agent.violations(plan)
        if problems:
            print("  This plan has problems listed above.")
            if not confirm("  Fill the cart anyway? (yes/no) > "):
                print("\nStopped. Nothing added to any cart.")
                return

        print("\nNothing has been ordered. The next step only FILLS your cart -")
        print("no payment, no order, and Spread cannot place one.")
        if not confirm("Add these to your real Swiggy cart? (yes/no) > "):
            print("\nCancelled. Nothing added to any cart.")
            return

        from app.execute_live import add_plan_to_cart

        print("\nAdding to your real cart...")
        results = await add_plan_to_cart(mcp, plan, address_id)

        for key, value in results.items():
            label = "ERROR" if key.endswith("_error") else "ok"
            print(f"  {key:<18} {label}: {value}")

        # Swiggy silently drops items that went out of stock between the
        # search and the cart write. The old version printed a note saying
        # "we aren't reacting to this yet" - now we do.
        await react_to_stockouts(mcp, plan, results, address_id)

        print("\nReading your carts back, to prove it landed...")
        if "food" in results:
            print(f"  Food cart:      {await swiggy.get_food_cart(mcp, address_id)}")
        if "instamart" in results:
            print(f"  Instamart cart: {await swiggy.get_instamart_cart(mcp)}")

    print("\nOpen the Swiggy app - these items are sitting in your cart.")
    print("NOTHING has been ordered. NOTHING has been paid for.")
    print("Clear it in the app any time, or re-run with a different plan.")


async def react_to_stockouts(mcp, plan, results, address_id) -> None:
    """Swiggy drops out-of-stock items from the cart without asking. That
    silently changes the plan the person approved, so we say so and let
    the planner pick replacements the same way evals.py tests on fake
    data. The cart is NOT rewritten automatically - the person approved a
    specific plan, and a replacement is a new thing to approve."""
    removed = (results.get("instamart") or {}).get("removedOutOfStockItems") or []
    if not removed:
        return

    print("\n" + "!" * 60)
    print("  Swiggy dropped items that just went out of stock:")
    for r in removed:
        print(f"    - {r.get('itemName', r.get('spinId', 'unknown item'))}")

    for r in removed:
        item_id = r.get("spinId") or r.get("skuId")
        if item_id:
            plan = agent.replace_unavailable(plan, str(item_id))

    print("\n  Replanned around them:")
    print(agent.render(plan))
    print("  Your cart still holds the ORIGINAL items minus the dropped ones.")
    print("  Re-run to fill it with the replanned version.")
    print("!" * 60)


if __name__ == "__main__":
    asyncio.run(main())
