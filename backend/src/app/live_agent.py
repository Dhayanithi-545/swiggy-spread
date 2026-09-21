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

from core import agent, portions
from integrations import live_tools as swiggy
from integrations.adapters import adapt_food_menu, adapt_instamart_products, adapt_menu_search
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
MAX_MENUS_TO_FETCH = 4

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


async def _candidate_restaurants(
    mcp: SwiggyMCP, address_id: str, req: agent.Request
) -> dict[str, dict]:
    """Which restaurants are worth fetching a full menu for?

    Returns {restaurant_id: {"name", "rating"}}, capped at
    MAX_MENUS_TO_FETCH.

    Two routes:
      - Dish hints use search_menu: ONE call answers "who near me serves
        parotta?" across every restaurant, instead of guessing which
        restaurant search would surface it.
      - No hints: a normal restaurant search, open ones only.
    """
    found: dict[str, dict] = {}

    hints = [dr.dish_hint for dr in req.dinner_requests if dr.dish_hint]
    for hint in hints[:3]:
        result = await swiggy.search_menu(mcp, address_id, hint)
        for dish in adapt_menu_search(result, slot="dinner"):
            rid = dish.ref.get("restaurant_id")
            if rid and rid not in found:
                found[rid] = {"name": dish.ref.get("restaurant_name", ""),
                              "rating": dish.ref.get("restaurant_rating", 0.0)}
            if len(found) >= MAX_MENUS_TO_FETCH:
                return found

    if found:
        return found

    for term in search_terms("dinner", req):
        result = await swiggy.search_restaurants(mcp, address_id, term)
        for r in (result.get("restaurants") or []):
            if r.get("availabilityStatus") != "OPEN":
                continue
            rid = str(r.get("id") or r.get("restaurantId") or "")
            if rid and rid not in found:
                try:
                    rating = float(r.get("avgRating") or 0)
                except (TypeError, ValueError):
                    rating = 0.0
                found[rid] = {"name": r.get("name", ""), "rating": rating}
            if len(found) >= MAX_MENUS_TO_FETCH:
                return found
        if found:
            return found  # one search's worth of candidates is plenty

    return found


def _score_dinner(items: list, picked: list, rating: float,
                  matched_requests: int = 0) -> float:
    """How good is this restaurant as THE dinner restaurant?

    Learned from the first live run, where a soup-only kitchen won
    "dinner" simply by being first in the search results: being ABLE to
    fill a course is not the same as being a good place to fill it from.

    The score rewards, in order of weight:
      - the picked meal actually contains a main (a dinner without a
        main is starters pretending)
      - role variety in the picked meal (main + rice + bread beats
        three mains)
      - a deep usable menu (more cart-ready dishes = better recovery
        options when something goes out of stock)
      - the restaurant's rating
    """
    picked_roles = {portions.role_of(i.name) for i, _ in picked}
    score = 0.0
    # When the user NAMED their dishes, nothing outweighs actually serving
    # them: "2 want parotta, 2 want biryani" should prefer the restaurant
    # that satisfies both requests over a deeper menu that satisfies one.
    score += 40 * matched_requests
    if "main" in picked_roles:
        score += 30
    score += 10 * len(picked_roles)
    score += min(len(items), 15)
    score += 2 * rating
    return score


async def _dinner_course(
    mcp: SwiggyMCP, address_id: str, req: agent.Request, budget_share: int
) -> tuple[agent.Course, str]:
    """Fetches up to MAX_MENUS_TO_FETCH candidate menus, builds a trial
    meal from EACH, scores them, and commits to the best one - never the
    merely-first one.

    Still never mixes items from two restaurants: a real food cart
    belongs to exactly one restaurant, so course.options only ever holds
    the winning restaurant's menu. That is also what keeps every later
    repair (rebalance swap, stock-out replacement) inside that
    restaurant automatically.

    Returns (course, why) - `why` is a human sentence for plan.notes
    explaining which restaurant won and on what grounds.
    """
    course = agent.Course(slot="dinner", platform="food", target=req.slots["dinner"])

    best = None  # (score, items, picked, problems, name)
    for rid, meta in (await _candidate_restaurants(mcp, address_id, req)).items():
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
                items, req.dinner_requests, budget_share)
            matched = len(req.dinner_requests) - len(problems)
        else:
            picked, problems = agent.pick_items(items, "dinner", budget_share,
                                                req.guests), []
            matched = 0
        if not picked:
            continue

        score = _score_dinner(items, picked, meta["rating"], matched)
        name = meta["name"] or (items[0].ref.get("restaurant_name") or "unnamed")
        if best is None or score > best[0]:
            best = (score, items, picked, problems, name)

    if best is None:
        # Nothing worked in any restaurant tried - violations() will flag
        # the empty course rather than this failing silently.
        course.notes.append("no open restaurant could fill this course")
        return course, ""

    score, items, picked, problems, name = best
    course.options = items          # scoped to the WINNING restaurant only
    course.items = picked
    course.notes = problems
    roles = sorted({portions.role_of(i.name) for i, _ in picked})
    why = (f"Dinner from {name} - best of the candidates checked "
           f"({len(items)} usable dishes, covers {', '.join(roles)}).")
    return course, why


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
            course, why = await _dinner_course(mcp, address_id, req, share)
            if why:
                plan.notes.append(why)
        else:
            course = await _instamart_course(mcp, address_id, slot, req, share)
        plan.courses.append(course)

    plan.courses.sort(key=lambda c: c.target)
    # Identical rules to the mock path - no live-specific version exists.
    plan = agent.rebalance(plan)
    plan = agent.top_up(plan)
    return plan
