"""
live_agent.py - runs agent.py's exact planner on real Swiggy data.

Nothing about HOW a plan is checked or fixed changes here - violations(),
rebalance(), replace_unavailable(), order_time() are all imported
straight from agent.py, completely unmodified. Only WHERE each course's
candidate items come from is different: a real restaurant/product
search instead of tools.py's mock catalog.

This file is the actual payoff of every earlier decision to keep
agent.py's rules from touching a data source directly - only this
file and the mock course_subagent() know Swiggy (or a fake catalog)
exists at all.
"""

from __future__ import annotations

import agent
import live_tools as swiggy
from adapters import adapt_food_menu, adapt_instamart_products
from mcp_client import SwiggyMCP

# What to search for, per slot. This is a placeholder, not a claim of
# intelligence - it's exactly the piece a real query-understanding
# step (the later Groq addition) should replace. Documented here so
# it's an obvious, honest gap rather than a hidden assumption.
DEFAULT_QUERY = {
    "snacks": "snacks",
    "dinner": "biryani",
    "dessert": "ice cream",
}

# Real network calls cost real seconds - cap how many restaurant menus
# we fetch for one plan.
MAX_RESTAURANTS_TO_CHECK = 3


async def _dinner_course(
    mcp: SwiggyMCP, address_id: str, term: str, req: agent.Request, budget_share: int
) -> agent.Course:
    """Tries restaurants one at a time and commits to the FIRST one that
    can fill the course - never mixes items from two restaurants,
    because a real food cart belongs to exactly one restaurant. This is
    also why rebalancing a dinner course later never accidentally
    swaps in an item from somewhere else: course.options only ever
    holds this one restaurant's menu.
    """
    result = await swiggy.search_restaurants(mcp, address_id, term)
    restaurants = [r for r in result.get("restaurants", [])
                   if r.get("availabilityStatus") == "OPEN"]

    for r in restaurants[:MAX_RESTAURANTS_TO_CHECK]:
        rid = r.get("id") or r.get("restaurantId")
        if not rid:
            continue

        menu = await swiggy.get_restaurant_menu(mcp, address_id, rid)
        items = adapt_food_menu(menu, slot="dinner")

        # Can't add these to a cart correctly yet - no variant/addon
        # selection built. Excluding them here means the planner never
        # even considers something we can't actually order.
        items = [i for i in items
                 if not i.ref.get("has_variants") and not i.ref.get("has_addons")]
        if req.veg_only:
            items = [i for i in items if i.veg]
        items = [i for i in items if i.available]

        picked = agent.pick_items(items, "dinner", budget_share, req.guests)
        if picked:
            course = agent.Course(slot="dinner", platform="food", target=req.slots["dinner"])
            course.options = items          # scoped to THIS restaurant only
            course.items = picked
            return course

    # Nothing worked in any of the restaurants tried - violations()
    # will flag the empty course rather than this failing silently.
    return agent.Course(slot="dinner", platform="food", target=req.slots["dinner"])


async def _instamart_course(
    mcp: SwiggyMCP, address_id: str, term: str, slot: str, req: agent.Request, budget_share: int
) -> agent.Course:
    result = await swiggy.search_products(mcp, address_id, term)
    options = adapt_instamart_products(result, slot=slot)

    if req.veg_only:
        options = [o for o in options if o.veg]
    options = [o for o in options if o.available]

    course = agent.Course(slot=slot, platform="instamart", target=req.slots[slot])
    course.options = options
    course.items = agent.pick_items(options, slot, budget_share, req.guests)
    return course


async def build_plan_live(req: agent.Request, mcp: SwiggyMCP, address_id: str) -> agent.Plan:
    """Same shape as agent.build_plan() - split the budget, fill each
    course, then enforce the cross-cutting rules. Only where each
    course's candidates come from is different."""
    plan = agent.Plan(request=req)

    weights = {"snacks": 0.25, "dinner": 0.5, "dessert": 0.25}
    active = {s: weights.get(s, 1 / len(req.slots)) for s in req.slots}
    scale = sum(active.values())

    for slot in req.slots:
        share = int(req.budget * active[slot] / scale)
        term = DEFAULT_QUERY.get(slot, slot)

        if slot == "dinner":
            course = await _dinner_course(mcp, address_id, term, req, share)
        else:
            course = await _instamart_course(mcp, address_id, term, slot, req, share)

        plan.courses.append(course)

    plan.courses.sort(key=lambda c: c.target)
    plan = agent.rebalance(plan)  # identical rules - no live-specific version exists
    return plan