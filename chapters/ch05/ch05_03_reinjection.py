"""
Chapter 5 -- LLMs as Reasoning Engines -- Example 3

Demonstrates instruction re-injection in a multi-step research-agent loop.

Setup:
    uv pip install -r ../../requirements.txt

Run from the repository root:
    python chapters/ch05/ch05_03_reinjection.py Apple
"""

import json
import os
import sys
from typing import Any

import anthropic
from dotenv import load_dotenv
from tavily import TavilyClient


load_dotenv("/Users/chensong/SongFiles/002Study/API_saved/.env")

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
MAX_STEPS = 10

SYSTEM_PROMPT = """You are a financial research assistant.

When asked about a company, use the search_news tool to retrieve relevant articles,
then identify the three most financially significant events in the past 90 days.

Critical requirements:
1. Ground every factual claim in the search_news results; do not invent facts.
2. Return exactly three events as valid JSON with event_type, date,
   financial_impact, and summary fields.
"""

# These are the two requirements that would be incidents if a long-running loop forgot them.
REINJECTED_CONSTRAINTS = (
    "Critical constraints: ground factual claims only in search_news results; "
    "return exactly three events as valid JSON."
)

TOOLS = [
    {
        "name": "search_news",
        "description": "Search recent news articles about a company.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query string."},
                "days_back": {
                    "type": "integer",
                    "description": "Days of news to search, from 1 to 90.",
                },
            },
            "required": ["query", "days_back"],
        },
    }
]


def reinjected_text(text: str) -> str:
    """Put persistent constraints first in every user-role text message."""
    return f"{REINJECTED_CONSTRAINTS}\n\n{text}"


def initial_message(company: str) -> dict[str, str]:
    return {
        "role": "user",
        "content": reinjected_text(f"Research recent financial news about {company}."),
    }


def tool_result_message(tool_results: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    """Re-inject constraints before the tool results provided to the next model call."""
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": REINJECTED_CONSTRAINTS},
            *tool_results,
        ],
    }


def run_research_agent(company: str, model: str = MODEL) -> dict[str, Any]:
    client = anthropic.Anthropic()
    tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    messages: list[dict[str, Any]] = [initial_message(company)]

    for step in range(1, MAX_STEPS + 1):
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text = "".join(block.text for block in response.content if block.type == "text")
            try:
                return {"status": "completed", "steps": step, "result": json.loads(text)}
            except json.JSONDecodeError as error:
                return {"status": "invalid_json", "steps": step, "error": error.msg, "raw": text}

        tool_calls = [block for block in response.content if block.type == "tool_use"]
        if not tool_calls:
            return {"status": "halted", "steps": step, "error": "Model made no tool call."}

        messages.append({"role": "assistant", "content": response.content})
        tool_results: list[dict[str, str]] = []
        for call in tool_calls:
            try:
                articles = tavily.search(
                    query=call.input["query"],
                    max_results=5,
                    days=min(call.input["days_back"], 90),
                )["results"]
                content = json.dumps(articles)
            except (KeyError, TypeError, ValueError) as error:
                content = json.dumps({"error": str(error)})
            tool_results.append(
                {"type": "tool_result", "tool_use_id": call.id, "content": content}
            )
        messages.append(tool_result_message(tool_results))

    return {"status": "budget_exceeded", "steps": MAX_STEPS}


if __name__ == "__main__":
    company = sys.argv[1] if len(sys.argv) > 1 else "Apple"
    print(json.dumps(run_research_agent(company), indent=2))