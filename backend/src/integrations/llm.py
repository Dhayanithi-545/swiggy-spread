"""
llm.py - the Groq-backed parser. Optional. Falls back to the regex
parser in agent.py if there's no API key, or if the call fails for any
reason - the agent should never go down because an external API did.

Why this exists: regex can find "budget 2000" in a sentence. It cannot
parse "one of us wants something light, my friend's allergic to nuts,
keep it under what feels reasonable for six people." That needs actual
language understanding - so this is the ONE place in Spread that calls
an LLM, and only for understanding the request, never for the budget
math, timing, or rebalancing logic in agent.py.

Model-agnostic on purpose (Swiggy's own team said this in the
Codebasics interview - don't tie yourself to one provider): this talks
to Groq's OpenAI-compatible chat endpoint over plain HTTP. Swapping
providers later means changing BASE_URL and MODEL, not rewriting logic.

NOT TESTED LIVE from this environment - api.groq.com isn't reachable
from here. Written carefully against Groq's documented API shape, but
you're the first one to actually run this against a real key.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import httpx

# so this runs both as `python -m <pkg>.<mod>` and as `python <pkg>/<mod>.py`
if __package__ in (None, ""):
    import pathlib
    import sys as _sys
    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from core import agent

try:
    from dotenv import load_dotenv
    # Point at src/.env explicitly. Bare load_dotenv() searches upward from
    # the CURRENT WORKING DIRECTORY, so it silently found nothing whenever
    # you ran from backend/ or the repo root.
    load_dotenv(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
    ))
except ImportError:
    pass  # python-dotenv not installed - fall back to real env vars only

BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You turn a person's plain-English request for a group meal into JSON.

Return ONLY valid JSON, no other text, matching exactly this shape:
{
  "guests": <int>,
  "budget": <int or null - null if genuinely not mentioned, never guess a number>,
  "veg_only": <bool - true if ANY guest is vegetarian>,
  "veg_guests": <int - how many are vegetarian, 0 if not mentioned>,
  "avoid_tags": [<string>, ...]  // e.g. "spicy", "egg" - only if explicitly disliked
  "dinner_requests": [
    {"count": <int>, "dish_hint": <string or null>, "veg_only": <bool>}, ...
  ]  // one entry per distinct dinner preference. If everyone wants
     // the same thing (or nothing specific), return ONE entry with
     // count = guests and dish_hint = null or the one dish mentioned.
  "dinner_time": <string like "20:00" or null if not mentioned>
}

Rules:
- Never invent a budget. If it's not stated, budget MUST be null.
- dinner_requests' counts should add up to guests when the person
  clearly split the group; if they didn't split it, use one entry.
- dish_hint should be a short food word ("biryani", "parotta"), not a
  full sentence.
"""


def parse_request_llm(text: str, now: datetime | None = None) -> agent.Request:
    """Tries Groq first, falls back to the regex parser in agent.py on
    ANY failure - missing key, network error, bad JSON, whatever. The
    fallback is not a degraded mode to apologize for; it's the same
    parser that's been eval-tested this whole project."""
    fallback = agent.parse_request(text, now=now)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return fallback

    try:
        data = _call_groq(text, api_key)
        return _to_request(data, text, now or datetime.now(), fallback)
    except Exception:
        # Deliberately broad: a parsing helper going down should never
        # take the whole agent down with it. Silent fallback here is
        # correct - the regex result is a real, tested answer, not a
        # placeholder.
        return fallback


def _call_groq(text: str, api_key: str) -> dict:
    response = httpx.post(
        BASE_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        },
        timeout=15,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def _to_request(data: dict, raw_text: str, now: datetime, fallback: agent.Request) -> agent.Request:
    """Converts Groq's JSON into our own Request/DishRequest - and
    falls back field-by-field to the regex parser's result for
    anything Groq left out or got a weird type for, rather than
    trusting the LLM's output blindly."""
    from datetime import timedelta

    guests = int(data.get("guests") or fallback.guests)
    budget = data.get("budget")
    budget = int(budget) if isinstance(budget, (int, float)) else None

    veg_only = bool(data.get("veg_only", fallback.veg_only))
    veg_guests = int(data.get("veg_guests") or fallback.veg_guests)
    avoid_tags = tuple(data.get("avoid_tags") or fallback.avoid_tags)

    dinner_requests = []
    for dr in data.get("dinner_requests") or []:
        try:
            dinner_requests.append(agent.DishRequest(
                count=int(dr["count"]),
                dish_hint=dr.get("dish_hint") or None,
                veg_only=bool(dr.get("veg_only", False)),
            ))
        except (KeyError, TypeError, ValueError):
            continue  # skip a malformed entry rather than crash the whole parse

    dinner_time = data.get("dinner_time")
    if dinner_time:
        try:
            hour, minute = map(int, dinner_time.split(":"))
            dinner = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if dinner < now:
                dinner += timedelta(days=1)
            slots = {s: dinner + timedelta(minutes=off)
                     for s, off in agent.DEFAULT_SLOT_TIMES.items()}
        except (ValueError, TypeError):
            slots = fallback.slots
    else:
        slots = fallback.slots

    return agent.Request(
        guests=guests,
        budget=budget,
        veg_only=veg_only,
        veg_guests=veg_guests,
        avoid_tags=avoid_tags,
        slots=slots,
        dinner_requests=dinner_requests,
        raw=raw_text,
    )


if __name__ == "__main__":
    import sys
    text = " ".join(sys.argv[1:]) or input("Try a sentence > ")
    req = parse_request_llm(text)
    print(f"guests={req.guests} budget={req.budget} veg_only={req.veg_only}")
    print(f"dinner_requests={req.dinner_requests}")
    if not os.getenv("GROQ_API_KEY"):
        print("\n(No GROQ_API_KEY set - this used the regex fallback, not Groq.)")