"""
portions.py - how much food a group of people actually needs.

The old rule was one line: portions_needed(guests, serves=2). For six
guests that returned 3, and the planner dutifully bought three of the
same dish. Nobody feeds six people three parottas and calls it dinner.

The numbers here come from Indian catering guidance, not from taste:

  - one curry per 4-5 guests (variety, not volume)
  - ~1.5 breads per person
  - one rice/biryani portion per 2-3 people
  - 2-3 appetiser pieces per person
  - 1-2 dessert pieces per person
  - Rs200-300 per head is a comfortable mid-range spread, no alcohol

Everything is a plain function of guest count. No LLM, no network - so
evals can pin these exactly, and a plan for six people is the same plan
every time you run it.
"""

from __future__ import annotations

from dataclasses import dataclass

# Rupees per head for a comfortable mid-range spread, used to SUGGEST a
# budget when the person didn't name one. Never used as a default -
# suggesting "about 1800 for six?" and being told "no, 1200" is fine;
# silently planning to 1800 is not.
RUPEES_PER_HEAD = 250

# What each course is worth as a share of a per-head budget. A dinner-only
# request should not be priced as if it were a whole evening.
COURSE_WEIGHT = {
    "snacks": 0.3,
    "dinner": 1.0,
    "dessert": 0.35,
}

# How a dinner should be composed, in order of importance. Each entry is
# (role, how many guests one portion covers). The planner walks this list
# and fills what the budget allows, so a small group gets a main and a
# bread while a big group also gets rice and a second main.
DINNER_COMPOSITION = [
    ("main", 4),      # one curry per 4-5 guests
    ("rice", 3),      # biryani / fried rice, one per 2-3
    ("bread", 2),     # ~1.5 per person, sold in packs of 2-4
    ("main", 5),      # a second, different main once the group is big
    ("side", 6),      # raita, salad - only for larger groups
]

# Words that identify what role a dish plays. Deliberately crude keyword
# matching: it runs on real Swiggy menu names we do not control, and a
# wrong guess costs variety, not correctness. An LLM picker would do this
# better and is the obvious upgrade - see CLAUDE.md.
ROLE_WORDS = {
    "rice": ("biryani", "rice", "pulao", "pulav", "fried rice", "khichdi"),
    "bread": ("naan", "roti", "paratha", "parotta", "kulcha", "chapati",
              "rumali", "bread", "poori", "puri"),
    "side": ("raita", "salad", "papad", "curd", "pickle", "chutney"),
    "main": ("curry", "masala", "gravy", "paneer", "chicken", "mutton",
             "dal", "kofta", "korma", "tikka", "butter", "kadai", "handi"),
}


@dataclass(frozen=True)
class Portions:
    """How many distinct items to buy, and how many of each."""
    distinct_items: int
    qty_each: int

    @property
    def total_units(self) -> int:
        return self.distinct_items * self.qty_each


def role_of(name: str) -> str:
    """Which part of a meal this dish plays. Falls back to 'main' - an
    unrecognised dish is more likely a curry than a papad, and treating
    it as a main is the less wrong failure."""
    n = (name or "").lower()
    # Check bread/rice/side before main: "butter naan" contains "butter",
    # which is a main word, but it is obviously a bread.
    for role in ("bread", "rice", "side"):
        if any(w in n for w in ROLE_WORDS[role]):
            return role
    if any(w in n for w in ROLE_WORDS["main"]):
        return "main"
    return "main"


def dinner_slots(guests: int) -> list[tuple[str, int]]:
    """What a dinner for this many people should be made of.

    Returns (role, quantity) pairs in priority order. The planner buys
    down this list until the money runs out, so the first entries are
    the ones a table genuinely cannot do without.
    """
    guests = max(1, guests)
    out: list[tuple[str, int]] = []
    for role, covers in DINNER_COMPOSITION:
        qty = _ceil_div(guests, covers)
        if qty >= 1:
            out.append((role, qty))
    return out


def snack_portions(guests: int) -> Portions:
    """2-3 pieces per person. Packaged Instamart snacks serve roughly
    three, and two different things on a table beats six of one."""
    packs = max(1, _ceil_div(guests, 3))
    distinct = 2 if guests >= 3 else 1
    return Portions(distinct_items=distinct, qty_each=max(1, _ceil_div(packs, distinct)))


def dessert_portions(guests: int) -> Portions:
    """1-2 pieces per person. Dessert tubs and boxes serve about four."""
    packs = max(1, _ceil_div(guests, 4))
    distinct = 2 if guests >= 5 else 1
    return Portions(distinct_items=distinct, qty_each=max(1, _ceil_div(packs, distinct)))


def portions_for(slot: str, guests: int) -> Portions:
    if slot == "snacks":
        return snack_portions(guests)
    if slot == "dessert":
        return dessert_portions(guests)
    # dinner is composed by role, not by a flat count - see dinner_slots()
    slots = dinner_slots(guests)
    return Portions(distinct_items=len(slots), qty_each=1)


def suggest_budget(guests: int, slots) -> int:
    """A number to OFFER the person, never one to assume.

    Scaled by which courses they actually asked for: dinner for four is
    not priced like a whole evening for four. Rounded to the nearest 100
    because '1847' reads like a machine talking.
    """
    guests = max(1, guests)
    weight = sum(COURSE_WEIGHT.get(s, 1.0) for s in slots) or 1.0
    # A dinner-only request is the reference point: weight 1.0 -> per-head.
    raw = guests * RUPEES_PER_HEAD * weight
    return int(round(raw / 100.0) * 100)


def budget_range(guests: int, slots) -> tuple[int, int]:
    """The spread to quote when asking, e.g. 'somewhere around 1500-2200'."""
    mid = suggest_budget(guests, slots)
    return int(mid * 0.8 // 100 * 100), int(mid * 1.25 // 100 * 100)


def _ceil_div(a: int, b: int) -> int:
    return -(-a // max(1, b))


# Kept because evals and older call sites use it, and because "how many
# portions of one dish" is still the right question for a single-dish
# request ("3 want biryani").
def portions_needed(guests: int, per_item_serves: int = 2) -> int:
    """Round up. 5 guests, serves-2 dishes -> 3 portions."""
    return max(1, _ceil_div(guests, per_item_serves))
