"""
inspect_update_food_cart.py - read the WHOLE description this time.

discover_tools.py truncated each tool's description to one line, 100
characters, and only printed each parameter's name/type - not its own
description. MCP schemas often bury the real required shape ("each
item needs itemId, quantity, and variantId - pass null if none") in
exactly that text we cut off. Four different key names all silently
no-op'd, which points at a missing required field, not a wrong name -
so this reads everything the server actually says about the tool,
in full, before we guess a fifth time.

    python -m devtools.inspect_update_food_cart
"""

import asyncio
import json

# so this runs both as `python -m <pkg>.<mod>` and as `python <pkg>/<mod>.py`
if __package__ in (None, ""):
    import pathlib
    import sys as _sys
    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from integrations.auth import load_token
from integrations.mcp_client import SwiggyMCP

TOOLS_TO_INSPECT = ["update_food_cart", "get_food_cart"]


async def main() -> None:
    token = load_token()
    if not token:
        print("No token yet. Run: python -m integrations.auth")
        return

    async with SwiggyMCP(token, servers=("food",)) as mcp:
        session = mcp._sessions["food"]
        result = await session.list_tools()

        for tool in result.tools:
            if tool.name not in TOOLS_TO_INSPECT:
                continue
            print("\n" + "=" * 70)
            print(f"  {tool.name}")
            print("=" * 70)
            print("\nFULL description:\n")
            print(tool.description)
            print("\nFULL input schema:\n")
            print(json.dumps(tool.input_schema, indent=2))


if __name__ == "__main__":
    asyncio.run(main())