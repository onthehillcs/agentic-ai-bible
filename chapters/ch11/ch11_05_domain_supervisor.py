"""
Chapter 11 — Multi-Agent Systems — Example 5
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch11_05_review_file.py
"""
# ch11_hierarchical.py (fragment)
# Two-level hierarchy: coordinator -> domain supervisors -> workers

import json
import concurrent.futures
import anthropic

client = anthropic.Anthropic()

CORRECTNESS_SYSTEM = (
    "You are a code correctness reviewer. Given source code, identify bugs, "
    "logic errors, and edge cases not handled. Output JSON: "
    '{"issues": [{"line": int, "severity": "critical|major|minor", "description": str}]}'
)

STYLE_SYSTEM = (
    "You are a code style reviewer. Given source code, identify style violations, "
    "naming issues, and readability problems. Output JSON: "
    '{"issues": [{"line": int, "severity": "major|minor", "description": str}]}'
)

DOMAIN_SUPERVISOR_SYSTEM = (
    "You are a domain code review supervisor. Given a list of correctness and style issues "
    "for a set of files, produce a concise domain-level summary. Focus on the three most "
    "critical issues and any cross-cutting themes. Output JSON: "
    '{"domain_summary": str, "critical_issues": list, "themes": list}'
)

def review_file(file_path: str, file_content: str) -> dict:
    """Run correctness and style workers in parallel on a single file."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        correctness_future = executor.submit(
            run_worker, CORRECTNESS_SYSTEM,
            f"Review this file ({file_path}):\n{file_content}")
        style_future = executor.submit(
            run_worker, STYLE_SYSTEM,
            f"Review this file ({file_path}):\n{file_content}")
    correctness = correctness_future.result()
    style = style_future.result()
    return {"file": file_path, "correctness": correctness, "style": style}


def run_worker(system_prompt: str, user_message: str) -> dict:
    """Call Claude with a system prompt and return parsed JSON response."""
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    import json
    try:
        return json.loads(response.content[0].text)
    except Exception:
        return {"raw": response.content[0].text}


if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = review_file('example.py', 'def hello():\n    return 42\n')
        print(result)
