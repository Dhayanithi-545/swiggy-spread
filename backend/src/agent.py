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

import tools
from tools import MenuItem

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
    """What the user actually wants."""
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
    Used by the graph to decide whether to ask a question instead of
    silently proceeding - see the 'clarify' node in build_graph()."""
    gaps = []
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

    if plan.total > req.budget:
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


def pick_items(
    options: list[MenuItem], slot: str, budget_share: int, guests: int
) -> list[tuple[MenuItem, int]]:
    """The single-dish version - still used for snacks/dessert, where
    'one person wants a different snack than another' hasn't come up
    yet. Pulled out on its own so mock and live data sources make the
    same decision the same way.
    """
    if not options:
        return []

    items: list[tuple[MenuItem, int]] = []
    spent = 0
    want = 2  # variety, not volume

    for item in sorted(options, key=lambda o: o.price, reverse=True):
        if len(items) >= want:
            break
        qty = portions_needed(guests) if slot == "dinner" else 1
        cost = item.price * qty
        if spent + cost <= budget_share:
            items.append((item, qty))
            spent += cost

    if not items:  # budget share too small - take the cheapest anyway
        cheapest = min(options, key=lambda o: o.price)
        items.append((cheapest, 1))

    return items


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

    if slot == "dinner":
        items, problems = pick_items_for_requests(options, req.dinner_plan(), budget_share)
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

    # Rough split. Dinner is the anchor, so it gets the most.
    weights = {"snacks": 0.25, "dinner": 0.5, "dessert": 0.25}
    active = {s: weights.get(s, 1 / len(req.slots)) for s in req.slots}
    scale = sum(active.values())

    for slot in req.slots:
        share = int(req.budget * active[slot] / scale)
        plan.courses.append(course_subagent(slot, req, share))

    plan.courses.sort(key=lambda c: c.target)
    plan = rebalance(plan)
    return plan


# ---------------------------------------------------------------- parsing


DEFAULT_SLOT_TIMES = {"snacks": -60, "dinner": 0, "dessert": 60}  # minutes vs dinner


def parse_request(text: str, now: datetime | None = None) -> Request:
    """Turn plain English into a Request.

    Regex first because it is free and predictable. If an LLM is
    available it refines the fuzzy parts - but the regex result is always
    the fallback, so the agent never dies because an API was down.
    """
    now = now or datetime.now()
    t = text.lower()

    guests = 4
    m = re.search(r"(\d+)\s*(friends?|people|guests?|of us)", t)
    if m:
        guests = int(m.group(1))

    budget: int | None = None
    m = re.search(r"(?:budget|under|max|within)\D{0,10}(\d{3,6})", t)
    if m:
        budget = int(m.group(1))
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

    # dinner time
    hour, minute = 20, 0
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", t)
    if m:
        hour = int(m.group(1)) % 12
        minute = int(m.group(2) or 0)
        if m.group(3) == "pm":
            hour += 12
    dinner = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if dinner < now:
        dinner += timedelta(days=1)

    slots = {s: dinner + timedelta(minutes=off)
             for s, off in DEFAULT_SLOT_TIMES.items()}

    return Request(
        guests=guests,
        budget=budget,
        veg_only=veg_only,
        veg_guests=veg_guests,
        avoid_tags=tuple(avoid),
        slots=slots,
        dinner_requests=dinner_requests,
        raw=text,
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
    req = plan.request
    lines = [
        "",
        "=" * 58,
        f"  PLAN  -  {req.guests} guests  -  budget Rs{req.budget}",
        "=" * 58,
    ]
    if req.veg_only:
        lines.append(f"  Vegetarian-only (because {req.veg_guests} guest(s) are veg)")
    if req.avoid_tags:
        lines.append(f"  Avoiding: {', '.join(req.avoid_tags)}")
    lines.append("")

    for c in plan.courses:
        lines.append(f"  {c.slot.upper()}  -  on the table {c.target:%H:%M}")
        lines.append(
            f"    order at {c.order_at:%H:%M}  "
            f"({c.platform}, eta {c.eta}m + {c.buffer}m buffer)"
        )
        for item, qty in c.items:
            lines.append(f"      {qty} x {item.name:<34} Rs{item.price * qty:>5}")
        lines.append(f"    {'subtotal':<44} Rs{c.subtotal:>5}")
        lines.append("")

    lines.append(f"  {'TOTAL':<44} Rs{plan.total:>5}")
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

    import guardrail

    # The in-memory checkpointer logs a warning every time it deserializes
    # one of our own dataclasses (Request/Course/Plan/DishRequest/MenuItem)
    # from a checkpoint - harmless, they're ours, not untrusted input. This
    # goes through Python's logging module, not warnings.warn(), so a
    # warnings.filterwarnings() call does nothing here - silence the
    # specific logger instead. If you move to a real database checkpointer
    # later, store plain dicts and this goes away on its own.
    logging.getLogger("langgraph.checkpoint.serde.jsonplus").setLevel(logging.ERROR)

    class State(TypedDict, total=False):
        text: str
        blocked: str
        request: Request
        plan: Plan
        approved: bool
        receipt: list[str]

    def guard_node(state):
        v = guardrail.check(state["text"])
        return {} if v.allowed else {"blocked": v.reason}

    def parse_node(state):
        try:
            import llm
            return {"request": llm.parse_request_llm(state["text"])}
        except ImportError:
            return {"request": parse_request(state["text"])}

    def clarify_node(state):
        req = state["request"]
        gaps = missing_info(req)
        if not gaps:
            return {}
        answer = interrupt({
            "question": "What's your budget for this? (e.g. 2000)",
            "gaps": gaps,
        })
        m = re.search(r"(\d{3,6})", str(answer))
        if m:
            req.budget = int(m.group(1))
        return {"request": req}

    def clarify_failed_node(state):
        return {"blocked": "Still no budget number - run again and include "
                            "one, e.g. 'budget 2000'."}

    def plan_node(state):
        return {"plan": build_plan(state["request"])}

    def approval_node(state):
        """Stops here. Nothing is ordered until a human replies."""
        answer = interrupt({
            "plan": render(state["plan"]),
            "question": "Place these orders? (yes / no)",
        })
        ok = str(answer).strip().lower() in {"y", "yes", "ok", "confirm"}
        return {"approved": ok}

    def execute_node(state):
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

    def after_clarify(state):
        return "clarify_failed" if missing_info(state["request"]) else "plan"

    def after_approval(state):
        return "execute" if state.get("approved") else END

    g = StateGraph(State)
    g.add_node("guard", guard_node)
    g.add_node("parse", parse_node)
    g.add_node("clarify", clarify_node)
    g.add_node("clarify_failed", clarify_failed_node)
    g.add_node("plan", plan_node)
    g.add_node("approval", approval_node)
    g.add_node("execute", execute_node)

    g.set_entry_point("guard")
    g.add_conditional_edges("guard", after_guard, {"parse": "parse", END: END})
    g.add_edge("parse", "clarify")
    g.add_conditional_edges("clarify", after_clarify,
                            {"plan": "plan", "clarify_failed": "clarify_failed"})
    g.add_edge("clarify_failed", END)
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
            answer = input(f"\n{value['question']} > ")
            result = graph.invoke(Command(resume=answer), cfg)

        if result.get("receipt"):
            print("\nOrders (dry run - nothing was actually bought):")
            for line in result["receipt"]:
                print("  " + line)
        else:
            print("\nCancelled. Nothing ordered.")

    except ImportError:
        # LangGraph not installed - still show the plan, ask for budget
        # directly instead of the interrupt() mechanism
        import guardrail
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