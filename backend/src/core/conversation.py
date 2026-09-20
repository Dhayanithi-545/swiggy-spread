"""
conversation.py - what the user actually asked for, and what to ask next.

This file exists because of one bug that was really a product mistake:
every request got snacks AND dinner AND dessert, whatever the person
said. "order dinner for 4 tonight" came back as a three-course evening
and spent their money on two courses they never mentioned.

So there are two jobs here:

  1. infer_slots()   - which courses did they actually ask for?
  2. next_question() - of everything we still don't know, what is the
                       ONE thing worth interrupting them for?

The asking rule, because over-asking is as bad as over-assuming:

  - Infer anything that can be safely inferred.
  - Ask only about things that change the outcome.
  - NEVER invent a budget or a headcount. That's their money and their
    guests - getting it wrong is worse than asking.
  - Cap the questions (MAX_QUESTIONS), then proceed with assumptions
    stated out loud instead of interrogating them.
  - Every question carries a default, so pressing enter is a valid answer.
  - Budget is offered as a range, not demanded as a number.

Pure functions, no LLM, no network. The LLM (llm.py) can produce a
better Request than the regex does, but the decision about what is
still missing is made here, the same way, every time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

ALL_SLOTS = ("snacks", "dinner", "dessert")

# How many things we'll interrupt for before giving up and proceeding
# with stated assumptions.
MAX_QUESTIONS = 3

# A parse bug turning "3000" into "300000" must not build an absurd cart.
# Nobody plans a house gathering on Swiggy for more than this.
MAX_BUDGET = 100_000
MIN_BUDGET = 100

# Same idea for the guest count.
MAX_GUESTS = 100


# ------------------------------------------------------------ slot inference

SLOT_WORDS = {
    "snacks": (
        r"\bsnacks?\b", r"\bstarters?\b", r"\bappetiz?ers?\b", r"\bchips\b",
        r"\bnibbles?\b", r"\bfinger food\b", r"\bchakna\b", r"\bnamkeen\b",
    ),
    "dinner": (
        r"\bdinner\b", r"\blunch\b", r"\bmeal\b", r"\bmains?\b", r"\bfood\b",
        r"\bbiryani\b", r"\bcurry\b", r"\bthali\b", r"\bpizza\b", r"\beat\b",
        r"\bsupper\b", r"\bfeast\b",
    ),
    "dessert": (
        r"\bdessert", r"\bsweets?\b", r"\bcake\b", r"\bice cream\b",
        r"\bgulab jamun\b", r"\bpastry\b", r"\bpastries\b", r"\bbrownie",
        r"\bhalwa\b", r"\bkheer\b", r"\brasmalai\b",
    ),
}

# Phrases that genuinely mean "the whole evening" - only these expand to
# all three courses without asking.
WHOLE_EVENING = (
    r"\bwhole (evening|night|thing)\b",
    r"\bfull (spread|meal|course|evening)\b",
    r"\beverything\b",
    r"\bthree courses?\b",
    r"\b3 courses?\b",
    r"\bsnacks?,? (and )?dinner,? (and )?dessert",
    r"\bstart to finish\b",
    r"\bsort (it|everything) out\b",
    r"\bplan the (evening|night|party)\b",
)

# Words that say "this is a gathering" without saying which courses.
# These make the courses question worth asking; on their own they do
# NOT mean all three.
GATHERING = (
    r"\bpart(y|ies)\b", r"\bgathering\b", r"\bget.?together\b",
    r"\bfriends? (are )?(coming|over)\b", r"\bpeople (are )?coming\b",
    r"\bhaving (people|friends|guests)\b", r"\bhost(ing)?\b",
    r"\bcelebrat", r"\bbirthday\b", r"\banniversar",
)


def infer_slots(text: str) -> tuple[tuple[str, ...], bool]:
    """Which courses did they ask for?

    Returns (slots, confident).

    confident=False means we guessed and should check. The caller decides
    whether to ask - a request with an explicit "dinner" in it is
    confident; "6 friends coming over" is not.
    """
    t = (text or "").lower()

    if _any(t, WHOLE_EVENING):
        return ALL_SLOTS, True

    named = tuple(s for s in ALL_SLOTS if _any(t, SLOT_WORDS[s]))

    if named:
        # They named at least one course. Take them at their word - this
        # is the case the old code got wrong by bolting on two more.
        return named, True

    if _any(t, GATHERING):
        # A gathering with no course named. Could be anything. Worth one
        # question; dinner is the sane fallback if they don't answer.
        return ("dinner",), False

    # Nothing to go on at all.
    return ("dinner",), False


# The numbered menu shown with the courses question, and what each entry
# means. Kept next to the parser so the list the user sees and the list
# we read back can't drift apart.
COURSE_CHOICES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("snacks only", ("snacks",)),
    ("dinner only", ("dinner",)),
    ("dessert only", ("dessert",)),
    ("the whole evening (snacks, dinner, dessert)", ALL_SLOTS),
)


def parse_slots_answer(answer: str) -> tuple[str, ...]:
    """Read a reply to the courses question. Accepts a menu number
    ('2'), a course name ('dinner'), several ('snacks and dessert'),
    or 'all' / 'everything'."""
    a = (answer or "").strip().lower()
    if not a:
        return ()

    if re.fullmatch(r"\s*(all|everything|whole evening)\s*", a):
        return ALL_SLOTS

    # A single menu number picks that row outright.
    m = re.fullmatch(r"\s*(\d+)\s*", a)
    if m:
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(COURSE_CHOICES):
            return COURSE_CHOICES[idx][1]
        return ()

    picked = {s for s in ALL_SLOTS if _any(a, SLOT_WORDS[s])}

    # Several numbers, e.g. "1 3" or "1,3".
    for n in re.findall(r"\d+", a):
        idx = int(n) - 1
        if 0 <= idx < len(COURSE_CHOICES):
            picked.update(COURSE_CHOICES[idx][1])

    return tuple(s for s in ALL_SLOTS if s in picked)


# ------------------------------------------------------------ questions


@dataclass(frozen=True)
class Question:
    """One thing to ask, with everything the caller needs to render it
    and to interpret the answer."""
    field: str                      # "courses" | "budget" | "guests" | "time"
    text: str                       # what to show the person
    default: str = ""               # used when they just press enter
    options: tuple[str, ...] = ()   # shown as a numbered list if present
    why: str = ""                   # one line: why we're asking

    def prompt(self) -> str:
        lines = [self.text]
        for i, opt in enumerate(self.options, 1):
            lines.append(f"    {i}. {opt}")
        if self.default:
            lines.append(f"  (enter = {self.default})")
        return "\n".join(lines)


@dataclass
class Gaps:
    """What we still don't know about a request, and what we assumed."""
    questions: list[Question] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


def next_question(req, asked: tuple[str, ...] = ()) -> Question | None:
    """The single most valuable thing we don't know, or None.

    Priority order is deliberate - each answer changes the answers below
    it. Courses decide what we search for at all. Guests decide portions
    AND the budget we'd suggest. Budget is last because we can quote a
    sensible range once we know the first two.
    """
    if len(asked) >= MAX_QUESTIONS:
        return None

    if "courses" not in asked and not getattr(req, "slots_confident", True):
        return Question(
            field="courses",
            text="  What should I sort out?",
            options=tuple(label for label, _ in COURSE_CHOICES),
            default="dinner only",
            why="I don't want to order courses you didn't ask for.",
        )

    if "guests" not in asked and not getattr(req, "guests_known", True):
        return Question(
            field="guests",
            text="  How many people am I feeding?",
            default="4",
            why="Portions and the budget I'd suggest both hang off this.",
        )

    if "time" not in asked and not getattr(req, "time_known", True):
        return Question(
            field="time",
            text="  What time should the food be on the table? (e.g. 8pm)",
            default="8pm",
            why="I work backwards from this to decide when to order.",
        )

    if "budget" not in asked and req.budget is None:
        from core import portions

        low, high = portions.budget_range(req.guests, req.slots)
        mid = portions.suggest_budget(req.guests, req.slots)
        courses = " + ".join(req.slots)
        return Question(
            field="budget",
            text=(f"  What's your budget? For {req.guests} people and "
                  f"{courses}, Rs{low}-{high} is a comfortable spread."),
            default=str(mid),
            why="I hold this across every cart, so I need a real number.",
        )

    return None


def apply_answer(req, question: Question, answer: str, now=None):
    """Fold one answer back into the Request. Returns the Request.

    An empty answer means 'use the default you offered' - that's why
    every Question carries one. A junk answer falls back to the default
    too, rather than looping on the same question, which is the classic
    way these flows trap people.
    """
    from core import agent

    raw = (answer or "").strip()
    text = raw or question.default

    if question.field == "courses":
        slots = parse_slots_answer(text) or parse_slots_answer(question.default)
        if slots:
            req.slots = agent.slot_times(slots, req.dinner_time)
            req.slots_confident = True

    elif question.field == "guests":
        m = re.search(r"\d+", text)
        if m:
            req.guests = clamp_guests(int(m.group()))
            req.guests_known = True

    elif question.field == "time":
        when = agent.parse_time(text, now=now)
        if when:
            req.dinner_time = when
            req.slots = agent.slot_times(tuple(req.slots), when)
            req.time_known = True

    elif question.field == "budget":
        m = re.search(r"\d[\d,]*", text)
        if m:
            req.budget = clamp_budget(int(m.group().replace(",", "")))

    return req


def run_clarify_loop(req, ask, *, now=None):
    """Ask until there's nothing worth asking, then hand the Request back.

    `ask` is a callable taking a Question and returning the person's
    reply as a string - the terminal passes input(), tests pass a list.
    Keeping the loop here rather than in each CLI means the live path and
    the mock path ask the same things in the same order, and it means the
    loop is testable without a terminal.

    Returns (request, blocked_reason). blocked_reason is non-empty if a
    reply tripped the guardrail - replies are user input too.
    """
    from core import guardrail

    asked: tuple[str, ...] = ()
    while True:
        question = next_question(req, asked)
        if question is None:
            return req, ""

        answer = ask(question)

        verdict = guardrail.check_answer(str(answer))
        if not verdict.allowed:
            return req, verdict.reason

        req = apply_answer(req, question, str(answer), now=now)
        asked = asked + (question.field,)


def clamp_budget(value: int) -> int:
    """A budget outside this range is a parse bug, not a rich customer."""
    return max(MIN_BUDGET, min(MAX_BUDGET, int(value)))


def clamp_guests(value: int) -> int:
    return max(1, min(MAX_GUESTS, int(value)))


def summarise_assumptions(req) -> list[str]:
    """What we decided for them, said out loud. Shown above the plan so
    nothing is silently assumed - the fix for the old behaviour, which
    quietly planned three courses and a 2000 budget."""
    out = []
    if not getattr(req, "slots_confident", True):
        out.append(f"assumed you wanted {' + '.join(req.slots)}")
    if not getattr(req, "guests_known", True):
        out.append(f"assumed {req.guests} people")
    if not getattr(req, "time_known", True):
        out.append(f"assumed {req.dinner_time:%H:%M} on the table")
    return out


def _any(text: str, patterns) -> bool:
    return any(re.search(p, text) for p in patterns)
