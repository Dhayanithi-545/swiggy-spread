"""
live_agent.py - runs core/agent.py's exact planner on real Swiggy data.

Nothing about HOW a plan is checked or fixed changes here - violations(),
rebalance(), replace_unavailable(), order_time(), compose_dinner() are
all imported straight from agent.py, completely unmodified. Only WHERE
each course's candidate items come from is different: a real
restaurant/product search instead of tools.py's mock catalog.

This file is the actual payoff of every earlier decision to keep
agent.py's rules from touching a data source directly - only this file
and the mock course_subagent() know Swiggy (or a fake catalog) exists
at all.

Parity note: this used to search a hardcoded "biryani" for every dinner
and ignore both the dish hints and the avoid-tags the user gave. It
searches what they asked for now, and applies the same filters the mock
path does, so the live plan and the mock plan are the same product.
"""

from __future__ import annotations

from core import agent
from integrations import live_tools as swiggy
from integrations.adapters import adapt_food_menu, adapt_instamart_products
from integrations.mcp_client import SwiggyMCP

# Fallback search terms, used only when the request gives us nothing more
# specific. Anything the user actually named beats these.
DEFAULT_QUERY = {
    "snacks": "party snacks",
    "dinner": "dinner",
    "dessert": "dessert",
}

# Real network calls cost real seconds - cap how many restaurant menus
# we fetch for one plan.
MAX_RESTAURANTS_TO_CHECK = 3

# The live path has no tag metadata (Swiggy doesn't return "spicy" as a
# field), so avoid-tags are matched against the dish name instead. Crude,
# but the alternative - silently ignoring "nothing spicy" - is worse.
AVOID_WORDS = {
    "spicy": ("spicy", "hot", "chilli", "chili", "peri", "schezwan",
              "andhra", "kolhapuri"),
    "egg": ("egg", "omelette", "tiramisu", "mayo"),
    "nuts": ("nut", "peanut", "cashew", "almond", "badam"),
}


def search_terms(slot: str, req: agent.Request) -> list[str]:
    """What to actually search Swiggy for.

    Dish hints come first and in the user's own words - if someone said
    "2 want parotta, 3 want biryani", we search parotta and biryani, not
    a generic term that happens to be hardcoded in this file.
    """
    terms: list[str] = []
    if slot == "dinner":
        terms = [dr.dish_hint for dr in req.dinner_requests if dr.dish_hint]
    if not terms:
        terms = [DEFAULT_QUERY.get(slot, slot)]
    # De-duplicate, keep order, cap the number of live searches.
    seen: set[str] = set()
    out = []
    for t in terms:
        key = t.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(t)
    return out[:3]


def allowed(item, req: agent.Request) -> bool:
    """The same dietary rules the mock path applies, against live data."""
    if not item.available:
        return False
    if req.veg_only and not item.veg:
        return False
    name = item.name.lower()
    for tag in req.avoid_tags:
        if any(w in name for w in AVOID_WORDS.get(tag, (tag,))):
            return False
    return True


async def _dinner_course(
    mcp: SwiggyMCP, address_id: str, req: agent.Request, budget_share: int
) -> agent.Course:
    """Tries restaurants one at a time and commits to the FIRST one that
    can fill the course - never mixes items from two restaurants,
    because a real food cart belongs to exactly one restaurant. This is
    also why rebalancing a dinner course later never accidentally
    swaps in an item from somewhere else: course.options only ever
    holds this one restaurant's menu.
    """
    course = agent.Course(slot="dinner", platform="food", target=req.slots["dinner"])

    for term in search_terms("dinner", req):
        result = await swiggy.search_restaurants(mcp, address_id, term)
        restaurants = [r for r in (result.get("restaurants") or [])
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
            items = [i for i in items if allowed(i, req)]
            if not items:
                continue

            # Same branch the mock planner takes: an explicit per-person
            # split is honoured dish by dish, otherwise the course is
            # composed by role (a main, a rice, a bread) rather than
            # buying N of one thing.
            if req.dinner_requests:
                picked, problems = agent.pick_items_for_requests(
                    items, req.dinner_requests, budget_share
                )
                course.notes = problems
            else:
                picked = agent.pick_items(items, "dinner", budget_share, req.guests)

            if picked:
                course.options = items      # scoped to THIS restaurant only
                course.items = picked
                return course

    # Nothing worked in any restaurant tried - violations() will flag the
    # empty course rather than this failing silently.
    course.notes.append("no open restaurant could fill this course")
    return course


async def _instamart_course(
    mcp: SwiggyMCP, address_id: str, slot: str, req: agent.Request, budget_share: int
) -> agent.Course:
    course = agent.Course(slot=slot, platform="instamart", target=req.slots[slot])

    options: list = []
    seen: set[str] = set()
    for term in search_terms(slot, req):
        result = await swiggy.search_products(mcp, address_id, term)
        for item in adapt_instamart_products(result, slot=slot):
            if item.id in seen or not allowed(item, req):
                continue
            seen.add(item.id)
            options.append(item)

    course.options = options
    course.items = agent.pick_items(options, slot, budget_share, req.guests)
    if not options:
        course.notes.append("nothing available on Instamart for this course")
    return course


async def build_plan_live(req: agent.Request, mcp: SwiggyMCP, address_id: str) -> agent.Plan:
    """Same shape as agent.build_plan() - split the budget, fill each
    course, then enforce the cross-cutting rules. Only where each
    course's candidates come from is different."""
    if req.budget is None:
        raise ValueError(
            "Request.budget is None - ask the person before planning. "
            "Use agent.missing_info(req) / conversation.next_question()."
        )

    plan = agent.Plan(request=req)

    for slot, share in agent.budget_split(req).items():
        if slot == "dinner":
            course = await _dinner_course(mcp, address_id, req, share)
        else:
            course = await _instamart_course(mcp, address_id, slot, req, share)
        plan.courses.append(course)

    plan.courses.sort(key=lambda c: c.target)
    # Identical rules to the mock path - no live-specific version exists.
    plan = agent.rebalance(plan)
    plan = agent.top_up(plan)
    return plan
