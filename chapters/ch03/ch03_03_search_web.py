"""
Chapter 3 — Anatomy of an Agent — Example 3
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch03_03_search_web.py
"""
# requires ANTHROPIC_API_KEY
import anthropic
import json

client = anthropic.Anthropic()

# Tool stub — replace with a real search API (e.g., Tavily, Brave Search)
def search_web(query: str) -> str:
    # Returns top-3 result snippets for query. Stub returns placeholder.
    return json.dumps([{"url": "https://example.com", "snippet": f"Result for: {query}"}])

TOOLS = [
    {
        "name": "search_web",
        "description": "Search the web and return relevant snippets for a query.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
    }
]

def run_research_agent(question: str, max_steps: int = 10) -> str:
    messages = [{"role": "user", "content": question}]
    for _ in range(max_steps):
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            tools=TOOLS,
            messages=messages,
        )
        # Append assistant turn
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Extract final text
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                if block.name == "search_web":
                    result = search_web(**block.input)
                else:
                    result = json.dumps({"error": f"Unknown tool: {block.name}"})
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                )
        messages.append({"role": "user", "content": tool_results})

    return "[Max steps reached without a final answer]"

if __name__ == "__main__":
    answer = run_research_agent("What are the main causes of the 2023 banking crisis?")
    print(answer)
