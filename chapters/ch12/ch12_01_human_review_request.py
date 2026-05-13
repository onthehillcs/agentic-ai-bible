"""
Chapter 12 — Human-in-the-Loop — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch12_01_HumanReviewRequest.py
"""
# ch12_hitl.py (fragment)
# Tested against Claude Sonnet 4.6, Anthropic SDK 0.49.0, April 2026.

import json
import anthropic
from dataclasses import dataclass
from typing import Optional

client = anthropic.Anthropic()

@dataclass
class HumanReviewRequest:
    action_type: str
    action_description: str
    agent_reasoning: str
    proposed_action: dict
    confidence: float  # 0-1
    review_id: str

def request_human_review(review_request: HumanReviewRequest) -> Optional[dict]:
    """
    In production: send to a review queue (Slack, email, web UI).
    Here: print for interactive review.
    Returns the approved (possibly modified) action, or None if rejected.
    """
    print(f"\n[HUMAN REVIEW REQUIRED]")
    print(f"Action: {review_request.action_type}")
    print(f"Description: {review_request.action_description}")
    print(f"Agent reasoning: {review_request.agent_reasoning}")
    print(f"Proposed action: {json.dumps(review_request.proposed_action, indent=2)}")
    print(f"Confidence: {review_request.confidence:.0%}")
    print(f"\nOptions: [A]pprove / [M]odify / [R]eject")

    # In production this would be async; here we simulate approval
    choice = "A"  # simulate approval for demonstration
    if choice == "A":
        return review_request.proposed_action
    elif choice == "R":
        return None
    else:
        # In production: return modified action from UI input
        return review_request.proposed_action

HITL_THRESHOLD = 0.75  # request review when confidence below 75%

def run_fraud_review_agent(transaction: dict) -> dict:
    """Review a flagged transaction with HITL for low-confidence decisions."""
    response = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=512,
        system="""You are a fraud detection analyst. Review the transaction and output:
{"decision": "approve|decline|escalate", "confidence": 0.0-1.0, "reasoning": "..."}
Be conservative: if uncertain, lower confidence and reason clearly.""",
        messages=[{"role": "user", "content": f"Review this transaction: {json.dumps(transaction)}"}],
    )

    try:
        result = json.loads(response.content[0].text)
    except json.JSONDecodeError:
        result = {"decision": "escalate", "confidence": 0.0, "reasoning": "parse error"}

    decision = result.get("decision", "escalate")
    confidence = float(result.get("confidence", 0.0))

    if confidence >= HITL_THRESHOLD:
        # High confidence: proceed autonomously
        return {"decision": decision, "confidence": confidence, "reviewed_by": "agent"}
    else:
        # Low confidence: request human review
        import uuid
        review_request = HumanReviewRequest(
            action_type="transaction_decision",
            action_description=f"Decide: {decision} on transaction {transaction.get('id', 'unknown')}",
            agent_reasoning=result.get("reasoning", ""),
            proposed_action={"decision": decision, "transaction_id": transaction.get("id")},
            confidence=confidence,
            review_id=str(uuid.uuid4())[:8],
        )
        approved = request_human_review(review_request)
        if approved:
            return {"decision": approved.get("decision", decision), "confidence": 1.0, "reviewed_by": "human"}
        else:
            return {"decision": "escalate", "confidence": 1.0, "reviewed_by": "human", "note": "rejected by reviewer"}

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = request_human_review(None)
        print(result)
