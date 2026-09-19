# Spread

A planning agent that runs a whole gathering, not a single order.

You say:

```
6 friends coming Saturday 8pm, budget 3000, 2 are vegetarian, one hates spice
```

It works out snacks, dinner and dessert, times each order backwards so the
food arrives when you want it, checks the budget across all three carts,
shows you the plan, and only orders after you say yes.

Built with LangGraph on top of Swiggy's MCP servers (Food, Instamart, Dineout).

See `PROJECT.md` for why this problem is harder than it looks.

---

## Run it

```bash
pip install langgraph
python agent.py "6 friends Saturday 8pm, budget 3000, 2 are vegetarian"
```

Run the tests:

```bash
python evals.py
```

That should print `42/42 passed`. The evals need no API key, no network
and no LangGraph - so if that table goes red, something is genuinely
broken.

Try the guardrail on its own:

```bash
python guardrail.py
```

---

## What you'll see

```
  SNACKS  -  on the table 19:00
    order at 18:30  (instamart, eta 15m + 15m buffer)
      1 x Cheese cubes platter               Rs  420
      1 x Nachos + salsa dip                 Rs  260
    subtotal                                     Rs  680

  DINNER  -  on the table 20:00
    order at 19:02  (food, eta 38m + 20m buffer)
      3 x Paneer butter masala               Rs 1140
    subtotal                                     Rs 1140

  DESSERT  -  on the table 21:00
    order at 20:30  (instamart, eta 15m + 15m buffer)
      1 x Vanilla ice cream tub              Rs  320
      1 x Rasmalai (4 pcs)                   Rs  260
    subtotal                                     Rs  580

  TOTAL                                        Rs 2400
  left over                                    Rs  600

Place these orders? (yes/no) >
```

Note the dinner line: you eat at 20:00, so it orders at **19:02** - 38
minutes of delivery plus a 20 minute buffer. Snacks arrive from a faster
platform so they get a shorter head start. That difference is the whole
project in one screenshot.

---

## How it fits together

```
        your request
             |
      [ guardrail check ]   guardrail.py - blocks off-topic and injection
             |
        [ PLANNER ]         agent.py - owns budget + dietary rules
             |
   ----------+----------
   |         |         |
[snacks]  [dinner]  [dessert]   subagents - each finds options for one slot
   |         |         |
   ----------+----------
             |
      [ YOU APPROVE ]       nothing happens before this
             |
       [ execute ]          dry run by default
```

The planner never searches for food itself. The subagents never decide.
That split is what keeps the budget rule alive across three separate
carts - a single agent doing everything forgets the budget by the third
order.

---

## Files

| file | what's in it |
|---|---|
| `agent.py` | planner, subagents, timing maths, rebalancing, replanning, the graph |
| `guardrail.py` | the filter that runs before the agent |
| `tools.py` | the catalog + search, and the real Swiggy MCP loader |
| `evals.py` | 42 tests - guardrail, planning, recovery |
| `PROJECT.md` | the design doc: what and why |

Five files, no nested folders.

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

Live mode needs Builders Club access (mcp.swiggy.com/builders), then:

```bash
export SPREAD_MODE=live
export SWIGGY_MCP_TOKEN=...
```

`load_swiggy_mcp_tools()` in `tools.py` has the connection code. The tool
names in there are placeholders - print the loaded tools once you have
access and correct them.

**Even in live mode, execution stays a dry run.** Turning on real orders
is a deliberate change to `execute_node`, not a flag. An agent that can
spend money by accident is not a portfolio project, it's a liability.

---

## Where it's weak

Being upfront, because these are the interesting questions:

- **Delivery estimates are guesses.** The buffer is 10 minutes + 20% of
  the ETA. That's a reasonable guess, not a measured one. With real data
  you'd learn the buffer per area and per hour.
- **Item choice is simple.** Subagents sort by price and take variety.
  A real version would consider what goes together, past orders, ratings.
- **The budget split is fixed** (25/50/25). It should adapt - a dessert-
  heavy request shouldn't get 25%.
- **The guardrail is rule-based.** Fast, free, predictable, and it will
  miss cleverly worded attacks. An LLM classifier belongs on top of
  these rules, never instead of them.

---

## Credit

Built on Swiggy's public MCP platform. Not affiliated with Swiggy. This
is a demo, not a product - no reselling of API access, no scraping beyond
the provided APIs, and Swiggy is credited clearly throughout.

The idea came from Swiggy's AI team describing this exact feature on the
Codebasics channel.