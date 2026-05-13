"""
Chapter 8 — Planning and Decomposition — Example 3
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch08_03_create_plan.py
"""
# ch08_plan_execute.py
# Tested against Claude Sonnet 4.6 (claude-sonnet-4-6-20250514),
# Anthropic SDK 0.49.0, as of April 2026.
# Requires: anthropic>=0.49, tavily-python>=0.5

import json
import re
import anthropic
from tavily import TavilyClient

client = anthropic.Anthropic()
tavily = TavilyClient()

PLAN_PROMPT = """
You are a planning assistant for engineering roadmap preparation.
Given a list of initiatives, produce a numbered execution plan.
For each initiative, specify:
  - The initiative name
  - What specific information to research (1-2 sentences)
  - The maximum number of search queries to use (1-3)
Format as a numbered markdown list. Do not begin researching yet.
"""

EXECUTE_PROMPT = """
You are an engineering planning analyst.
You have an execution plan and must work through it step by step.
For each step marked [ ], research it using the search tool,
then mark it [x] and add a 2-3 sentence summary of findings.
After completing a step, update the plan and present it.
Stop after completing all steps and output the final roadmap document.
"""

SEARCH_TOOL = {
    "name": "search",
    "description": "Search the web for recent information. Use targeted queries.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Specific search query (max 10 words)"},
        },
        "required": ["query"],
    },
}


def create_plan(initiatives: list[str]) -> str:  # ① planning phase
    """Ask the model to produce an explicit plan before any execution begins."""
    response = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=1024,
        system=PLAN_PROMPT,
        messages=[{"role": "user", "content": "Initiatives:\n" + "\n".join(f"- {i}" for i in initiatives)}],
    )
    return response.content[0].text


def validate_plan(plan: str) -> bool:  # ② plan validation
    """Check that the plan has the right structure before execution."""
    lines = [l.strip() for l in plan.splitlines() if l.strip()]
    numbered_steps = [l for l in lines if re.match(r'^\d+\.', l)]
    return len(numbered_steps) > 0


def execute_plan(plan: str) -> str:  # ③ execution phase
    """Work through the plan step by step using tool calls."""
    messages = [
        {"role": "user", "content": f"Here is the execution plan. Work through each step:\n\n{plan}"}
    ]

    for iteration in range(30):  # ④ generous budget since plan may have many steps
        response = client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=2048,
            system=EXECUTE_PROMPT,
            tools=[SEARCH_TOOL],
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return next((b.text for b in response.content if hasattr(b, "text")), "No output produced.")

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                results = tavily.search(query=block.input["query"], max_results=3)["results"]
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps([{"title": r["title"], "content": r["content"][:300]} for r in results]),
                })
        messages.append({"role": "user", "content": tool_results})

    return "Execution budget exceeded."


def run_planning_agent(initiatives: list[str]) -> str:
    """Full Plan-and-Execute run for a list of engineering initiatives."""
    print(f"Planning phase: decomposing {len(initiatives)} initiatives...")
    plan = create_plan(initiatives)

    if not validate_plan(plan):
        return f"Plan validation failed. Raw plan:\n{plan}"

    print(f"Plan created with {plan.count(chr(10))} lines. Beginning execution...")
    return execute_plan(plan)

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = create_plan('Build a REST API for a todo app')
        print(result)
