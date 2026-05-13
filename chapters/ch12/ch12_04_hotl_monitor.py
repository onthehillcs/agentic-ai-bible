"""
Chapter 12 — Human-in-the-Loop — Example 4
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch12_04_log_event.py
"""
# ch12_hotl_monitor.py
# HOTL monitoring system with intervention support.
# Requires: fastapi>=0.110, anthropic>=0.49

import time
import threading
from dataclasses import dataclass, field
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
import anthropic

app = FastAPI()
client = anthropic.Anthropic()

# Shared agent control state (use Redis in distributed deployments)
_agent_control = {
    "pause_requested": False,
    "halt_requested": False,
    "injected_message": None,
}
_event_log: list[dict] = []
_lock = threading.Lock()


def log_event(event_type: str, detail: dict) -> None:
    with _lock:
        _event_log.append({
            "timestamp": time.time(),
            "event_type": event_type,
            "detail": detail,
        })
        # Keep last 500 events in memory; flush older events to persistent store
        if len(_event_log) > 500:
            _event_log.pop(0)


def check_for_intervention() -> Optional[str]:
    """
    Called by the agent at each loop iteration.
    Returns an injected message if one is waiting, or None.
    Raises SystemExit if halt is requested.
    """
    with _lock:
        if _agent_control["halt_requested"]:
            log_event("agent_halted", {"reason": "operator requested halt"})
            raise SystemExit("Agent halted by operator")
        if _agent_control["pause_requested"]:
            log_event("agent_paused", {"waiting_for": "operator instruction"})
            # Busy-wait for resume (in production: use an event or a queue)
            while _agent_control["pause_requested"]:
                time.sleep(0.5)
            log_event("agent_resumed", {})
        injected = _agent_control.get("injected_message")
        if injected:
            _agent_control["injected_message"] = None
            return injected
    return None


def run_monitored_agent(task: str, max_iterations: int = 20) -> str:
    """Run a ReAct-style agent loop with HOTL monitoring at each iteration."""
    messages = [{"role": "user", "content": task}]
    log_event("agent_started", {"task": task[:200]})

    for iteration in range(max_iterations):
        # Check for operator intervention before each model call
        injected = check_for_intervention()
        if injected:
            messages.append({"role": "user", "content": f"[Operator instruction]: {injected}"})
            log_event("instruction_injected", {"message": injected})

        response = client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=1024,
            system="You are a research assistant. Complete the task step by step.",
            messages=messages,
        )
        response_text = response.content[0].text
        log_event("agent_step", {
            "iteration": iteration,
            "output_preview": response_text[:200],
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        })

        if response.stop_reason == "end_turn":
            log_event("agent_complete", {"iterations": iteration + 1})
            return response_text

        messages.append({"role": "assistant", "content": response.content})

    log_event("agent_budget_exceeded", {"max_iterations": max_iterations})
    return "Task exceeded iteration budget."


# HOTL control endpoints
class InjectRequest(BaseModel):
    message: str

@app.post("/agent/pause")
def pause_agent():
    with _lock:
        _agent_control["pause_requested"] = True
    return {"status": "pause requested"}

@app.post("/agent/resume")
def resume_agent():
    with _lock:
        _agent_control["pause_requested"] = False
    return {"status": "resumed"}

@app.post("/agent/halt")
def halt_agent():
    with _lock:
        _agent_control["halt_requested"] = True
    return {"status": "halt requested"}

@app.post("/agent/inject")
def inject_instruction(req: InjectRequest):
    with _lock:
        _agent_control["injected_message"] = req.message
    return {"status": "instruction queued"}

@app.get("/agent/events")
def get_events(last_n: int = 50):
    with _lock:
        return {"events": _event_log[-last_n:]}

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = log_event('example', {})
        print(result)
