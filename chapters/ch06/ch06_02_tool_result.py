"""
Chapter 6 — Tool Use and Function Calling — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch06_02_ToolResult.py
"""
# ch06_tool_set.py
# Tested against Claude Sonnet 4.6 (claude-sonnet-4-6-20250514),
# Anthropic SDK 0.49.0, as of April 2026.
# Requires: anthropic>=0.49, pydantic>=2.0

import json
import anthropic
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class ToolResult:
    success: bool
    data: Optional[dict]
    error: Optional[str]
    error_category: Optional[str]  # transient | input | resource | fatal

    def to_json(self) -> str:
        return json.dumps(asdict(self))


ORDERS = {
    "ORD-1042": {"id": "ORD-1042", "product": "blue kettle", "status": "delivered",
                 "total": 49.99, "customer_id": "C-887"},
    "ORD-1043": {"id": "ORD-1043", "product": "coffee grinder", "status": "in_transit",
                 "total": 89.99, "customer_id": "C-887"},
}
REFUND_POLICY = {"delivered": True, "in_transit": False, "cancelled": False}


def get_order_by_id(order_id: str) -> str:
    order = ORDERS.get(order_id)
    if order is None:
        return ToolResult(
            success=False, data=None,
            error=f"No order found with ID '{order_id}'. Verify the order ID with the customer.",
            error_category="resource",
        ).to_json()
    return ToolResult(success=True, data=order, error=None, error_category=None).to_json()


def issue_refund(order_id: str, reason: str) -> str:
    order = ORDERS.get(order_id)
    if order is None:
        return ToolResult(
            success=False, data=None,
            error=f"No order found with ID '{order_id}'. Do not retry; report to customer.",
            error_category="resource",
        ).to_json()
    if not REFUND_POLICY.get(order["status"], False):
        return ToolResult(
            success=False, data=None,
            error=(
                f"Order '{order_id}' has status '{order['status']}' and is not eligible for refund. "
                "Inform the customer of the policy and offer to escalate if they disagree."
            ),
            error_category="resource",
        ).to_json()
    return ToolResult(
        success=True,
        data={"refund_amount": order["total"], "status": "initiated"},
        error=None, error_category=None,
    ).to_json()


TOOLS = [
    {
        "name": "get_order_by_id",
        "description": (
            "Fetch a single order record by its exact order ID (format: ORD-NNNN). "
            "Use this when the customer has provided their order ID directly. "
            "If the customer does not know their order ID, do not call this tool; "
            "ask the customer to check their confirmation email first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID exactly as shown on the customer's confirmation (e.g. ORD-1042)."
                }
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "issue_refund",
        "description": (
            "Issue a refund for a delivered order. This tool is NOT idempotent: "
            "do not call it more than once for the same order, even on timeout. "
            "If this tool times out, call get_order_by_id to check whether the refund was "
            "recorded before retrying. Only call this tool after confirming the order is "
            "eligible using get_order_by_id. Requires: order_id and a brief reason."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The exact order ID (format: ORD-NNNN)."},
                "reason": {"type": "string", "description": "Short description of why the refund is being issued (max 100 chars)."}
            },
            "required": ["order_id", "reason"],
        },
    },
]


def dispatch_tool(name: str, args: dict) -> str:
    if name == "get_order_by_id":
        return get_order_by_id(**args)
    if name == "issue_refund":
        return issue_refund(**args)
    return ToolResult(
        success=False, data=None,
        error=f"Unknown tool '{name}'. This is a framework bug; escalate immediately.",
        error_category="fatal",
    ).to_json()


def run_support_agent(customer_message: str) -> str:
    client = anthropic.Anthropic()
    system = (
        "You are a customer support agent. Help customers with order questions and refunds. "
        "Always confirm order details before issuing a refund. "
        "If a refund is not eligible, explain the policy clearly and offer to escalate."
    )
    messages = [{"role": "user", "content": customer_message}]

    for step in range(10):
        response = client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=1024,
            system=system,
            tools=TOOLS,
            messages=messages,
        )
        if response.stop_reason == "end_turn":
            return next((b.text for b in response.content if hasattr(b, "text")), "")

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = dispatch_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        messages.append({"role": "user", "content": tool_results})

    return "Agent loop exceeded iteration budget. Escalating to human agent."

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = get_order_by_id('abc-123')
        print(result)
