"""
Chapter 6 — Tool Use and Function Calling — Example 4
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch06_04_OrderInfo.py
"""
# requires ANTHROPIC_API_KEY
import anthropic
import uuid, json
from typing import TypedDict

client = anthropic.Anthropic()

# ── Typed return types (makes tool results auditable) ──
class OrderInfo(TypedDict):
    order_id: str
    status: str          # "shipped" | "processing" | "delivered" | "cancelled"
    total_usd: float
    items: list

class RefundResult(TypedDict):
    idempotency_key: str
    order_id: str
    refunded_usd: float
    status: str          # "approved" | "already_processed" | "rejected"

class EscalationResult(TypedDict):
    ticket_id: str
    queue: str
    estimated_wait_minutes: int

# ── Tool implementations (stubs — replace with real DB/payment calls) ──
def lookup_order(order_id: str) -> OrderInfo:
    return OrderInfo(order_id=order_id, status="delivered",
                     total_usd=129.99, items=["Widget Pro x1"])

def issue_refund(order_id: str, amount_usd: float,
                 idempotency_key: str) -> RefundResult:
    # idempotency_key prevents double-refunds on retries.
    # Real impl: check DB for existing key before calling payment provider
    return RefundResult(idempotency_key=idempotency_key, order_id=order_id,
                        refunded_usd=amount_usd, status="approved")

def escalate_to_human(order_id: str, reason: str,
                      priority: str = "normal") -> EscalationResult:
    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
    return EscalationResult(ticket_id=ticket_id, queue="tier-2",
                            estimated_wait_minutes=12)

# ── Tool schemas passed to the model ──
TOOLS = [
    {
        "name": "lookup_order",
        "description": "Look up an order by ID. Returns status, total, and items.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "issue_refund",
        "description": (
            "Issue a refund for an order. Requires an idempotency_key "
            "(UUID) to prevent duplicate charges. Only call after confirming "
            "the order is eligible for a refund."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id":         {"type": "string"},
                "amount_usd":       {"type": "number"},
                "idempotency_key":  {"type": "string",
                                    "description": "Client-generated UUID v4"},
            },
            "required": ["order_id", "amount_usd", "idempotency_key"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": "Escalate to a human agent when the issue cannot be resolved automatically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "reason":   {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "normal", "urgent"]},
            },
            "required": ["order_id", "reason"],
        },
    },
]

DISPATCH = {
    "lookup_order":      lambda a: lookup_order(**a),
    "issue_refund":      lambda a: issue_refund(**a),
    "escalate_to_human": lambda a: escalate_to_human(**a),
}

def run_support_agent(customer_message: str) -> str:
    messages = [{"role": "user", "content": customer_message}]
    for _ in range(10):
        resp = client.messages.create(
            model="claude-sonnet-4-5", max_tokens=1024,
            tools=TOOLS, messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason == "end_turn":
            return next((b.text for b in resp.content if hasattr(b, "text")), "")
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                out = DISPATCH[b.name](b.input)
                results.append({"type": "tool_result", "tool_use_id": b.id,
                                 "content": json.dumps(out)})
        messages.append({"role": "user", "content": results})
    return "[Escalating: max steps reached]"

if __name__ == "__main__":
    print(run_support_agent("My order #ORD-4821 arrived damaged. Can I get a refund?"))
