"""
Chapter 5 — LLMs as Reasoning Engines — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch05_01_run_research_agent.py
"""
# ch05_model_profile.py
# Tested against Claude Haiku 3.5, Claude Sonnet 4.6, Claude Opus 4.1,
# Anthropic SDK 0.49.0, as of April 2026.
# Requires: anthropic>=0.49, tavily-python>=0.5

import time
import json
import anthropic
from tavily import TavilyClient

MODELS = [
    "claude-haiku-3-5-20241022",    # small, fast, cheap
    "claude-sonnet-4-6-20250514",   # mid-tier, balanced
    "claude-opus-4-1-20250514",     # frontier, expensive
]

TOOLS = [
    {
        "name": "search_news",
        "description": (
            "Search recent news articles about a company. "
            "Returns a list of articles with title, date, and summary."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query string"},
                "days_back": {"type": "integer", "description": "How many days back to search (max 90)"},
            },
            "required": ["query", "days_back"],
        },
    }
]

OUTPUT_SCHEMA = {
    "events": [
        {
            "event_type": "string",
            "date": "YYYY-MM-DD",
            "financial_impact": "string (e.g. '$2.3B write-down')",
            "summary": "string (one sentence, max 30 words)",
        }
    ]
}

def run_research_agent(model: str, company: str) -> dict:
    client = anthropic.Anthropic()
    tavily = TavilyClient()
    messages = []
    start = time.time()
    input_tokens = 0
    output_tokens = 0

    system = (
        "You are a financial research assistant. "
        "When asked about a company, use the search_news tool to retrieve relevant articles, "
        "then identify the three most financially significant events in the past 90 days. "
        f"Return ONLY a valid JSON object matching this schema: {json.dumps(OUTPUT_SCHEMA)}"
    )
    messages.append({"role": "user", "content": f"Research recent financial news about {company}."})

    for _ in range(8):  # ① iteration budget caps the loop
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            tools=TOOLS,
            messages=messages,
        )
        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens

        if response.stop_reason == "end_turn":  # ② model decided it was done
            for block in response.content:
                if hasattr(block, "text"):
                    try:
                        result = json.loads(block.text)
                        elapsed = time.time() - start
                        return {
                            "model": model,
                            "result": result,
                            "latency_s": round(elapsed, 2),
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                        }
                    except json.JSONDecodeError:
                        pass  # will loop and self-correct
            break

        tool_calls = [b for b in response.content if b.type == "tool_use"]
        if not tool_calls:
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for call in tool_calls:  # ③ execute all tool calls returned in this step
            articles = tavily.search(
                query=call.input["query"],
                max_results=5,
                days=call.input["days_back"],
            )["results"]
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": json.dumps(articles),
            })
        messages.append({"role": "user", "content": tool_results})

    return {"model": model, "result": None, "error": "loop exhausted"}

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = run_research_agent('What are the latest trends in AI?')
        print(result)
