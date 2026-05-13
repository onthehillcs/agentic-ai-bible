"""
Chapter 12 — Human-in-the-Loop — Example 6
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch12_06_HITLRequest.py
"""
# requires ANTHROPIC_API_KEY
import anthropic, json, uuid
from dataclasses import dataclass

client = anthropic.Anthropic()

@dataclass
class HITLRequest:
    reason: str
    tool_name: str
    tool_input: dict
    ticket_id: str

pending_approvals: dict = {}   # in prod: persistent queue

def request_human_approval(tool_name: str, tool_input: dict, reason: str) -> str:
    # Pause the agent and return a ticket ID for the approver to act on.
    ticket = f"HITL-{uuid.uuid4().hex[:8].upper()}"
    pending_approvals[ticket] = HITLRequest(
        reason=reason, tool_name=tool_name,
        tool_input=tool_input, ticket_id=ticket
    )
    # In production: push to Slack / PagerDuty / approval queue
    print(f"[HITL] Approval required — ticket {ticket}\n"
          f"  Tool: {tool_name}\n  Input: {tool_input}\n  Reason: {reason}")
    return ticket

def hitl_intercept(tool_name: str, tool_input: dict, confidence: float):
    # Returns (proceed, reason).
    # proceed=False means the tool call is blocked pending human review.
    if tool_name == "issue_refund":
        amount = tool_input.get("amount_usd", 0)
        if amount > 500:
            ticket = request_human_approval(
                tool_name, tool_input,
                f"Refund ${amount:.2f} exceeds $500 auto-approval threshold"
            )
            return False, f"Pending human approval — ticket {ticket}"
    if confidence < 0.7:
        ticket = request_human_approval(
            tool_name, tool_input,
            f"Agent confidence {confidence:.2f} below 0.70 threshold"
        )
        return False, f"Pending human approval (low confidence) — ticket {ticket}"
    return True, ""

def get_agent_confidence(messages: list) -> float:
    # Ask the model to self-assess confidence before a consequential action.
    probe = messages + [{
        "role": "user",
        "content": "Before taking any action, rate your confidence that "
                   "you have correctly understood the issue and chosen the "
                   "right action (0.0–1.0). Reply with only a number."
    }]
    resp = client.messages.create(
        model="claude-haiku-4-5", max_tokens=8, messages=probe
    )
    try:
        return float(resp.content[0].text.strip())
    except ValueError:
        return 0.5   # default to cautious if parse fails

def run_support_agent_with_hitl(customer_message: str, TOOLS: list, DISPATCH: dict) -> str:
    messages = [{"role": "user", "content": customer_message}]
    for _ in range(10):
        resp = client.messages.create(
            model="claude-sonnet-4-5", max_tokens=1024,
            tools=TOOLS, messages=messages
        )
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason == "end_turn":
            return next((b.text for b in resp.content if hasattr(b, "text")), "")
        results = []
        for b in resp.content:
            if b.type != "tool_use":
                continue
            confidence = get_agent_confidence(messages)
            proceed, block_reason = hitl_intercept(b.name, b.input, confidence)
            if not proceed:
                results.append({"type": "tool_result", "tool_use_id": b.id,
                                 "content": json.dumps({"status": "blocked",
                                                        "reason": block_reason})})
            else:
                out = DISPATCH[b.name](b.input)
                results.append({"type": "tool_result", "tool_use_id": b.id,
                                 "content": json.dumps(out)})
        messages.append({"role": "user", "content": results})
    return "[Max steps reached]"

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = request_human_approval('example', {}, 'example')
        print(result)
