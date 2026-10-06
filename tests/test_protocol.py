"""End-to-end test: spawn the server over stdio and speak MCP to it.

This is the test that matters — it proves the server is a working MCP server
(initialize, list tools, call a tool), not merely that its functions work.
"""
from __future__ import annotations

import asyncio
import os
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def _run(coro):
    return asyncio.run(coro)


def test_stdio_lists_tools_prompts_and_calls_a_tool(oscar_db):
    async def scenario():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "oscar_mcp"],
            env={**os.environ, "OSCAR_DB_PATH": str(oscar_db)},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = {t.name for t in (await session.list_tools()).tools}
                assert {"oscar_status", "daily_summary", "therapy_trend", "list_machines"} <= tools

                prompts = {p.name for p in (await session.list_prompts()).prompts}
                assert {"assess_therapy", "review_for_uars"} <= prompts

                result = await session.call_tool("oscar_status", {})
                return result

    result = _run(scenario())
    text = " ".join(
        block.text for block in result.content if getattr(block, "type", None) == "text"
    )
    assert "tester" in text or "profiles" in text
