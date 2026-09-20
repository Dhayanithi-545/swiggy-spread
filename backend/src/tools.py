"""
tools.py - what the agent is allowed to touch.

Two modes:

  MOCK (default)  - a small built-in catalog. Runs offline, instantly,
                    and is deterministic, so evals can rely on it.
  LIVE            - real Swiggy MCP servers. Needs Builders Club access.
                    See load_swiggy_mcp_tools() at the bottom.

Everything above the search() function is deliberately boring data.
The interesting logic lives in agent.py.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace


# ---------------------------------------------------------------- data


@dataclass(frozen=True)
class MenuItem:
    id: str
    name: str
    price: int          # rupees
    veg: bool
    platform: str       # "instamart" | "food" | "dineout"
    slot: str           # "snacks" | "dinner" | "dessert"
    tags: tuple[str, ...] = ()
    available: bool = True
    # Provider-specific extras a real order needs but the planner never
    # touches - restaurant_id for Food, sku_id for Instamart, etc.
    # Empty for the mock catalog. Kept generic on purpose: every new
    # platform quirk we hit doesn't need a new MenuItem field.
    ref: dict = field(default_factory=dict)

    def __repr__(self) -> str:  # keeps eval output readable
        return f"{self.name} (Rs{self.price})"


CATALOG: list[MenuItem] = [
    # --- snacks (Instamart: groceries, arrives fast) ---
    MenuItem("s1", "Potato chips (family pack)", 120, True, "instamart", "snacks", ("crisps",)),
    MenuItem("s2", "Roasted peanuts 500g", 180, True, "instamart", "snacks", ("nuts",)),
    MenuItem("s3", "Nachos + salsa dip", 260, True, "instamart", "snacks", ("crisps",)),
    MenuItem("s4", "Paneer tikka (ready to heat)", 320, True, "instamart", "snacks", ("spicy",)),
    MenuItem("s5", "Chicken cocktail samosa", 340, False, "instamart", "snacks", ("spicy",)),
    MenuItem("s6", "Cheese cubes platter", 420, True, "instamart", "snacks", ()),
    MenuItem("s7", "Soft drinks (6 pack)", 240, True, "instamart", "snacks", ("drinks",)),

    # --- dinner (Food: restaurants) ---
    MenuItem("d1", "Veg biryani (serves 2)", 460, True, "food", "dinner", ("spicy", "rice")),
    MenuItem("d2", "Chicken biryani (serves 2)", 560, False, "food", "dinner", ("spicy", "rice")),
    MenuItem("d3", "Paneer butter masala", 380, True, "food", "dinner", ("curry",)),
    MenuItem("d4", "Dal tadka", 260, True, "food", "dinner", ("curry",)),
    MenuItem("d5", "Butter naan (4 pcs)", 180, True, "food", "dinner", ("bread",)),
    MenuItem("d6", "Butter chicken", 520, False, "food", "dinner", ("curry",)),
    MenuItem("d7", "Veg fried rice", 280, True, "food", "dinner", ("rice",)),
    MenuItem("d8", "Curd rice (serves 2)", 190, True, "food", "dinner", ("rice", "mild")),
    MenuItem("d9", "Parotta (4 pcs, serves 2)", 160, True, "food", "dinner", ()),

    # --- dessert ---
    MenuItem("x1", "Gulab jamun (6 pcs)", 180, True, "instamart", "dessert", ()),
    MenuItem("x2", "Vanilla ice cream tub", 320, True, "instamart", "dessert", ()),
    MenuItem("x3", "Chocolate brownie box", 420, True, "food", "dessert", ()),
    MenuItem("x4", "Rasmalai (4 pcs)", 260, True, "instamart", "dessert", ()),
    MenuItem("x5", "Tiramisu (single)", 480, False, "food", "dessert", ("egg",)),
]


# Rough delivery time per platform, in minutes. In LIVE mode this comes
# from the API instead - the number moves with area, hour and traffic.
BASE_ETA = {"instamart": 15, "food": 38, "dineout": 0}


# ---------------------------------------------------------------- search


_unavailable: set[str] = set()


def set_unavailable(*item_ids: str) -> None:
    """Used by evals to simulate stock-outs. No effect in LIVE mode."""
    _unavailable.update(item_ids)


def reset_availability() -> None:
    _unavailable.clear()


def search(
    slot: str,
    veg_only: bool = False,
    max_price: int | None = None,
    avoid_tags: tuple[str, ...] = (),
    platform: str | None = None,
) -> list[MenuItem]:
    """Find candidate items for one part of the evening.

    This is what a subagent calls. Note it returns OPTIONS - it never
    decides. Deciding is the planner's job.
    """
    out = []
    for item in CATALOG:
        if item.slot != slot:
            continue
        if item.id in _unavailable:
            continue
        if platform and item.platform != platform:
            continue
        if veg_only and not item.veg:
            continue
        if max_price is not None and item.price > max_price:
            continue
        if any(tag in item.tags for tag in avoid_tags):
            continue
        out.append(replace(item, available=True))
    return sorted(out, key=lambda i: i.price)


def get_eta(platform: str) -> int:
    """Delivery estimate in minutes."""
    return BASE_ETA.get(platform, 30)


def platform_for(slot: str) -> str:
    return {"snacks": "instamart", "dinner": "food", "dessert": "instamart"}.get(
        slot, "food"
    )


# ---------------------------------------------------------------- live mode


def live_mode() -> bool:
    return os.getenv("SPREAD_MODE", "mock").lower() == "live"


async def load_swiggy_mcp_tools():
    """Connect to the real Swiggy MCP servers.

    Requires Builders Club access (mcp.swiggy.com/builders). The exact
    tool names below are placeholders - print the loaded tools once you
    have access and update them.

    Deliberately NOT wired into the default path: this project ships in
    dry-run so a bug can never place a real order.
    """
    from langchain_mcp_adapters.client import MultiServerMCPClient

    token = os.environ["SWIGGY_MCP_TOKEN"]
    client = MultiServerMCPClient(
        {
            "swiggy_food": {
                "url": "https://mcp.swiggy.com/food",
                "transport": "streamable_http",
                "headers": {"Authorization": f"Bearer {token}"},
            },
            "swiggy_instamart": {
                "url": "https://mcp.swiggy.com/instamart",
                "transport": "streamable_http",
                "headers": {"Authorization": f"Bearer {token}"},
            },
        }
    )
    tools = await client.get_tools()
    print("Loaded Swiggy MCP tools:", [t.name for t in tools])
    return tools