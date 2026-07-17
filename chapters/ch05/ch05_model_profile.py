"""Profile a financial-news research agent across Anthropic model tiers.

Setup:
    uv pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here
    export TAVILY_API_KEY=your_key_here

Run:
    python ch05_model_profile.py Apple   --models claude-haiku-4-5 claude-sonnet-4-6 claude-opus-4-7   --input-price-per-million 0.80 3.00 15.00   --output-price-per-million 4.00 15.00 75.00

Prices must be supplied in the same order as the configured models. Check the
provider's current pricing page before using this script for a cost decision.
"""

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any

import anthropic
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv("/Users/chensong/SongFiles/002Study/API_saved/.env", override=True)

MODEL_DEFAULTS = [
    os.getenv("ANTHROPIC_MODEL_LIGHT", "claude-haiku-4-5"),
    os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
    os.getenv("ANTHROPIC_MODEL_HEAVY", "claude-opus-4-7"),
]
MAX_STEPS = 8
MAX_DAYS_BACK = 90

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
                "days_back": {
                    "type": "integer",
                    "description": "How many days back to search (maximum 90)",
                },
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
            "financial_impact": "string",
            "summary": "string (one sentence, maximum 30 words)",
        }
    ]
}


@dataclass(frozen=True)
class Pricing:
    input_per_million: float
    output_per_million: float


def calculate_cost(input_tokens: int, output_tokens: int, pricing: Pricing) -> float:
    return (
        input_tokens / 1_000_000 * pricing.input_per_million
        + output_tokens / 1_000_000 * pricing.output_per_million
    )


def score_structure(result: Any) -> float:
    """Return the fraction of required output checks satisfied by the result."""
    checks: list[bool] = [isinstance(result, dict)]
    if not isinstance(result, dict):
        return 0.0

    events = result.get("events")
    checks.append(isinstance(events, list) and len(events) == 3)
    if not isinstance(events, list):
        return sum(checks) / len(checks)

    for event in events:
        checks.append(isinstance(event, dict))
        if not isinstance(event, dict):
            continue
        checks.extend(
            [
                isinstance(event.get("event_type"), str) and bool(event["event_type"].strip()),
                isinstance(event.get("date"), str)
                and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", event["date"])),
                isinstance(event.get("financial_impact"), str)
                and bool(event["financial_impact"].strip()),
                isinstance(event.get("summary"), str)
                and 0 < len(event["summary"].split()) <= 30,
            ]
        )
    return sum(checks) / len(checks)


def parse_json_object(text: str) -> dict[str, Any]:
    """Extract the first JSON object from a model response."""
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise json.JSONDecodeError("No JSON object found", text, 0)


def run_research_agent(
    client: anthropic.Anthropic,
    tavily: TavilyClient,
    model: str,
    company: str,
    pricing: Pricing,
) -> dict[str, Any]:
    system = (
        "You are a financial research assistant. Use search_news to retrieve relevant "
        f"articles about {company}. Identify exactly three financially significant events "
        "from the past 90 days. Return only valid JSON matching this schema: "
        f"{json.dumps(OUTPUT_SCHEMA)}"
    )
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": f"Research recent financial news about {company}."}
    ]
    started_at = time.perf_counter()
    input_tokens = 0
    output_tokens = 0

    for step in range(1, MAX_STEPS + 1):
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            tools=TOOLS,
            messages=messages,
        )
        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens

        if response.stop_reason == "end_turn":
            text = "".join(block.text for block in response.content if block.type == "text")
            try:
                result = parse_json_object(text)
            except json.JSONDecodeError as error:
                return profile_error(
                    model,
                    input_tokens,
                    output_tokens,
                    pricing,
                    started_at,
                    step,
                    f"invalid JSON: {error.msg}",
                )
            return {
                "model": model,
                "result": result,
                "structure_score": round(score_structure(result), 3),
                "latency_s": round(time.perf_counter() - started_at, 2),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost_usd": round(calculate_cost(input_tokens, output_tokens, pricing), 6),
                "steps": step,
            }

        tool_calls = [block for block in response.content if block.type == "tool_use"]
        if not tool_calls:
            return profile_error(model, input_tokens, output_tokens, pricing, started_at, step, "no tool call")

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for call in tool_calls:
            try:
                days_back = min(max(int(call.input["days_back"]), 1), MAX_DAYS_BACK)
                articles = tavily.search(
                    query=call.input["query"],
                    max_results=5,
                    days=days_back,
                )["results"]
                content = json.dumps(articles)
            except Exception as error:
                content = json.dumps({"error": f"{type(error).__name__}: {error}"})
            tool_results.append(
                {"type": "tool_result", "tool_use_id": call.id, "content": content}
            )
        messages.append({"role": "user", "content": tool_results})

    return profile_error(model, input_tokens, output_tokens, pricing, started_at, MAX_STEPS, "loop exhausted")


def profile_error(
    model: str,
    input_tokens: int,
    output_tokens: int,
    pricing: Pricing,
    started_at: float,
    steps: int,
    error: str,
) -> dict[str, Any]:
    return {
        "model": model,
        "result": None,
        "structure_score": 0.0,
        "latency_s": round(time.perf_counter() - started_at, 2),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": round(calculate_cost(input_tokens, output_tokens, pricing), 6),
        "steps": steps,
        "error": error,
    }


def print_summary(profiles: list[dict[str, Any]]) -> None:
    print("\nModel comparison")
    print("model | structure_score | latency_s | input_tokens | output_tokens | cost_usd | error")
    for profile in profiles:
        print(
            f"{profile['model']} | {profile['structure_score']} | "
            f"{profile['latency_s']} | {profile['input_tokens']} | "
            f"{profile['output_tokens']} | "
            f"{profile['estimated_cost_usd']:.6f} | {profile.get('error', '')}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("company", help="Company to research, for example: Apple")
    parser.add_argument("--models", nargs="+", default=MODEL_DEFAULTS)
    parser.add_argument("--input-price-per-million", nargs="+", type=float, required=True)
    parser.add_argument("--output-price-per-million", nargs="+", type=float, required=True)
    args = parser.parse_args()
    if len(args.models) != len(args.input_price_per_million) or len(args.models) != len(args.output_price_per_million):
        parser.error("Provide one input and output price for every model.")
    return args


def main() -> None:
    args = parse_args()
    if not os.getenv("ANTHROPIC_API_KEY") or not os.getenv("TAVILY_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY and TAVILY_API_KEY before running this script.")

    client = anthropic.Anthropic()
    tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    profiles = []
    for model, input_price, output_price in zip(
        args.models, args.input_price_per_million, args.output_price_per_million
    ):
        print(f"Running {model}...")
        profiles.append(
            run_research_agent(
                client,
                tavily,
                model,
                args.company,
                Pricing(input_price, output_price),
            )
        )

    print_summary(profiles)
    print("\nFull results")
    print(json.dumps(profiles, indent=2))


if __name__ == "__main__":
    main()
