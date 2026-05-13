"""
Chapter 12 — Human-in-the-Loop — Example 3
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch12_03_review_queue_page.py
"""
# ch12_review_interface.py
# Review queue web endpoint using FastAPI.
# Serves HTML directly for simplicity; production would use a frontend framework.
# Requires: fastapi>=0.110, uvicorn>=0.29

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import json
import time

app = FastAPI()

# Shared pending_reviews store (import from ch12_async_hitl.py in production)
_pending_reviews: dict[str, dict] = {}  # populated by the agent service
_review_outcomes: list[dict] = []       # audit log


@app.get("/review", response_class=HTMLResponse)
def review_queue_page():
    """Render the review queue as a simple HTML page."""
    if not _pending_reviews:
        return "<html><body><h2>No pending reviews.</h2></body></html>"

    items_html = ""
    for r in _pending_reviews.values():
        action = json.dumps(r.get("proposed_action", {}), indent=2)
        age_seconds = int(time.time() - r.get("created_at", time.time()))
        items_html += f"""
        <div style="border:1px solid #ccc; margin:16px; padding:16px; font-family:monospace">
          <h3>Review ID: {r['review_id']} &nbsp; <small style='color:gray'>({age_seconds}s ago)</small></h3>
          <p><b>Proposed action:</b><pre>{action}</pre></p>
          <p><b>Agent reasoning:</b> {r.get('agent_reasoning', 'N/A')}</p>
          <form method="post" action="/review/submit">
            <input type="hidden" name="review_id" value="{r['review_id']}" />
            <input type="hidden" name="run_id" value="{r['run_id']}" />
            <label>Decision:
              <select name="decision">
                <option value="approve">Approve</option>
                <option value="modify">Modify</option>
                <option value="reject">Reject</option>
              </select>
            </label>&nbsp;
            <label>Modified action (JSON, only if modifying):
              <input type="text" name="modified_action" size="60" placeholder='{{"decision": "escalate"}}' />
            </label>&nbsp;
            <button type="submit">Submit</button>
          </form>
        </div>
        """
    return f"<html><body><h2>Pending Reviews ({len(_pending_reviews)})</h2>{items_html}</body></html>"


@app.post("/review/submit", response_class=HTMLResponse)
def submit_review(
    review_id: str = Form(...),
    run_id: str = Form(...),
    decision: str = Form(...),
    modified_action: str = Form(""),
):
    """Process a reviewer's decision and remove from queue."""
    if review_id not in _pending_reviews:
        return "<html><body><p>Review not found or already processed.</p></body></html>"

    parsed_modification = None
    if decision == "modify" and modified_action.strip():
        try:
            parsed_modification = json.loads(modified_action)
        except json.JSONDecodeError:
            return "<html><body><p>Invalid JSON in modified action.</p></body></html>"

    outcome = {
        "review_id": review_id,
        "run_id": run_id,
        "decision": decision,
        "modified_action": parsed_modification,
        "reviewer_id": "web_reviewer",
        "submitted_at": time.time(),
    }
    _pending_reviews.pop(review_id, None)
    _review_outcomes.append(outcome)

    # In production: POST outcome to the agent service's callback endpoint
    # requests.post("http://agent-service/review/callback", json=outcome)

    return f"<html><body><p>Review {review_id} submitted: {decision}. <a href='/review'>Back to queue</a></p></body></html>"


@app.get("/review/audit")
def review_audit_log():
    """Return the audit log of all submitted review decisions."""
    return {"outcomes": _review_outcomes}

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = review_queue_page()
        print(result)
