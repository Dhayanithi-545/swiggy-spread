"""
integrations - everything that talks to the outside world.

Swiggy's MCP servers, the OAuth login, the response-shape adapters, and
the optional Groq parser. Nothing in here decides what to order - it
only knows how to fetch, authenticate, and translate. The planner in
core/ never sees a raw Swiggy response.
"""
