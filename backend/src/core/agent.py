"""
agent.py - the planner, the subagents, and the graph.

Layout of this file:

  1. Data     - Request, Course, Plan
  2. Pure logic - timing, validation, rebalancing, replanning
                  (no LLM, no network, no LangGraph - so evals can
                   test it directly and get the same answer every time)
  3. Subagents  - one per course, each finds options for its own slot
  4. Graph      - LangGraph wiring with a human approval gate
  5. CLI

LangGraph is imported lazily inside build_graph(). That is on purpose:
evals.py can import this file and test the logic without LangGraph or an
API key installed.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta

if __name__ == "__main__" and __package__ is None:  # `python core/agent.py`
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from core import portions, tools
from core.tools import MenuItem

# Re-exported so callers (and evals) keep importing this from agent, even
# though the real numbers now live in portions.py.
portions_needed = portions.portions_needed

# ---------------------------------------------------------------- 1. data


@dataclass
class DishRequest:
    """One distinct preference inside a slot - '2 people want parotta',
    '3 people want biryani'. A slot can hold several of these. This is
    the actual fix for 'everyone in dinner gets the same dish' - each
    DishRequest is its own headcount and its own hint."""
    count: int
    dish_hint: str | None = None    # free text - "parotta", "biryani"
    veg_only: bool = False


@dataclass
class Request:
    """What the user actually wants.

    The *_known / slots_confident flags are the difference between "they
    told us" and "we guessed". conversation.next_question() reads them to
    decide what is worth asking, and summarise_assumptions() reads them to
    say out loud what we decided for them. Defaulting silently and
    defaulting loudly are very different products.
    """
    guests: int = 4
    # None means genuinely UNKNOWN, not "assume 2000". A silent default
    # was the bug: the agent should ask, not guess, when this is None.
    budget: int | None = None
    veg_only: bool = False          # true if ANY guest is vegetarian-only
    veg_guests: int = 0
    avoid_tags: tuple[str, ...] = ()
    slots: dict[str, datetime] = field(default_factory=dict)  # slot -> eat-by time
    # Per-person dinner splits. Empty list means "one dish for everyone" -
    # the old behaviour - so every existing caller keeps working.
    dinner_requests: list[DishRequest] = field(default_factory=list)
    raw: str = ""

    # When dinner (or the single requested course) should be on the table.
    # Kept separately from slots so re-answering "what time?" can move the
    # whole evening without rebuilding the request.
    dinner_time: datetime | None = None

    # Did they tell us, or did we guess?
    slots_confident: bool = True
    guests_known: bool = True
    time_known: bool = True

    def dinner_plan(self) -> list[DishRequest]:
        """What dinner actually needs to satisfy. Falls back to one
        request covering everyone if nobody specified a per-person
        split - this is what keeps every old call site working
        unchanged."""
        if self.dinner_requests:
            return self.dinner_requests
        return [DishRequest(count=self.guests, dish_hint=None, veg_only=self.veg_only)]


def missing_info(req: Request) -> list[str]:
    """What the agent genuinely doesn't know and shouldn't guess.

    Order matters and is the same order conversation.next_question()
    asks in: each answer changes the ones below it.
    """
    gaps = []
    if not req.slots_confident:
        gaps.append("courses")
    if not req.guests_known:
        gaps.append("guests")
    if not req.time_known:
        gaps.append("time")
    if req.budget is None:
        gaps.append("budget")
    return gaps


@dataclass
class Course:
    """One part of the evening. One cart, one platform, one target time."""
    slot: str
    platform: str
    target: datetime                 # when food should be ON THE TABLE
    items: list[tuple[MenuItem, int]] = field(default_factory=list)  # (item, qty)
    # Every candidate that was available when this course was built -
    # mock or live, doesn't matter. Rebalancing and stock-out recovery
    # pick from THIS list instead of re-searching, so they work
    # identically no matter where the data came from.
    options: list[MenuItem] = field(default_factory=list)
    # Dish requests that couldn't be matched (e.g. "parotta" not found
    # anywhere on this platform). Not a hard block - violations() turns
    # these into visible problems rather than the plan pretending
    # everyone's request was satisfied.
    notes: list[str] = field(default_factory=list)

    @property
    def subtotal(self) -> int:
        return sum(item.price * qty for item, qty in self.items)

    @property
    def eta(self) -> int:
        return tools.get_eta(self.platform)

    @property
    def buffer(self) -> int:
        """Safety margin. Longer ETAs are less reliable, so they get more
        slack. 10 minutes flat + 20% of the ETA, rounded up to 5."""
        raw = 10 + self.eta * 0.2
        return int(-(-raw // 5) * 5)

    @property
    def order_at(self) -> datetime:
        """The whole point of the project: work backwards from the target."""
        return order_time(self.target, self.eta, self.buffer)


@dataclass
class Plan:
    request: Request
    courses: list[Course] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(c.subtotal for c in self.courses)


# ---------------------------------------------------------------- 2. pure logic


def order_time(target: datetime, eta_minutes: int, buffer_minutes: int) -> datetime:
    """'Dessert at 10pm' does not mean 'order at 10pm'."""
    return target - timedelta(minutes=eta_minutes + buffer_minutes)


def portions_needed(guests: int, per_item_serves: int = 2) -> int:
    """Round up. 5 guests, serves-2 dishes -> 3 portions."""
    return max(1, -(-guests // per_item_serves))


def violations(plan: Plan) -> list[str]:
    """Every rule that must hold across the WHOLE evening, not per cart.
    This is the function that stops the agent forgetting the budget by
    the third order."""
    req = plan.request
    out: list[str] = []

    # A plan with no budget is a bug upstream, not an over-budget plan.
    # Say so instead of raising TypeError comparing int > None.
    if req.budget is None:
        out.append("no budget was ever established for this plan")
    elif plan.total > req.budget:
        out.append(f"over budget: {plan.total} > {req.budget}")

    if req.veg_only:
        for c in plan.courses:
            for item, _ in c.items:
                if not item.veg:
                    out.append(f"non-veg item in {c.slot}: {item.name}")

    for c in plan.courses:
        if not c.items:
            out.append(f"{c.slot} is empty")
        if c.order_at >= c.target:
            out.append(f"{c.slot} ordered too late to arrive by target")
        for item, _ in c.items:
            bad = set(item.tags) & set(req.avoid_tags)
            if bad:
                out.append(f"{c.slot}: {item.name} has avoided tag {sorted(bad)[0]}")
        for note in c.notes:
            out.append(f"{c.slot}: {note}")

    return out


def rebalance(plan: Plan) -> Plan:
    """Bring the plan back under budget.

    Strategy, in order:
      1. Drop quantity from the most expensive line in the fattest course.
      2. If a line hits zero, swap it for the cheapest valid alternative.
      3. Give up loudly rather than silently overspending.

    Never touches the last item of a course - an empty course is a worse
    failure than a slightly expensive one, and violations() will flag it.
    """
    if plan.request.budget is None:
        return plan  # nothing to rebalance against; violations() reports it

    guard = 0
    while plan.total > plan.request.budget and guard < 50:
        guard += 1

        # fattest course that still has something to give
        candidates = [c for c in plan.courses if len(c.items) > 1 or
                      (c.items and c.items[0][1] > 1)]
        if not candidates:
            plan.notes.append(
                f"Cannot reach budget {plan.request.budget}; "
                f"cheapest possible plan is {plan.total}."
            )
            return plan

        course = max(candidates, key=lambda c: c.subtotal)
        idx = max(range(len(course.items)), key=lambda i: course.items[i][0].price)
        item, qty = course.items[idx]

        if qty > 1:
            course.items[idx] = (item, qty - 1)
            plan.notes.append(f"Reduced {item.name} to {qty - 1} to fit budget.")
            continue

        cheaper = _cheaper_alternative(course, item, plan.request)
        if cheaper is not None:
            course.items[idx] = (cheaper, 1)
            plan.notes.append(f"Swapped {item.name} -> {cheaper.name} to fit budget.")
        else:
            course.items.pop(idx)
            plan.notes.append(f"Dropped {item.name} to fit budget.")

    return plan


def _cheaper_alternative(course: Course, item: MenuItem, req: Request) -> MenuItem | None:
    """Looks in the course's OWN cached options - never re-searches a
    data source. That's what lets this run identically whether the
    course came from the mock catalog or a real Swiggy search."""
    chosen = {i.id for i, _ in course.items}
    candidates = [o for o in course.options if o.id not in chosen and o.price < item.price]
    return candidates[0] if candidates else None


def replace_unavailable(plan: Plan, item_id: str) -> Plan:
    """An item went out of stock. Fix ONLY that item.

    A demo would rebuild the whole plan (and quietly change everything
    else). This finds the closest valid replacement, keeps the rest
    untouched, and re-checks the budget afterwards.
    """
    req = plan.request
    for course in plan.courses:
        for i, (item, qty) in enumerate(course.items):
            if item.id != item_id:
                continue

            chosen = {x.id for x, _ in course.items if x.id != item_id}
            options = [o for o in course.options
                       if o.id not in chosen and o.id != item_id]
            if not options:
                course.items.pop(i)
                plan.notes.append(f"{item.name} unavailable, no replacement found.")
                return plan

            # closest price wins - keeps the plan's shape intact
            best = min(options, key=lambda o: abs(o.price - item.price))
            course.items[i] = (best, qty)
            plan.notes.append(f"{item.name} unavailable -> replaced with {best.name}.")
            return rebalance(plan)

    return plan


def retime(plan: Plan) -> Plan:
    """Called when an ETA moves. order_at is computed, not stored, so the
    times fix themselves - this just records what changed."""
    for c in plan.courses:
        plan.notes.append(
            f"{c.slot}: order at {c.order_at:%H:%M} "
            f"(eta {c.eta}m + buffer {c.buffer}m) to eat at {c.target:%H:%M}"
        )
    return plan


# ---------------------------------------------------------------- 3. subagents


def pick_items_for_requests(
    options: list[MenuItem], requests: list[DishRequest], budget_share: int
) -> tuple[list[tuple[MenuItem, int]], list[str]]:
    """The multi-dish version of pick_items. Each DishRequest gets its
    OWN item, matched to its own hint - 'parotta' finds something with
    'parotta' in the name, 'biryani' finds a biryani. This is the
    actual mechanism behind 'one person wants X, another wants Y'.

    Returns (items, problems) - problems lists any request that
    couldn't be matched, so violations() can surface it instead of the
    plan silently pretending everyone got what they asked for.
    """
    items: list[tuple[MenuItem, int]] = []
    problems: list[str] = []
    spent = 0
    used_ids: set[str] = set()

    for dr in requests:
        candidates = [o for o in options if o.id not in used_ids]
        if dr.veg_only:
            candidates = [o for o in candidates if o.veg]

        if dr.dish_hint:
            hint = dr.dish_hint.lower()
            matched = [o for o in candidates if hint in o.name.lower()]
            if not matched:
                problems.append(f"couldn't find '{dr.dish_hint}' for {dr.count} guest(s)")
                continue
            candidates = matched

        if not candidates:
            problems.append(f"nothing available for {dr.count} guest(s)")
            continue

        qty = portions_needed(dr.count)
        candidates.sort(key=lambda o: o.price)

        # Prefer something that still fits what's left of the budget,
        # but never drop the request just because it doesn't - a
        # request going slightly over gets fixed by rebalance() later,
        # same as everything else.
        chosen = next(
            (c for c in candidates if spent + c.price * qty <= budget_share),
            candidates[0],
        )
        items.append((chosen, qty))
        used_ids.add(chosen.id)
        spent += chosen.price * qty

    return items, problems


def compose_dinner(
    options: list[MenuItem], budget_share: int, guests: int
) -> list[tuple[MenuItem, int]]:
    """Build a dinner that looks like a meal, not a pile of one dish.

    The old code bought `portions_needed(guests)` of whichever item it
    liked, so six people got three parottas and nothing to eat them
    with. portions.dinner_slots() says what a table for this many people
    should actually hold - a main, a rice, a bread, a second main once
    the group is big - and this fills that list in priority order until
    the money runs out.

    Falls back to the cheapest single item if the share is too small for
    even one role. An under-fed course is a visible problem; an empty
    one is a worse one.
    """
    if not options:
        return []

    by_role: dict[str, list[MenuItem]] = {}
    for o in options:
        by_role.setdefault(portions.role_of(o.name), []).append(o)
    for group in by_role.values():
        group.sort(key=lambda o: o.price, reverse=True)

    items: list[tuple[MenuItem, int]] = []
    used: set[str] = set()
    spent = 0

    for role, qty in portions.dinner_slots(guests):
        pool = [o for o in by_role.get(role, []) if o.id not in used]
        if not pool:
            continue
        # Best thing in this role that the remaining share can carry.
        pick = next((o for o in pool if spent + o.price * qty <= budget_share), None)
        if pick is None:
            continue
        items.append((pick, qty))
        used.add(pick.id)
        spent += pick.price * qty

    if not items:
        cheapest = min(options, key=lambda o: o.price)
        items.append((cheapest, 1))

    return items


def pick_items(
    options: list[MenuItem], slot: str, budget_share: int, guests: int
) -> list[tuple[MenuItem, int]]:
    """Choose items for one course.

    Dinner is composed by role (see compose_dinner). Snacks and dessert
    are simpler: a couple of different things, in quantities that match
    the headcount - portions.py holds those numbers.

    Pulled out on its own so mock and live data sources make the same
    decision the same way.
    """
    if not options:
        return []

    if slot == "dinner":
        return compose_dinner(options, budget_share, guests)

    want = portions.portions_for(slot, guests)
    items: list[tuple[MenuItem, int]] = []
    spent = 0

    for item in sorted(options, key=lambda o: o.price, reverse=True):
        if len(items) >= want.distinct_items:
            break
        cost = item.price * want.qty_each
        if spent + cost <= budget_share:
            items.append((item, want.qty_each))
            spent += cost

    if not items:  # budget share too small - take the cheapest anyway
        cheapest = min(options, key=lambda o: o.price)
        items.append((cheapest, 1))

    return items


def top_up(plan: Plan) -> Plan:
    """Spend the leftover, if there's a lot of it and something sensible
    to spend it on.

    The counterpart to rebalance(). A planner that comes back 40% under
    budget isn't being thrifty, it's under-catering: the person told us
    what they were willing to spend on feeding their friends. This adds
    quantity to what's already chosen, cheapest-first, and stops the
    moment it would cross the line.

    Only runs when the gap is worth acting on - shaving the last Rs40 off
    a budget produces churn, not a better dinner.
    """
    req = plan.request
    if req.budget is None or not plan.courses:
        return plan

    leftover = req.budget - plan.total
    if leftover <= 0 or leftover < req.budget * 0.15:
        return plan

    added_variety: list[str] = []
    added_qty = 0
    guard = 0

    while guard < 20:
        guard += 1
        leftover = req.budget - plan.total
        if leftover <= 0:
            break

        # Variety first. A second dessert beats two of the first one, and
        # the same is true of snacks and of dinner - that's why the
        # course carries its full options list around.
        new_item = _best_new_item(plan, req, leftover)
        if new_item is not None:
            course, item = new_item
            course.items.append((item, 1))
            added_variety.append(item.name)
            continue

        # Nothing new fits - add another of the cheapest thing that does.
        bump = None
        for course in plan.courses:
            for idx, (item, qty) in enumerate(course.items):
                if item.price <= leftover and (bump is None or item.price < bump[2].price):
                    bump = (course, idx, item, qty)
        if bump is None:
            break
        course, idx, item, qty = bump
        course.items[idx] = (item, qty + 1)
        added_qty += 1

    bits = []
    if added_variety:
        bits.append("added " + ", ".join(added_variety))
    if added_qty:
        bits.append(f"{added_qty} extra portion(s)")
    if bits:
        plan.notes.append(
            f"Budget had room, so I {' and '.join(bits)}. "
            f"Rs{req.budget - plan.total} still unspent."
        )
    return plan


def _best_new_item(plan: Plan, req: Request, leftover: int):
    """The most expensive not-yet-chosen option that still fits, so spare
    budget buys something worth having rather than the cheapest filler.
    Honours the same veg and avoid-tag rules as everything else - spare
    money is not an excuse to break a dietary rule."""
    best = None
    for course in plan.courses:
        # When someone said "2 want parotta, 4 want biryani", those ARE
        # the dishes. Spare budget is not a licence to add a third thing
        # nobody asked for - that's the assumption this whole rewrite is
        # about not making.
        if course.slot == "dinner" and req.dinner_requests:
            continue
        chosen = {i.id for i, _ in course.items}
        for opt in course.options:
            if opt.id in chosen or opt.price > leftover:
                continue
            if req.veg_only and not opt.veg:
                continue
            if set(opt.tags) & set(req.avoid_tags):
                continue
            if best is None or opt.price > best[1].price:
                best = (course, opt)
    return best


def course_subagent(slot: str, req: Request, budget_share: int) -> Course:
    """One helper, one job: propose items for its own slot.

    Small and narrow on purpose. It does not know about the other courses
    and it does not know the total budget - it is handed a share. The
    planner owns the whole picture.
    """
    platform = tools.platform_for(slot)
    course = Course(slot=slot, platform=platform, target=req.slots[slot])

    options = tools.search(
        slot=slot,
        veg_only=req.veg_only,
        avoid_tags=req.avoid_tags,
        platform=platform,
    )
    if not options:  # relax platform if nothing fits
        options = tools.search(slot=slot, veg_only=req.veg_only,
                               avoid_tags=req.avoid_tags)
        if options:
            course.platform = options[0].platform

    course.options = options

    # Only honour the per-person split when they actually gave one.
    # Falling through to dinner_plan()'s catch-all entry would buy a
    # single dish for the whole table - which is exactly what
    # compose_dinner() exists to avoid.
    if slot == "dinner" and req.dinner_requests:
        items, problems = pick_items_for_requests(options, req.dinner_requests, budget_share)
        course.items = items
        course.notes = problems
    else:
        course.items = pick_items(options, slot, budget_share, req.guests)

    return course


def build_plan(req: Request) -> Plan:
    """Planner: split the budget, run the subagents, then enforce the
    rules that cross all of them.

    Requires req.budget to be known - call missing_info(req) first and
    ask the person, rather than defaulting silently. See the 'clarify'
    node in build_graph() for how the CLI/graph path handles this.
    """
    if req.budget is None:
        raise ValueError(
            "Request.budget is None - ask the person before calling "
            "build_plan(). Use missing_info(req) to check first."
        )

    plan = Plan(request=req)

    for slot, share in budget_split(req).items():
        plan.courses.append(course_subagent(slot, req, share))

    plan.courses.sort(key=lambda c: c.target)
    plan = rebalance(plan)
    plan = top_up(plan)
    return plan


def budget_split(req: Request) -> dict[str, int]:
    """How much of the budget each requested course gets.

    Weighted by portions.COURSE_WEIGHT and normalised over only the
    courses actually asked for - so a dinner-only request gets the whole
    budget for dinner, instead of the old code's fixed 25/50/25 that
    quietly assumed three courses existed.
    """
    if not req.slots:
        return {}
    weights = {s: portions.COURSE_WEIGHT.get(s, 1.0) for s in req.slots}
    scale = sum(weights.values()) or 1.0
    return {s: int(req.budget * w / scale) for s, w in weights.items()}


# ---------------------------------------------------------------- parsing


DEFAULT_SLOT_TIMES = {"snacks": -60, "dinner": 0, "dessert": 60}  # minutes vs dinner


def slot_times(slots, anchor: datetime) -> dict[str, datetime]:
    """Turn a list of course names into eat-by times around an anchor.

    Only the requested courses get a time, which is what stops a
    dinner-only request from sprouting a snacks and a dessert course.
    A single requested course sits ON the anchor - if someone asks for
    dessert at 10pm they mean dessert at 10pm, not dessert at 11.
    """
    slots = tuple(slots)
    if len(slots) == 1:
        return {slots[0]: anchor}
    return {s: anchor + timedelta(minutes=DEFAULT_SLOT_TIMES.get(s, 0)) for s in slots}


def parse_time(text: str, now: datetime | None = None) -> datetime | None:
    """Find a clock time in plain English. Returns None when there isn't
    one, so the caller can ask instead of inventing 8pm."""
    now = now or datetime.now()
    t = (text or "").lower()

    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", t)
    if m:
        hour = int(m.group(1)) % 12
        minute = int(m.group(2) or 0)
        if m.group(3) == "pm":
            hour += 12
    else:
        m = re.search(r"\bat\s+(\d{1,2}):(\d{2})\b", t)
        if m:
            hour, minute = int(m.group(1)), int(m.group(2))
        elif re.search(r"\b(tonight|this evening)\b", t):
            hour, minute = 20, 0
        elif re.search(r"\b(lunch|noon|afternoon)\b", t):
            hour, minute = 13, 0
        else:
            return None

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    when = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if when < now:
        when += timedelta(days=1)
    return when


def parse_request(text: str, now: datetime | None = None) -> Request:
    """Turn plain English into a Request.

    Regex first because it is free and predictable. If an LLM is
    available it refines the fuzzy parts - but the regex result is always
    the fallback, so the agent never dies because an API was down.

    Anything not found here stays unknown and gets a *_known flag of
    False, so conversation.next_question() can ask rather than guess.
    """
    from core import conversation

    now = now or datetime.now()
    t = text.lower()

    # "6 friends", "8 people", and also the very common "dinner for 4" /
    # "for 6 of us", which the noun-anchored pattern alone walked past.
    m = re.search(r"(\d+)\s*(?:friends?|people|guests?|of us|adults?|pax|heads?)", t)
    if not m:
        m = re.search(r"\bfor\s+(\d+)\b", t)
    guests_known = bool(m)
    guests = conversation.clamp_guests(int(m.group(1))) if m else 4

    budget: int | None = None
    m = re.search(r"(?:budget|under|max|within|around|about|upto|up to)\D{0,10}(\d{3,6})", t)
    if not m:
        m = re.search(r"(?:rs\.?|₹)\s*(\d{3,6})", t)
    if m:
        budget = conversation.clamp_budget(int(m.group(1)))
        # else stays None - genuinely unknown, not a silent guess.

    veg_guests = 0
    m = re.search(r"(\d+)\s*(?:are\s*)?(?:veg|vegetarian)", t)
    if m:
        veg_guests = int(m.group(1))
    veg_only = veg_guests > 0 or bool(re.search(r"\b(all veg|pure veg|only veg)\b", t))

    avoid: list[str] = []
    if re.search(r"(no spice|hates? spice|not spicy|mild)", t):
        avoid.append("spicy")
    if re.search(r"(no egg|eggless)", t):
        avoid.append("egg")

    dinner_requests = _parse_dish_splits(t)

    # Which courses did they actually ask for? This is the fix for every
    # request becoming a three-course evening.
    requested, slots_confident = conversation.infer_slots(t)

    when = parse_time(t, now=now)
    time_known = when is not None
    anchor = when or now.replace(hour=20, minute=0, second=0, microsecond=0)
    if anchor < now:
        anchor += timedelta(days=1)

    return Request(
        guests=guests,
        budget=budget,
        veg_only=veg_only,
        veg_guests=veg_guests,
        avoid_tags=tuple(avoid),
        slots=slot_times(requested, anchor),
        dinner_requests=dinner_requests,
        raw=text,
        dinner_time=anchor,
        slots_confident=slots_confident,
        guests_known=guests_known,
        time_known=time_known,
    )


def _parse_dish_splits(t: str) -> list[DishRequest]:
    """Catches the plain, common phrasing: '2 want parotta, 3 want
    biryani', '2 people prefer biryani and 3 want parotta'. Deliberately
    narrow - this is exactly the piece Groq's parser (llm.py) should
    replace for anything phrased less predictably. Returns [] when
    nothing matches, which falls back to 'one dish for everyone' via
    Request.dinner_plan().
    """
    pattern = re.compile(
        r"(\d+)\s*(?:people|guests?|of them|of us)?\s*"
        r"(?:want|wants|prefer|prefers|like|likes)\s+"
        r"([a-z][a-z\s]{2,20}?)(?=,|\band\b|$)"
    )
    out = []
    for count_str, dish in pattern.findall(t):
        dish = dish.strip()
        if dish and dish not in ("it", "that", "this"):
            out.append(DishRequest(count=int(count_str), dish_hint=dish))
    return out


# ---------------------------------------------------------------- rendering


def render(plan: Plan) -> str:
    from core import conversation

    req = plan.request
    budget_label = f"budget Rs{req.budget}" if req.budget is not None else "no budget set"
    lines = [
        "",
        "=" * 58,
        f"  PLAN  -  {req.guests} guests  -  {budget_label}",
        "=" * 58,
    ]
    if req.veg_only:
        lines.append(f"  Vegetarian-only (because {req.veg_guests} guest(s) are veg)")
    if req.avoid_tags:
        lines.append(f"  Avoiding: {', '.join(req.avoid_tags)}")

    # Anything we decided for them, said out loud before they approve it.
    for assumed in conversation.summarise_assumptions(req):
        lines.append(f"  NOTE: {assumed} - say so if that's wrong")
    lines.append("")

    for c in plan.courses:
        lines.append(f"  {c.slot.upper()}  -  on the table {c.target:%H:%M}")
        lines.append(
            f"    order at {c.order_at:%H:%M}  "
            f"({c.platform}, eta {c.eta}m + {c.buffer}m buffer)"
        )
        for item, qty in c.items:
            # Real Swiggy dish names run long. Truncate for the column so
            # the price stays where the eye expects it - this is the
            # screen someone approves from, so it has to stay readable.
            name = item.name if len(item.name) <= 34 else item.name[:33] + "…"
            lines.append(f"      {qty} x {name:<34} Rs{item.price * qty:>5}")
        lines.append(f"    {'subtotal':<44} Rs{c.subtotal:>5}")
        lines.append("")

    lines.append(f"  {'TOTAL':<44} Rs{plan.total:>5}")
    if req.budget is not None:
        lines.append(f"  {'left over':<44} Rs{req.budget - plan.total:>5}")

    problems = violations(plan)
    if problems:
        lines.append("")
        lines.append("  PROBLEMS:")
        lines += [f"    - {p}" for p in problems]

    if plan.notes:
        lines.append("")
        lines.append("  Decisions made:")
        lines += [f"    - {n}" for n in plan.notes]

    lines.append("=" * 58)
    return "\n".join(lines)


# ---------------------------------------------------------------- 4. graph


def build_graph():
    """LangGraph wiring. Imported lazily so evals.py doesn't need it.

    guard -> parse -> clarify -> plan -> [HUMAN APPROVAL] -> execute

    'clarify' is the actual fix for silently defaulting the budget to
    2000: if parse_request couldn't find one, the graph PAUSES and asks,
    the same interrupt() mechanism the approval gate already uses.
    """
    import logging
    from typing import TypedDict
    from langgraph.graph import END, StateGraph
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import interrupt

    from core import guardrail

    # The in-memory checkpointer logs a warning every time it deserializes
    # one of our own dataclasses (Request/Course/Plan/DishRequest/MenuItem)
    # from a checkpoint - harmless, they're ours, not untrusted input. This
    # goes through Python's logging module, not warnings.warn(), so a
    # warnings.filterwarnings() call does nothing here - silence the
    # specific logger instead. If you move to a real database checkpointer
    # later, store plain dicts and this goes away on its own.
    logging.getLogger("langgraph.checkpoint.serde.jsonplus").setLevel(logging.ERROR)

    from core import conversation

    class State(TypedDict, total=False):
        text: str
        blocked: str
        request: Request
        asked: tuple[str, ...]
        plan: Plan
        approved: bool
        receipt: list[str]

    def guard_node(state):
        v = guardrail.check(state["text"])
        return {} if v.allowed else {"blocked": v.reason}

    def parse_node(state):
        try:
            from integrations import llm
            return {"request": llm.parse_request_llm(state["text"]), "asked": ()}
        except ImportError:
            return {"request": parse_request(state["text"]), "asked": ()}

    def clarify_node(state):
        """Ask for what we genuinely don't know - courses first, then
        headcount, then time, then budget. One question per pass, capped
        at conversation.MAX_QUESTIONS, then we proceed with assumptions
        stated in the plan rather than interrogating anyone.
        """
        req = state["request"]
        asked = tuple(state.get("asked") or ())

        question = conversation.next_question(req, asked)
        if question is None:
            return {"request": req, "asked": asked}

        answer = interrupt({
            "question": question.prompt(),
            "why": question.why,
            "field": question.field,
        })

        # A reply is user input like any other. The first message goes
        # through the guardrail; without this, so does everything after
        # it - an injection attempt typed at the budget prompt would
        # otherwise sail straight past.
        verdict = guardrail.check_answer(str(answer))
        if not verdict.allowed:
            return {"blocked": verdict.reason}

        req = conversation.apply_answer(req, question, str(answer))
        return {"request": req, "asked": asked + (question.field,)}

    def after_clarify_loop(state):
        """Keep asking while there's something worth asking and we
        haven't hit the cap."""
        if state.get("blocked"):
            return END
        req = state["request"]
        asked = tuple(state.get("asked") or ())
        if conversation.next_question(req, asked) is not None:
            return "clarify"
        return "plan" if req.budget is not None else "no_budget"

    def no_budget_node(state):
        """Budget is the one thing we will not invent. Everything else
        has a defensible default; someone's spending limit does not."""
        return {"blocked": "I still don't have a budget, and I won't guess "
                           "one - it's your money. Run again with a number, "
                           "e.g. 'dinner for 6, budget 2000'."}

    def plan_node(state):
        return {"plan": build_plan(state["request"])}

    def approval_node(state):
        """Stops here. Nothing happens until a human replies."""
        answer = interrupt({
            "plan": render(state["plan"]),
            "question": "Go ahead with this plan? (yes / no)",
            "field": "approval",
        })
        ok = str(answer).strip().lower() in {"y", "yes", "ok", "confirm", "go"}
        return {"approved": ok}

    def execute_node(state):
        """Dry run. Spread fills carts; it does not place orders. The
        live path (app/execute_live.py) adds to a real Swiggy cart and
        stops there too - see integrations/safety.py."""
        plan = state["plan"]
        receipt = []
        for c in plan.courses:
            receipt.append(
                f"[DRY RUN] {c.order_at:%H:%M} -> {c.platform}: "
                f"{len(c.items)} item(s), Rs{c.subtotal}"
            )
        return {"receipt": receipt}

    def after_guard(state):
        return END if state.get("blocked") else "parse"

    def after_approval(state):
        return "execute" if state.get("approved") else END

    g = StateGraph(State)
    g.add_node("guard", guard_node)
    g.add_node("parse", parse_node)
    g.add_node("clarify", clarify_node)
    g.add_node("no_budget", no_budget_node)
    g.add_node("plan", plan_node)
    g.add_node("approval", approval_node)
    g.add_node("execute", execute_node)

    g.set_entry_point("guard")
    g.add_conditional_edges("guard", after_guard, {"parse": "parse", END: END})
    g.add_edge("parse", "clarify")
    # clarify loops back into itself until there's nothing left worth
    # asking - that's what makes this a conversation rather than one
    # hardcoded budget question.
    g.add_conditional_edges("clarify", after_clarify_loop,
                            {"clarify": "clarify", "plan": "plan",
                             "no_budget": "no_budget", END: END})
    g.add_edge("no_budget", END)
    g.add_edge("plan", "approval")
    g.add_conditional_edges("approval", after_approval,
                            {"execute": "execute", END: END})
    g.add_edge("execute", END)

    return g.compile(checkpointer=MemorySaver())


# ---------------------------------------------------------------- 5. cli


def main() -> None:
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        text = input("What's the plan? > ").strip()

    try:
        from langgraph.types import Command
        graph = build_graph()
        cfg = {"configurable": {"thread_id": "spread-1"}}

        result = graph.invoke({"text": text}, cfg)

        while True:
            if result.get("blocked"):
                print("\n" + result["blocked"] + "\n")
                return

            state = graph.get_state(cfg)
            if not state.next:
                break  # graph reached the end - nothing left to ask

            value = state.tasks[0].interrupts[0].value
            if "plan" in value:
                print(value["plan"])
            print()
            print(value["question"])
            if value.get("why"):
                print(f"  ({value['why']})")
            try:
                answer = input("  > ")
            except EOFError:
                # Piped or scripted input ran out mid-conversation. Take
                # the offered default rather than dumping a traceback.
                print("(no input - using the default)")
                answer = ""
            result = graph.invoke(Command(resume=answer), cfg)

        if result.get("receipt"):
            print("\nPlan confirmed (dry run - nothing was bought, no cart touched):")
            for line in result["receipt"]:
                print("  " + line)
            print("\nTo fill a REAL Swiggy cart with this, use:")
            print("  python -m app.run_live_plan \"<your request>\"")
            print("Even that stops at the cart. Spread never places an order.")
        else:
            print("\nCancelled. Nothing ordered.")

    except ImportError:
        # LangGraph not installed - still show the plan, ask for budget
        # directly instead of the interrupt() mechanism
        from core import guardrail
        v = guardrail.check(text)
        if not v:
            print("\n" + v.reason + "\n")
            return
        req = parse_request(text)
        if req.budget is None:
            answer = input("What's your budget for this? (e.g. 2000) > ")
            m = re.search(r"(\d{3,6})", answer)
            if not m:
                print("\nStill no budget number - run again and include one.\n")
                return
            req.budget = int(m.group(1))
        print(render(build_plan(req)))
        print("\n(Install langgraph to get the approval gate.)")


if __name__ == "__main__":
    main()