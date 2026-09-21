# Spread

A planning agent that runs a whole gathering, not a single order.

You say:

```
6 friends coming Saturday 8pm, budget 3000, 2 are vegetarian, one hates spice
```

It works out snacks, dinner and dessert, times each order backwards so the
food arrives when you want it, checks the budget across all three carts,
shows you the plan, and fills your Swiggy cart once you say yes.

Or you say:

```
order dinner for 4 tonight
```

and you get dinner for 4. Not dinner plus snacks plus dessert you never
asked for — **the courses come from you**, and when the request is genuinely
ambiguous ("6 friends coming over") it asks instead of assuming.

> **Spread never places an order.** It plans, it prices, it fills your cart,
> and it stops. That's enforced in code, not in a comment — see
> [Never places an order](#never-places-an-order).

Built with LangGraph on top of Swiggy's MCP servers (Food, Instamart, Dineout).

See `PROJECT.md` for why this problem is harder than it looks, and
`CLAUDE.md` for the current build state.

---

## Run it

Everything runs from `backend/src`:

```bash
cd backend/src
pip install -r requirements.txt
python -m core.agent "6 friends Saturday 8pm, budget 3000, 2 are vegetarian"
```

Run the tests:

```bash
python -m tests.evals
```

That should print `223/223 passed`. The evals need **no API key, no network,
no Swiggy token and no real account** — the whole live path runs against an
in-memory Swiggy (`tests/fake_mcp.py`) built from real captured response
shapes. If that table goes red, something is genuinely broken.

And the live path is not just simulated: the full flow — login, plan,
approval, real cart filled and read back — **has been verified against a
real Swiggy account** (2026-09-21).

Try the guardrail on its own:

```bash
python -m core.guardrail
```

---

## What you'll see

When something's missing, it asks — one thing at a time, with a default you
can just press enter through:

```
  What should I sort out?
    1. snacks only
    2. dinner only
    3. dessert only
    4. the whole evening (snacks, dinner, dessert)
  (enter = dinner only)
  (I don't want to order courses you didn't ask for.)
  > 4

  What's your budget? For 6 people and snacks + dinner + dessert,
  Rs2400-3700 is a comfortable spread.
  (enter = 3000)
  > 3000
```

Then the plan:

```
  SNACKS  -  on the table 19:00
    order at 18:30  (instamart, eta 15m + 15m buffer)
      1 x Cheese cubes platter               Rs  420
      1 x Potato chips (family pack)         Rs  120
    subtotal                                     Rs  540

  DINNER  -  on the table 20:00
    order at 19:02  (food, eta 38m + 20m buffer)
      2 x Paneer butter masala               Rs  760
      2 x Veg biryani (serves 2)             Rs  920
    subtotal                                     Rs 1680

  DESSERT  -  on the table 21:00
    order at 20:30  (instamart, eta 15m + 15m buffer)
      1 x Vanilla ice cream tub              Rs  320
      1 x Rasmalai (4 pcs)                   Rs  260
    subtotal                                     Rs  580

  TOTAL                                        Rs 2800
  left over                                    Rs  200

Go ahead with this plan? (yes / no) >
```

Two things worth noticing.

**The timing.** You eat at 20:00, so dinner is ordered at **19:02** — 38
minutes of delivery plus a 20 minute buffer. Snacks come from a faster
platform, so they get a shorter head start. That difference is the whole
project in one screenshot.

**The dinner is a meal.** A main and a rice, in quantities that feed six —
not three of one dish. `core/portions.py` holds the catering numbers
(one curry per 4–5 guests, ~1.5 breads per person) that make that true.

---

## Never places an order

Spread fills your cart and stops. A cart is free and reversible; an order
isn't. This is enforced in two independent layers in
`integrations/safety.py`:

1. The typed wrappers (`place_food_order`, `checkout_instamart`) refuse.
2. **Every single MCP call** is checked against a deny-list and a set of
   regex patterns before it reaches the wire — including the untyped
   passthrough, and including tool names this project has never seen
   (`im_place_order_v2`, `makePayment`). That second layer is the one that
   matters: it means a typo or a careless future edit still can't spend
   your money.

Unlocking it requires an exact environment variable that nothing in the
codebase sets. There is deliberately no flag, CLI option, or function
argument that does it. Fifteen tests in the suite exist to keep it that way.

---

## How it fits together

```
        your request
             |
      [ guardrail check ]   core/guardrail.py - off-topic, injection, fraud
             |
      [ what did they ask for? ]
             |                core/conversation.py - infers the courses,
      [ ask what's missing ]  asks only what changes the outcome, and
             |                never invents a budget or a headcount
        [ PLANNER ]           core/agent.py - owns budget + dietary rules
             |
   ----------+----------
   |         |         |
[snacks]  [dinner]  [dessert]   only the courses you actually wanted
   |         |         |
   ----------+----------
             |
      [ YOU APPROVE ]       nothing happens before this
             |
     [ fill the cart ]      and stop. never an order.
```

The planner never searches for food itself. The subagents never decide.
That split is what keeps the budget rule alive across three separate
carts - a single agent doing everything forgets the budget by the third
order.

---

## Files

```
backend/src/
  core/          the brain - deterministic, offline, no LLM, no network
    agent.py        planner, subagents, timing, rebalancing, replanning, the graph
    conversation.py which courses did they ask for, and what's worth asking
    portions.py     how much food a group of N actually needs
    guardrail.py    the filter that runs before the agent, and on every reply
    tools.py        the mock catalog + search
  integrations/  the outside world
    safety.py       the ordering kill switch - read this one first
    sanitize.py     Swiggy's text is untrusted input; this defangs it
    mcp_client.py   the wire connection to Swiggy's MCP servers
    auth.py         one-time Swiggy login (OAuth + PKCE), caches the token
    live_tools.py   Swiggy's real calls wrapped in plain functions
    adapters.py     Swiggy's real response shapes -> our MenuItem
    llm.py          optional Groq request parser, falls back to regex
  app/           where core meets integrations, and what you run
    live_agent.py    core's unmodified planner, fed real Swiggy data
    execute_live.py  fills a real cart (and cannot place an order)
    run_live.py      proves the Swiggy connection works
    run_live_plan.py the actual product, running for real
  tests/           223 checks, none needing a token or a network
    evals.py              guardrail, planning, recovery + the runner
    evals_conversation.py slots, asking, portions, the graph end to end
    evals_live.py         safety, sanitizing, adapters, live plan, cart
    fake_mcp.py           an in-memory Swiggy built from real response shapes
  devtools/      throwaway scripts that turned guesses into confirmed shapes
    discover_tools.py, inspect_shapes.py,
    inspect_update_food_cart.py, debug_food_cart.py
```

`core` imports nothing from the other folders at load time - `llm.py` is
pulled in lazily inside the graph and falls back to regex if it isn't
there. `integrations` only borrows `core`'s data types, never its
decisions. `app` is the only place a real Swiggy response and the
planner are in the same room. That's what keeps `tests/` runnable with
no network, no API key and no LangGraph.

Every command runs from `backend/src` as `python -m <folder>.<file>`.

---

## One design decision worth knowing

The logic that can be checked - timing, budget rebalancing, replanning -
is **plain Python functions with no LLM in them**. The LLM is only used
to understand what you typed and to choose between items.

That's deliberate. "Is this plan under budget?" has a right answer, so it
should not depend on a model's mood. It also means `evals.py` gives the
same result every single run, which is what makes the test table worth
showing to anyone.

---

## Mock vs live

Ships in **mock mode**: a small built-in catalog, offline, instant.

```bash
python -m core.agent "6 friends Saturday 8pm, budget 3000, 2 are vegetarian"
```

Live mode needs Builders Club access (mcp.swiggy.com/builders):

```bash
python -m integrations.auth          # once - browser login, phone + OTP
python -m app.run_live_plan "dinner for 6 at 8pm, budget 2500"
```

That searches real restaurants near your real saved address, plans against
real prices, shows you the plan, and — only if you say yes — fills your real
Swiggy cart. Then it stops. Open the app and the items are waiting.

---

## Where it's weak

Being upfront, because these are the interesting questions:

- **Delivery estimates are guesses.** The buffer is 10 minutes + 20% of
  the ETA. That's a reasonable guess, not a measured one. With real data
  you'd learn the buffer per area and per hour. (Real ETAs seen in
  testing ran 40–80 minutes — longer than the mock's 38.)
- **Dish-role matching is keyword-based.** `portions.role_of()` decides
  "Butter Naan" is a bread by looking for the word. It runs on real menu
  names nobody controls, so it will mislabel things. The cost is variety,
  not correctness — but an LLM picker is the obvious upgrade. (The first
  live run taught it that soups are sides and noodles are staples.)
- **Restaurant scoring is simple.** The dinner restaurant is now chosen
  by score (has a real main? role variety? menu depth? rating?) instead
  of "first open one that works" — but the score is four hand-tuned
  terms, not learned taste.
- **Avoid-tags are matched against dish names in live mode**, because
  Swiggy doesn't return a "spicy" field. Crude, but silently ignoring
  "nothing spicy" would be worse.
- **The guardrail is rule-based.** Fast, free, predictable, and it will
  miss cleverly worded attacks. An LLM classifier belongs on top of
  these rules, never instead of them.
- **Dineout is unimplemented.** The guardrail lets "book a table for 4"
  through and then nothing useful happens. Swiggy exposes the tools; we
  don't call them yet.
- **Coupons are listed, not applied.** After filling the cart, available
  coupons for the restaurant are printed (read-only) — applying one is
  deliberately left to the human in the app. Note from live testing:
  agent traffic only sees COD-compatible offers, and the real Instamart
  server does not expose coupon tools at all (the docs say it does; the
  server wins).

---

## Credit

Built on Swiggy's public MCP platform. Not affiliated with Swiggy. This
is a demo, not a product - no reselling of API access, no scraping beyond
the provided APIs, and Swiggy is credited clearly throughout.

The idea came from Swiggy's AI team describing this exact feature on the
Codebasics channel.