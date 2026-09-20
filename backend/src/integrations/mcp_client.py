"""
mcp_client.py - the actual wire connection to Swiggy's MCP servers.

Everything here uses the real `mcp` Python SDK (pip install mcp), the
same one Claude Desktop and Cursor use. No custom protocol code - MCP
speaks JSON-RPC over HTTP and this library handles that.

One SwiggyMCP object keeps sessions to as many of Swiggy's three
servers as you ask for, open at once, so a single plan (snacks +
dinner + dessert) can call across all of them in one run.

Every call() goes through safety.refuse_if_spending() first. That check
is here, on the wire, rather than only in live_tools.py's typed
wrappers - a passthrough call with a hand-typed tool name has to clear
the same bar as everything else.
"""

from __future__ import annotations

import json
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

from integrations.safety import refuse_if_spending

SERVER_URLS = {
    "food": "https://mcp.swiggy.com/food",
    "instamart": "https://mcp.swiggy.com/im",
    "dineout": "https://mcp.swiggy.com/dineout",
}

REQUEST_TIMEOUT_SECONDS = 30.0


class SwiggyMCP:
    """
    Usage:

        async with SwiggyMCP(token, servers=("food", "instamart")) as mcp:
            tools = await mcp.list_tools("food")
            result = await mcp.call("food", "get_addresses", {})
    """

    def __init__(self, token: str, servers: tuple[str, ...] = ("food",)):
        unknown = [s for s in servers if s not in SERVER_URLS]
        if unknown:
            raise ValueError(
                f"Unknown Swiggy server(s) {unknown}. "
                f"Known: {sorted(SERVER_URLS)}"
            )
        self.token = token
        self.servers = servers
        self._stack = AsyncExitStack()
        self._sessions: dict[str, ClientSession] = {}
        self._tool_names: dict[str, set[str]] = {}

    async def __aenter__(self) -> "SwiggyMCP":
        try:
            for name in self.servers:
                # create_mcp_http_client() comes from the MCP SDK itself.
                # Building the client by hand with `httpx.AsyncClient` is
                # what broke here before: the SDK is typed against httpx2,
                # a different package from the httpx that auth.py uses, so
                # a hand-rolled client is the wrong object. Letting the SDK
                # build it means this keeps working when it switches again.
                client = create_mcp_http_client(
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                read, write = await self._stack.enter_async_context(
                    streamable_http_client(SERVER_URLS[name], http_client=client)
                )
                session = await self._stack.enter_async_context(
                    ClientSession(read, write)
                )
                await session.initialize()
                self._sessions[name] = session
        except BaseException:
            # A half-open set of sessions leaks connections and makes the
            # next error far more confusing than the first one.
            await self._stack.aclose()
            raise
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self._stack.aclose()

    def _session(self, server: str) -> ClientSession:
        try:
            return self._sessions[server]
        except KeyError:
            raise RuntimeError(
                f"No open session for '{server}'. Opened: {sorted(self._sessions)}. "
                f"Pass it in SwiggyMCP(token, servers=(...))."
            ) from None

    async def list_tools(self, server: str) -> list[dict[str, Any]]:
        """Every tool this server exposes, with its input schema.

        Run this once for 'instamart' to see the real tool names - the
        code in this repo only assumes tool names for 'food', which are
        confirmed against Swiggy's published docs.
        """
        result = await self._session(server).list_tools()
        tools = [
            {
                "name": t.name,
                "description": t.description,
                "schema": t.input_schema,
            }
            for t in result.tools
        ]
        self._tool_names[server] = {t["name"] for t in tools}
        return tools

    async def has_tool(self, server: str, tool: str) -> bool:
        """Cheap check against the server's real tool list, fetched once
        per session. Instamart's tool names were never published, so the
        honest thing is to ask the server rather than assume."""
        if server not in self._tool_names:
            await self.list_tools(server)
        return tool in self._tool_names[server]

    async def call(self, server: str, tool: str, arguments: dict[str, Any]) -> Any:
        """Call one tool, return its parsed data.

        Every Swiggy tool replies { success, data, message } or
        { success: false, error }. This unwraps that envelope so
        callers just get the payload, and raises on failure so a bug
        can't silently continue with empty data.
        """
        # Before anything touches the network. See safety.py for why this
        # lives here and not only in live_tools.py.
        refuse_if_spending(tool, context=f"{server} server")

        result = await self._session(server).call_tool(tool, arguments)

        payload = result.structured_content
        if payload is None:
            text = "".join(
                block.text for block in result.content if hasattr(block, "text")
            )
            if not text:
                payload = {}
            else:
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    # Some tools answer in prose. That isn't an error, and
                    # it isn't JSON either - hand it back rather than
                    # crashing on a response we simply didn't predict.
                    payload = {"text": text}

        if not isinstance(payload, dict):
            if result.is_error:
                raise RuntimeError(f"{server}.{tool} failed: {payload!r}")
            return payload

        if result.is_error or payload.get("success") is False:
            raise RuntimeError(f"{server}.{tool} failed: {_error_message(payload)}")

        return payload.get("data", payload)


def _error_message(payload: dict) -> str:
    """Swiggy's error field has been seen as a string, as {"message": ...},
    and as absent entirely. Handle all three rather than throwing an
    AttributeError while trying to report someone else's error."""
    err = payload.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or err.get("code") or err)
    if err:
        return str(err)
    return str(payload.get("message") or "Unknown MCP error")
