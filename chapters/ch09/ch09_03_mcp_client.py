"""
Chapter 9 — Model Context Protocol — Example 3
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch09_03_mcp_tool_to_anthropic.py
"""
# ch09_mcp_client.py
# Tested against mcp[cli]>=1.5.0, anthropic>=0.49, as of April 2026.
# Requires: mcp[cli]>=1.5, anthropic>=0.49

import json
import asyncio
import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ANTHROPIC_MODEL = "claude-sonnet-4-6-20250514"


def mcp_tool_to_anthropic(tool) -> dict:
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.inputSchema,
    }


async def run_agent_with_mcp_server(user_message: str) -> str:
    server_params = StdioServerParameters(
        command="python",
        args=["ch09_mcp_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_response = await session.list_tools()
            anthropic_tools = [mcp_tool_to_anthropic(t) for t in tools_response.tools]

            client = anthropic.Anthropic()
            messages = [{"role": "user", "content": user_message}]

            for _ in range(10):
                response = client.messages.create(
                    model=ANTHROPIC_MODEL,
                    max_tokens=1024,
                    system="You are a product assistant. Help customers find products and check availability.",
                    tools=anthropic_tools,
                    messages=messages,
                )

                if response.stop_reason == "end_turn":
                    return next((b.text for b in response.content if hasattr(b, "text")), "")

                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await session.call_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result.content[0].text if result.content else "{}",
                        })
                messages.append({"role": "user", "content": tool_results})

    return "Agent loop exhausted."


if __name__ == "__main__":
    result = asyncio.run(run_agent_with_mcp_server(
        "Is the blue kettle in stock? I want to know the price and how many are available."
    ))
    print(result)
