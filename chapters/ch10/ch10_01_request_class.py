"""
Chapter 10 — Single-Agent Patterns — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch10_01_RequestClass.py
"""
# ch10_router_executor.py
# Tested against Claude Sonnet 4.6 (claude-sonnet-4-6-20250514),
# Anthropic SDK 0.49.0, as of April 2026.
# Requires: anthropic>=0.49

import json
import anthropic
from enum import Enum

client = anthropic.Anthropic()

class RequestClass(str, Enum):
    ORDER_STATUS = "order_status"
    RETURN = "return"
    PRODUCT = "product"
    ESCALATION = "escalation"
    OFF_TOPIC = "off_topic"

ROUTER_SYSTEM = """You are a request classifier for a customer support system.
Classify the customer message into exactly one of these categories:
- order_status: questions about order status, shipping, delivery
- return: requests to return or refund a product
- product: questions about product features, availability, or specifications
- escalation: explicit requests to speak with a human agent
- off_topic: anything not related to orders, products, or support

Output ONLY a JSON object with a single field: {"class": "<category>"}"""

def route_request(customer_message: str) -> RequestClass:  # router call
    response = client.messages.create(
        model="claude-haiku-3-5-20241022",  # cheap model for routing
        max_tokens=32,
        system=ROUTER_SYSTEM,
        messages=[{"role": "user", "content": customer_message}],
    )
    try:
        result = json.loads(response.content[0].text)
        return RequestClass(result["class"])
    except (json.JSONDecodeError, ValueError, KeyError):
        return RequestClass.OFF_TOPIC  # safe default

ORDER_TOOLS = [
    {
        "name": "get_order_status",
        "description": "Get the current status and tracking info for an order by order ID.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
]

RETURN_TOOLS = [
    {
        "name": "check_return_eligibility",
        "description": "Check if an order is eligible for return based on purchase date and product type.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "initiate_return",
        "description": (
            "Initiate a return for an eligible order. Not idempotent: do not call more than once. "
            "Only call after confirming eligibility with check_return_eligibility."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["order_id", "reason"],
        },
    },
]

def execute_request(request_class: RequestClass, customer_message: str) -> str:
    """Dispatch to the appropriate executor based on the router's classification."""
    if request_class == RequestClass.ORDER_STATUS:
        tools = ORDER_TOOLS
        system = "You are a customer support agent specializing in order status and shipping questions. Be concise and specific."
    elif request_class == RequestClass.RETURN:
        tools = RETURN_TOOLS
        system = "You are a customer support agent specializing in returns. Always verify eligibility before initiating a return."
    elif request_class == RequestClass.ESCALATION:
        return "I understand you'd like to speak with a human agent. I'm connecting you now. Reference ID: ESC-" + str(hash(customer_message))[-6:]
    else:
        return "I can help with order status, returns, and product questions. Could you clarify what you need?"

    messages = [{"role": "user", "content": customer_message}]
    for _ in range(8):
        response = client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=1024,
            system=system,
            tools=tools,
            messages=messages,
        )
        if response.stop_reason == "end_turn":
            return next((b.text for b in response.content if hasattr(b, "text")), "")
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                # In production: dispatch to real implementations
                result = json.dumps({"success": True, "data": {"status": "demo_result"}})
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
        messages.append({"role": "user", "content": tool_results})
    return "Request exceeded processing budget."

def handle_customer_message(customer_message: str) -> str:
    request_class = route_request(customer_message)
    return execute_request(request_class, customer_message)

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = route_request('example')
        print(result)
