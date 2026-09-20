"""
core - the brain. Planning, rules, and the mock catalog.

Nothing in here talks to the network or to an LLM (llm.py is imported
lazily inside the graph and falls back to regex). That is what makes
tests/evals.py deterministic: the same input gives the same plan every
single run.
"""
