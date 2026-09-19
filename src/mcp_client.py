"""
mcp_client.py - the actual wire connection to Swiggy's MCP servers.

Everything here uses the real `mcp` Python SDK (pip install mcp), the
same one Claude Desktop and Cursor use. No custom protocol code - MCP
speaks JSON-RPC over HTTP and this library handles that.

One SwiggyMCP object keeps sessions to as many of Swiggy's three
servers as you ask for, open at once, so a single plan (snacks +
dinner + dessert) can call across all of them in one run.
"""

from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

SERVER_URLS = {
    "food": "https://mcp.swiggy.com/food",
    "instamart": "https://mcp.swiggy.com/im",
    "dineout": "https://mcp.swiggy.com/dineout",
}


class SwiggyMCP:
    """
    Usage:

        async with SwiggyMCP(token, servers=("food", "instamart")) as mcp:
            tools = await mcp.list_tools("food")
            result = await mcp.call("food", "get_addresses", {})
    """

    def __init__(self, token: str, servers: tuple[str, ...] = ("food",)):
        self.token = token
        self.servers = servers
        self._stack = AsyncExitStack()
        self._sessions: dict[str, ClientSession] = {}

    async def __aenter__(self) -> "SwiggyMCP":
        for name in self.servers:
            url = SERVER_URLS[name]
            client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=30.0,
            )
            read, write = await self._stack.enter_async_context(
                streamable_http_client(url, http_client=client)
            )
            session = await self._stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self._sessions[name] = session
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self._stack.aclose()

    async def list_tools(self, server: str) -> list[dict[str, Any]]:
        """Every tool this server exposes, with its input schema.
        Run this once for 'instamart' to see the real tool names -
        the code in this repo only assumes tool names for 'food',
        which are confirmed against Swiggy's published docs."""
        result = await self._sessions[server].list_tools()
        return [
            # in list_tools(), change this line:
            {"name": t.name, "description": t.description, "schema": t.input_schema}        
            # {"name": t.name, "description": t.description, "schema": t.inputSchema}
            for t in result.tools
        ]

    async def call(self, server: str, tool: str, arguments: dict[str, Any]) -> dict:
        """Call one tool, return its parsed data.

        Every Swiggy tool replies { success, data, message } or
        { success: false, error }. This unwraps that envelope so
        callers just get the payload, and raises on failure so a bug
        can't silently continue with empty data.
        """
        result = await self._sessions[server].call_tool(tool, arguments)

        if result.structured_content is not None:
            payload = result.structured_content
        else:
            import json
            text = "".join(
                block.text for block in result.content if hasattr(block, "text")
            )
            payload = json.loads(text) if text else {}

        if result.is_error or payload.get("success") is False:
            err = payload.get("error", {}).get("message", "Unknown MCP error")
            raise RuntimeError(f"{server}.{tool} failed: {err}")

        return payload.get("data", payload)