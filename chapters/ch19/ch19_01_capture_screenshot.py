"""
Chapter 19 — Computer-Use and Browser Agents — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch19_01_capture_screenshot.py
"""
import anthropic
import base64
import subprocess
import time
from pathlib import Path

client = anthropic.Anthropic()

def capture_screenshot(path: str = "/tmp/screen.png") -> str:
    """Capture current screen state and return base64-encoded PNG."""
    subprocess.run(
        ["scrot", "-z", path],
        check=True,
        timeout=5
    )
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")

def execute_action(action: dict) -> None:
    """Execute a computer-use action using xdotool."""
    action_type = action["type"]

    if action_type == "mouse_move":
        subprocess.run(
            ["xdotool", "mousemove", str(action["coordinate"][0]), str(action["coordinate"][1])],
            check=True
        )
    elif action_type == "left_click":
        subprocess.run(
            ["xdotool", "mousemove", str(action["coordinate"][0]), str(action["coordinate"][1])],
            check=True
        )
        time.sleep(0.1)
        subprocess.run(["xdotool", "click", "1"], check=True)
    elif action_type == "type":
        subprocess.run(
            ["xdotool", "type", "--clearmodifiers", action["text"]],
            check=True
        )
    elif action_type == "key":
        subprocess.run(
            ["xdotool", "key", action["key"]],
            check=True
        )
    elif action_type == "scroll":
        direction = "5" if action["direction"] == "down" else "-5"
        subprocess.run(
            ["xdotool", "mousemove", str(action["coordinate"][0]), str(action["coordinate"][1])],
            check=True
        )
        subprocess.run(["xdotool", "click", "4" if action["direction"] == "up" else "5"], check=True)

def run_computer_use_agent(task: str, max_steps: int = 50) -> str:
    """Run a computer-use agent loop for the given task."""
    messages = []
    tools = [
        {
            "type": "computer_20241022",
            "name": "computer",
            "display_width_px": 1920,
            "display_height_px": 1080,
            "display_number": 1,
        }
    ]

    # Initial screenshot
    screenshot_b64 = capture_screenshot()
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": screenshot_b64},
            },
            {"type": "text", "text": task},
        ],
    })

    for step in range(max_steps):
        response = client.beta.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            tools=tools,
            messages=messages,
            betas=["computer-use-2024-10-22"],
        )

        # Append assistant response
        messages.append({"role": "assistant", "content": response.content})

        # Check for task completion
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "Task completed."

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use" and block.name == "computer":
                action = block.input
                try:
                    execute_action(action)
                    time.sleep(0.5)  # Allow UI to settle
                    new_screenshot = capture_screenshot()
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": new_screenshot,
                                },
                            }
                        ],
                    })
                except subprocess.CalledProcessError as e:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "is_error": True,
                        "content": f"Action execution failed: {e}",
                    })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    return "Max steps reached without task completion."

if __name__ == '__main__':
    import asyncio
    asyncio.run(capture_screenshot('https://example.com', '/tmp/screenshot.png'))
    print('Screenshot saved to /tmp/screenshot.png')
