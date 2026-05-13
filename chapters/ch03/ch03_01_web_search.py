"""
Chapter 3 — Anatomy of an Agent — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch03_01_web_search.py
"""
"""A minimal ReAct-style research agent, ~150 lines.

Reads: ANTHROPIC_API_KEY. Uses the Messages API with tool use.
Run:   python research_agent.py "Your question here"
"""
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

import anthropic
import httpx

MODEL = "claude-sonnet-4-5"
MAX_STEPS = 10
SYSTEM_PROMPT = (
    "You are a research assistant. Answer the user's question by searching "
    "the web, reading relevant pages, and synthesizing findings. When you "
    "have enough information, call the `final_answer` tool with a concise "
    "answer and a list of the URLs you relied on. If you cannot answer "
    "confidently after at most 8 tool calls, call `final_answer` with your "
    "best partial answer and `confidence: low`."
)


# ---------- Tool definitions ----------

def web_search(query: str) -> dict[str, Any]:
    """Search the web via a public SerpAPI-compatible endpoint."""
    r = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": 5},
        headers={"X-Subscription-Token": os.environ["BRAVE_API_KEY"]},
        timeout=15,
    )
    r.raise_for_status()
    results = r.json().get("web", {}).get("results", [])
    return {
        "results": [
            {"title": x["title"], "url": x["url"], "snippet": x.get("description", "")}
            for x in results[:5]
        ]
    }


def fetch_page(url: str) -> dict[str, Any]:
    """Fetch a page and return its first ~8000 characters of text."""
    try:
        r = httpx.get(url, timeout=20, follow_redirects=True,
                      headers={"User-Agent": "research-agent/0.1"})
        r.raise_for_status()
    except httpx.HTTPError as e:
        return {"error": f"fetch failed: {e}"}
    # Crude HTML-to-text: readers in production should use trafilatura.
    import re
    text = re.sub(r"<[^>]+>", " ", r.text)
    text = re.sub(r"\s+", " ", text).strip()
    return {"url": str(r.url), "text": text[:8000]}


def final_answer(answer: str, sources: list[str], confidence: str) -> dict[str, Any]:
    """Terminator tool: the loop returns when the model calls this."""
    return {"answer": answer, "sources": sources, "confidence": confidence}


TOOLS: dict[str, Callable[..., Any]] = {
    "web_search": web_search,
    "fetch_page": fetch_page,
    "final_answer": final_answer,
}

TOOL_SCHEMAS = [
    {
        "name": "web_search",
        "description": "Search the web. Returns up to 5 results with title, url, and snippet.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "fetch_page",
        "description": "Fetch the text content of a web page by URL.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "final_answer",
        "description": (
            "Emit the final answer. Confidence must be 'high', 'medium', or 'low'. "
            "Sources must be the URLs relied on."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "sources": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            },
            "required": ["answer", "sources", "confidence"],
        },
    },
]


# ---------- The loop ----------

@dataclass
class RunResult:
    status: str                      # "answered" | "budget_exceeded" | "halted"
    answer: str | None = None
    sources: list[str] = field(default_factory=list)
    confidence: str | None = None
    steps: int = 0


def run(question: str) -> RunResult:
    client = anthropic.Anthropic()
    messages: list[dict[str, Any]] = [{"role": "user", "content": question}]

    for step in range(1, MAX_STEPS + 1):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            # Model produced text with no tool call. Treat as stuck.
            return RunResult(status="halted", steps=step)

        tool_results = []
        for tu in tool_uses:
            if tu.name == "final_answer":
                return RunResult(
                    status="answered",
                    answer=tu.input["answer"],
                    sources=tu.input["sources"],
                    confidence=tu.input["confidence"],
                    steps=step,
                )
            try:
                out = TOOLS[tu.name](**tu.input)
            except Exception as e:
                out = {"error": f"{type(e).__name__}: {e}"}
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps(out)[:8000],
            })
        messages.append({"role": "user", "content": tool_results})

    return RunResult(status="budget_exceeded", steps=MAX_STEPS)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: research_agent.py 'your question'", file=sys.stderr)
        sys.exit(2)
    result = run(" ".join(sys.argv[1:]))
    print(json.dumps(result.__dict__, indent=2))
