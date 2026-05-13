"""
Chapter 12 — Human-in-the-Loop — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch12_02_AgentRunState.py
"""
# ch12_async_hitl.py
# Async HITL with webhook-based review queue.
# Requires: fastapi>=0.110, uvicorn>=0.29, anthropic>=0.49

import json
import uuid
import time
from dataclasses import dataclass, field, asdict
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import anthropic

app = FastAPI()
client = anthropic.Anthropic()

# In production: use Redis or a database. Here: in-memory for clarity.
_pending_reviews: dict[str, dict] = {}  # review_id -> review payload
_suspended_runs: dict[str, dict] = {}   # run_id -> suspended run state


@dataclass
class AgentRunState:
    run_id: str
    transaction: dict
    agent_result: dict
    status: str = "pending_review"  # pending_review | resumed | complete
    human_decision: Optional[dict] = None
    created_at: float = field(default_factory=time.time)


class ReviewOutcome(BaseModel):
    review_id: str
    run_id: str
    decision: str          # approve | modify | reject
    modified_action: Optional[dict] = None
    reviewer_id: str


def suspend_for_review(run_state: AgentRunState, proposed_action: dict, reasoning: str) -> str:
    """Suspend a run and post a review request. Returns the review_id."""
    review_id = str(uuid.uuid4())[:12]
    review_payload = {
        "review_id": review_id,
        "run_id": run_state.run_id,
        "proposed_action": proposed_action,
        "agent_reasoning": reasoning,
        "transaction": run_state.transaction,
        "created_at": time.time(),
        "callback_url": f"http://localhost:8000/review/callback",
    }
    _pending_reviews[review_id] = review_payload
    _suspended_runs[run_state.run_id] = asdict(run_state)
    # In production: post review_payload to Slack, email, or a web review queue
    print(f"[ASYNC REVIEW] Review {review_id} queued for run {run_state.run_id}")
    return review_id


@app.post("/review/callback")
def receive_review_callback(outcome: ReviewOutcome):
    """Webhook endpoint: called by the review UI when a human submits their decision."""
    if outcome.run_id not in _suspended_runs:
        raise HTTPException(status_code=404, detail="Run not found or already resumed")
    if outcome.review_id not in _pending_reviews:
        raise HTTPException(status_code=404, detail="Review not found or already processed")

    run_data = _suspended_runs.pop(outcome.run_id)
    _pending_reviews.pop(outcome.review_id)

    # Restore run state and inject human decision
    run_state = AgentRunState(**run_data)
    if outcome.decision == "approve":
        run_state.human_decision = run_state.agent_result
    elif outcome.decision == "modify" and outcome.modified_action:
        run_state.human_decision = outcome.modified_action
    else:  # reject
        run_state.human_decision = {"decision": "escalate", "note": f"Rejected by {outcome.reviewer_id}"}
    run_state.status = "resumed"

    # Resume execution with the human decision
    final_result = _complete_run_after_review(run_state)
    return {"status": "resumed", "run_id": outcome.run_id, "final_result": final_result}


def _complete_run_after_review(run_state: AgentRunState) -> dict:
    """Complete a run after human review has provided a decision."""
    decision = run_state.human_decision or {"decision": "escalate"}
    return {
        "run_id": run_state.run_id,
        "transaction_id": run_state.transaction.get("id"),
        "decision": decision.get("decision"),
        "reviewed_by": "human",
        "completed_at": time.time(),
    }


@app.get("/review/pending")
def list_pending_reviews():
    """Return all pending review requests, for display in the review UI."""
    return {"pending": list(_pending_reviews.values())}

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = suspend_for_review(None, {}, 'example')
        print(result)
