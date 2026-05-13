"""
Chapter 10 — Single-Agent Patterns — Example 4
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch10_04_build_scratchpad_message.py
"""
# ch10_scratchpad.py (fragment)

def build_scratchpad_message(task: str, scratchpad: str, iteration: int) -> str:
    """Build the user message that includes the persistent scratchpad."""
    return f"""TASK: {task}

SCRATCHPAD (your working notes and plan, updated each step):
{scratchpad if scratchpad else "[empty - fill this in before your first tool call]"}

Iteration {iteration}: Continue with the next step in your plan.
Update the scratchpad at the start of your response before calling any tool."""

def extract_scratchpad_update(model_response_text: str) -> tuple[str, str]:
    """Extract updated scratchpad content from model response."""
    # Model is instructed to delimit scratchpad updates
    if "<scratchpad>" in model_response_text and "</scratchpad>" in model_response_text:
        start = model_response_text.index("<scratchpad>") + len("<scratchpad>")
        end = model_response_text.index("</scratchpad>")
        new_scratchpad = model_response_text[start:end].strip()
        remaining = model_response_text[:model_response_text.index("<scratchpad>")] + \
                    model_response_text[model_response_text.index("</scratchpad>") + len("</scratchpad>"):]
        return new_scratchpad, remaining.strip()
    return "", model_response_text

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = build_scratchpad_message('example', 'example', 1)
        print(result)
