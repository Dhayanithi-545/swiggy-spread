"""
safety.py - the one place that decides what counts as spending money.

Spread adds items to a real Swiggy cart. A cart is free and reversible.
Placing the order is neither, so it is blocked here rather than left to
whoever is editing a calling file at the time.

Two layers, on purpose:

  1. live_tools.place_food_order() / checkout_instamart() call
     refuse_if_spending() before they build a request.
  2. mcp_client.call() checks EVERY tool name against SPENDING_TOOLS
     before it hits the wire. This is the layer that matters, because
     call_instamart_tool() is a passthrough - without it, one string
     typed in the wrong place could place an order the typed wrappers
     would have caught.

Layer 2 means a bug, a typo, or a future careless edit in the layer
above still cannot spend money. That's the whole point of having both.

Turning ordering on is deliberately annoying: set

    SPREAD_ALLOW_REAL_ORDERS=yes-i-want-to-spend-real-money

There is no flag, no CLI option and no function argument that does it,
so it cannot happen by accident or by an agent deciding it would be
helpful.
"""

from __future__ import annotations

import os
import re

# Env var that unlocks real spending, and the exact value it must have.
UNLOCK_VAR = "SPREAD_ALLOW_REAL_ORDERS"
UNLOCK_VALUE = "yes-i-want-to-spend-real-money"

# Exact tool names known to place an order or move money. Matched
# case-insensitively against the tool name sent to any Swiggy server.
SPENDING_TOOLS = frozenset({
    "place_food_order",
    "place_order",
    "checkout",
    "checkout_instamart",
    "confirm_order",
    "create_order",
    "initiate_payment",
    "make_payment",
    "process_payment",
    "pay",
})

# Belt and braces for tool names this project has never seen. Swiggy can
# add tools at any time and Instamart's full tool list was never
# published - an unknown `im_place_order_v2` should be refused by
# default, not sail through because it isn't in the set above.
SPENDING_PATTERNS = (
    re.compile(r"place.*order", re.I),
    re.compile(r"checkout", re.I),
    re.compile(r"confirm.*order", re.I),
    re.compile(r"(^|_)pay(ment)?($|_)", re.I),
)


class OrderingDisabled(RuntimeError):
    """Raised instead of placing a real order. Not a bug - the system
    working as designed."""


def _snakeify(name: str) -> str:
    """camelCase -> snake_case, so `makePayment` and `make_payment` are the
    same string to the patterns below. Swiggy's own tools are snake_case,
    but a future one or a hand-typed passthrough might not be, and that is
    not a distinction worth losing money over."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()


def is_spending_tool(tool_name: str) -> bool:
    name = (tool_name or "").strip()
    if name.lower() in SPENDING_TOOLS:
        return True
    normalised = _snakeify(name)
    if normalised in SPENDING_TOOLS:
        return True
    return any(p.search(name) or p.search(normalised) for p in SPENDING_PATTERNS)


def ordering_unlocked() -> bool:
    return os.getenv(UNLOCK_VAR, "") == UNLOCK_VALUE


def refuse_if_spending(tool_name: str, *, context: str = "") -> None:
    """Raise unless this tool is safe to call. Called on every single
    MCP tool invocation, not just the ones we wrote a wrapper for."""
    if not is_spending_tool(tool_name):
        return
    if ordering_unlocked():
        return

    where = f" ({context})" if context else ""
    raise OrderingDisabled(
        f"Refusing to call '{tool_name}'{where} - it places a real order "
        f"or moves real money.\n"
        f"Spread is a planner: it fills your cart and stops there.\n"
        f"If you genuinely want to spend money, set "
        f"{UNLOCK_VAR}={UNLOCK_VALUE} in your environment."
    )
