"""
Chapter 10 — Single-Agent Patterns — Example 5
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch10_05_ReturnStep.py
"""
# ch10_returns_step_machine.py
# Tested against Claude Sonnet 4.6, Anthropic SDK 0.49.0, April 2026.
# Requires: anthropic>=0.49

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import anthropic

client = anthropic.Anthropic()

class ReturnStep(str, Enum):
    VERIFY_ORDER = "verify_order"
    CHECK_ELIGIBILITY = "check_eligibility"
    CONFIRM_WITH_CUSTOMER = "confirm_with_customer"
    INITIATE_RETURN = "initiate_return"
    COMPLETE = "complete"

@dataclass
class ReturnState:
    current_step: ReturnStep = ReturnStep.VERIFY_ORDER
    order_id: Optional[str] = None
    order_verified: bool = False
    eligible: bool = False
    customer_confirmed: bool = False

RETURN_TOOLS_BY_STEP = {
    ReturnStep.VERIFY_ORDER: [
        {
            "name": "get_order_by_id",
            "description": "Fetch order details to verify the order exists and belongs to this customer.",
            "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]},
        }
    ],
    ReturnStep.CHECK_ELIGIBILITY: [
        {
            "name": "check_return_eligibility",
            "description": "Check whether a verified order is within the return window and eligible for return.",
            "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]},
        }
    ],
    ReturnStep.INITIATE_RETURN: [
        {
            "name": "initiate_return",
            "description": "Initiate return for a confirmed eligible order. Not idempotent. Call only after customer confirmation.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["order_id", "reason"],
            },
        }
    ],
}

def step_system_prompt(state: ReturnState) -> str:
    return (
        f"You are a returns specialist. Current workflow step: {state.current_step.value}. "
        f"Order ID collected: {state.order_id or 'not yet collected'}. "
        f"Complete the current step, then respond with STEP_COMPLETE if the step is done."
    )

def handle_return_request(conversation_history: list[dict], state: ReturnState) -> tuple[str, ReturnState]:
    """Execute one step of the returns workflow and advance the state if complete."""
    if state.current_step == ReturnStep.COMPLETE:
        return "Your return has been initiated. You will receive a confirmation email shortly.", state

    if state.current_step == ReturnStep.CONFIRM_WITH_CUSTOMER:
        # This step is handled by conversation, not a tool call
        last_user_message = next((m["content"] for m in reversed(conversation_history) if m["role"] == "user"), "")
        affirmative = any(word in last_user_message.lower() for word in ["yes", "confirm", "proceed", "go ahead"])
        if affirmative:
            state.customer_confirmed = True
            state.current_step = ReturnStep.INITIATE_RETURN
        else:
            return "Please confirm you'd like to proceed with the return by saying 'yes'.", state

    tools = RETURN_TOOLS_BY_STEP.get(state.current_step, [])
    system = step_system_prompt(state)
    messages = list(conversation_history)

    for _ in range(4):  # tight per-step budget
        response = client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=512,
            system=system,
            tools=tools,
            messages=messages,
        )
        if response.stop_reason == "end_turn":
            text = next((b.text for b in response.content if hasattr(b, "text")), "")
            if "STEP_COMPLETE" in text:
                # Advance the state machine to the next step
                steps = list(ReturnStep)
                idx = steps.index(state.current_step)
                state.current_step = steps[min(idx + 1, len(steps) - 1)]
            return text.replace("STEP_COMPLETE", "").strip(), state

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                if block.name == "get_order_by_id":
                    state.order_id = block.input.get("order_id")
                    result = json.dumps({"success": True, "data": {"id": state.order_id, "product": "blue kettle", "status": "delivered"}})
                    state.order_verified = True
                elif block.name == "check_return_eligibility":
                    result = json.dumps({"success": True, "data": {"eligible": True, "reason": "within 30-day window"}})
                    state.eligible = True
                else:
                    result = json.dumps({"success": True, "data": {"return_id": "RET-8821", "status": "initiated"}})
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
        messages.append({"role": "user", "content": tool_results})

    return "Could not complete the current step. Escalating to a human agent.", state

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = step_system_prompt(None)
        print(result)
