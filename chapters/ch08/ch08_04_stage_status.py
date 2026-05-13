"""
Chapter 8 — Planning and Decomposition — Example 4
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch08_04_StageStatus.py
"""
# requires ANTHROPIC_API_KEY
import anthropic, json
from dataclasses import dataclass, field
from enum import Enum

client = anthropic.Anthropic()
SONNET = "claude-sonnet-4-5"

class StageStatus(Enum):
    PENDING   = "pending"
    COMPLETE  = "complete"
    FAILED    = "failed"

@dataclass
class PlanStage:
    name: str
    prompt_template: str
    status: StageStatus = StageStatus.PENDING
    output: str = ""

CODING_PLAN_STAGES = [
    PlanStage(
        name="understand_requirements",
        prompt_template=(
            "Analyse this coding task and list: "
            "(1) inputs and outputs, (2) edge cases, (3) constraints.\n\nTask: {task}"
        ),
    ),
    PlanStage(
        name="write_code",
        prompt_template=(
            "Requirements analysis:\n{understand_requirements}\n\n"
            "Write production-quality Python code that satisfies these requirements. "
            "Include type hints and docstrings. Return only the code block."
        ),
    ),
    PlanStage(
        name="write_tests",
        prompt_template=(
            "Implementation:\n{write_code}\n\n"
            "Write pytest unit tests covering happy paths, edge cases, and error cases. "
            "Return only the test code block."
        ),
    ),
    PlanStage(
        name="run_tests",
        prompt_template=(
            "Code:\n{write_code}\n\nTests:\n{write_tests}\n\n"
            "Simulate running the tests. List each test case and whether it PASSES or FAILS. "
            "If any fail, explain why."
        ),
    ),
    PlanStage(
        name="fix_failures",
        prompt_template=(
            "Original code:\n{write_code}\n\n"
            "Test results:\n{run_tests}\n\n"
            "Fix any failing tests. Return the corrected code block only. "
            "If all tests passed, return the original code unchanged."
        ),
    ),
]

def execute_plan(task: str) -> dict:
    # Run the coding plan stages in order, threading outputs as context.
    context = {"task": task}
    for stage in CODING_PLAN_STAGES:
        prompt = stage.prompt_template.format(**context)
        response = client.messages.create(
            model=SONNET, max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        stage.output = response.content[0].text
        stage.status = StageStatus.COMPLETE
        context[stage.name] = stage.output
        print(f"[{stage.name}] done ({len(stage.output)} chars)")
    return context

if __name__ == "__main__":
    task = (
        "Write a function that takes a list of integers and returns "
        "the two numbers that add up to a target sum. "
        "Raise ValueError if no pair exists."
    )
    result = execute_plan(task)
    print("\n=== Final Implementation ===")
    print(result["fix_failures"])
