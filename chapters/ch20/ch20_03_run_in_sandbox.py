"""
Chapter 20 — Coding Agents — Example 3
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch20_03_SandboxResult.py
"""
# requires ANTHROPIC_API_KEY
# Linux only — uses tmpfs and subprocess resource limits
import anthropic, subprocess, tempfile, textwrap, json, re, os
from pathlib import Path
from dataclasses import dataclass

client = anthropic.Anthropic()
SONNET = "claude-sonnet-4-5"

@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool

def extract_code_block(text: str) -> str:
    # Pull the first ```python ... ``` block from the text
    match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    return match.group(1) if match else text


if __name__ == '__main__':
    example = SandboxResult(exit_code=0, stdout='Hello, world!', stderr='', timed_out=False)
    print(example)
    snippet = extract_code_block('```python\nprint(42)\n```')
    print('Extracted:', repr(snippet))
