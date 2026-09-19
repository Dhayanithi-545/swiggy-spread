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
class Request:
    """What the user actually wants."""
    guests: int = 4
    budget: int = 2000
    veg_only: bool = False          # true if ANY guest is vegetarian-only
    veg_guests: int = 0
    avoid_tags: tuple[str, ...] = ()
    slots: dict[str, datetime] = field(default_factory=dict)  # slot -> eat-by time
    raw: str = ""


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


def pick_items(
    options: list[MenuItem], slot: str, budget_share: int, guests: int
) -> list[tuple[MenuItem, int]]:
    """The actual choosing logic - given a list of candidates and a
    budget slice, pick a few. Pulled out on its own so both the mock
    subagent and the live one (in live_agent.py) make the same
    decision the same way, off whatever options they were handed.
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
    course.items = pick_items(options, slot, budget_share, req.guests)
    return course


def build_plan(req: Request) -> Plan:
    """Planner: split the budget, run the subagents, then enforce the
    rules that cross all of them."""
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

    budget = 2000
    m = re.search(r"(?:budget|under|max|within)\D{0,10}(\d{3,6})", t)
    if m:
        budget = int(m.group(1))

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
        raw=text,
    )


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

    guard -> parse -> plan -> [HUMAN APPROVAL] -> execute
    """
    import warnings
    from typing import TypedDict
    from langgraph.graph import END, StateGraph
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import interrupt

    import guardrail

    # The in-memory checkpointer warns about pickling our own dataclasses
    # (Request/Course/Plan). Harmless here - they're ours, not user input.
    # If you move to a real database checkpointer, store plain dicts instead.
    warnings.filterwarnings("ignore", message="Deserializing unregistered type")

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
        return {"request": parse_request(state["text"])}

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

    def after_approval(state):
        return "execute" if state.get("approved") else END

    g = StateGraph(State)
    g.add_node("guard", guard_node)
    g.add_node("parse", parse_node)
    g.add_node("plan", plan_node)
    g.add_node("approval", approval_node)
    g.add_node("execute", execute_node)

    g.set_entry_point("guard")
    g.add_conditional_edges("guard", after_guard, {"parse": "parse", END: END})
    g.add_edge("parse", "plan")
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

        if result.get("blocked"):
            print("\n" + result["blocked"] + "\n")
            return

        # paused at the approval gate
        state = graph.get_state(cfg)
        if state.next:
            print(state.tasks[0].interrupts[0].value["plan"])
            answer = input("\nPlace these orders? (yes/no) > ")
            result = graph.invoke(Command(resume=answer), cfg)

        if result.get("receipt"):
            print("\nOrders (dry run - nothing was actually bought):")
            for line in result["receipt"]:
                print("  " + line)
        else:
            print("\nCancelled. Nothing ordered.")

    except ImportError:
        # LangGraph not installed - still show the plan
        import guardrail
        v = guardrail.check(text)
        if not v:
            print("\n" + v.reason + "\n")
            return
        print(render(build_plan(parse_request(text))))
        print("\n(Install langgraph to get the approval gate.)")


if __name__ == "__main__":
    main()