"""
Chapter 20 — Coding Agents — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch20_02_execute_tool.py
"""
import subprocess
import re
import anthropic
from pathlib import Path

client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file. Returns the file content as a string.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative path to the file"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file, replacing its current contents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "apply_edit",
        "description": (
            "Apply a search-and-replace edit to a file. "
            "The 'search' string must appear verbatim in the file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "search": {"type": "string", "description": "Exact text to find in the file"},
                "replace": {"type": "string", "description": "Text to replace it with"}
            },
            "required": ["path", "search", "replace"]
        }
    },
    {
        "name": "run_tests",
        "description": "Run pytest on the specified path and return the output.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to test file or directory"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "shell",
        "description": "Run a shell command and return stdout + stderr.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"}
            },
            "required": ["command"]
        }
    }
]

def execute_tool(name: str, args: dict) -> str:
    """Dispatch a tool call and return its result as a string."""
    try:
        if name == "read_file":
            return Path(args["path"]).read_text(encoding="utf-8")

        elif name == "write_file":
            Path(args["path"]).write_text(args["content"], encoding="utf-8")
            return f"Wrote {len(args['content'])} bytes to {args['path']}"

        elif name == "apply_edit":
            path = Path(args["path"])
            current = path.read_text(encoding="utf-8")
            if args["search"] not in current:
                return (
                    f"ERROR: Search string not found in {args['path']}. "
                    "Re-read the file to get current contents."
                )
            updated = current.replace(args["search"], args["replace"], 1)
            path.write_text(updated, encoding="utf-8")
            return f"Edit applied to {args['path']}"

        elif name == "run_tests":
            result = subprocess.run(
                ["python", "-m", "pytest", args["path"], "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=120
            )
            output = result.stdout + result.stderr
            return output[:8000]  # Truncate very long test output

        elif name == "shell":
            result = subprocess.run(
                args["command"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            return (result.stdout + result.stderr)[:4000]

    except subprocess.TimeoutExpired:
        return f"ERROR: Command timed out after allowed duration"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"

def run_coding_agent(task: str, working_dir: str, max_iterations: int = 20) -> str:
    """
    Run a coding agent loop to complete the given task.
    Returns a summary of what was done.
    """
    system_prompt = f"""You are an expert software engineer. Your working directory is: {working_dir}

You have tools to read files, write files, apply targeted edits, run tests, and execute shell commands.
Work methodically: read relevant code first, make changes, verify with tests, and iterate.

When applying edits, use apply_edit with exact verbatim search strings from the current file content.
If an edit fails because the search string was not found, re-read the file and try again.

When you have completed the task and all tests pass, respond with a plain text summary of what you did.
Do not call any more tools after the task is complete."""

    messages = [{"role": "user", "content": task}]

    for iteration in range(max_iterations):
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=8096,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Extract final text response
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "Task completed."

        if response.stop_reason != "tool_use":
            return f"Unexpected stop reason: {response.stop_reason}"

        # Execute all tool calls and collect results
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        messages.append({"role": "user", "content": tool_results})

    return f"Max iterations ({max_iterations}) reached."

if __name__ == "__main__":
    import sys
    working_directory = sys.argv[1] if len(sys.argv) > 1 else "."
    task_description = """The file calculator.py has a bug in its divide() function that causes
    it to return 0 when dividing by negative numbers instead of the correct result.
    Find and fix the bug, then ensure all tests in test_calculator.py pass."""
    result = run_coding_agent(task_description, working_directory)
    print(result)
