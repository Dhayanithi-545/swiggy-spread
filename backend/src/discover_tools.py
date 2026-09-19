"""
discover_tools.py - see exactly what Swiggy actually gives you.

This repo's live_tools.py hardcodes the Food tools because their exact
names and parameters are published at
https://mcp.swiggy.com/builders/docs/reference/food/ and confirmed
against that page.

Instamart and Dineout tool names are NOT hardcoded anywhere in this
project, on purpose - rather than guess, run this once and read the
real names and schemas straight from Swiggy's server:

    python discover_tools.py

Then open live_tools.py and fill in the Instamart functions using
whatever this prints.
"""

import asyncio
import json

from auth import load_token
from mcp_client import SwiggyMCP


async def main() -> None:
    token = load_token()
    if not token:
        print("No token found. Run: python auth.py")
        return

    async with SwiggyMCP(token, servers=("food", "instamart", "dineout")) as mcp:
        for server in ("food", "instamart", "dineout"):
            print(f"\n{'=' * 60}")
            print(f"  {server.upper()}")
            print("=" * 60)
            tools = await mcp.list_tools(server)
            for t in tools:
                print(f"\n  {t['name']}")
                desc = (t["description"] or "").split("\n")[0]
                print(f"    {desc[:100]}")
                props = (t["schema"] or {}).get("properties", {})
                required = set((t["schema"] or {}).get("required", []))
                for pname, pinfo in props.items():
                    mark = "required" if pname in required else "optional"
                    print(f"      - {pname} ({pinfo.get('type', '?')}, {mark})")


if __name__ == "__main__":
    asyncio.run(main())