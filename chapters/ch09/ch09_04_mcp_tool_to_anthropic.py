"""
Chapter 9 — Model Context Protocol — Example 4
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch09_04_list_tools.py
"""
# ch09_search_server.py -- MCP server wrapping Tavily search
# Tested against mcp[cli]>=1.5.0, tavily-python>=0.5, as of April 2026.
# Requires: mcp[cli]>=1.5, tavily-python>=0.5

import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from tavily import TavilyClient
import asyncio

app = Server("search-tools")
tavily = TavilyClient()


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_news",
            description=(
                "Search recent news and web content. Returns up to 5 results with title, URL, "
                "and a content excerpt. Use targeted 5-10 word queries for best results. "
                "Specify days_back to limit results to a recent time window."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "days_back": {"type": "integer", "description": "Days to look back (1-90). Default: 30."},
                },
                "required": ["query"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "search_news":
        results = tavily.search(
            query=arguments["query"],
            max_results=5,
            days=arguments.get("days_back", 30),
        )["results"]
        trimmed = [{"title": r["title"], "url": r["url"], "content": r["content"][:400]} for r in results]
        return [types.TextContent(type="text", text=json.dumps(trimmed))]
    return [types.TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


if __name__ == "__main__":
    asyncio.run(stdio_server(app))
