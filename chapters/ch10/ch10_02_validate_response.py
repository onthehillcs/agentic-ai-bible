"""
Chapter 10 — Single-Agent Patterns — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch10_02_validate_response.py
"""
# ch10_validator.py (fragment)

VALIDATOR_SYSTEM = """You are a quality reviewer for customer support responses.
Check the response against these rules:
1. Does not promise a specific delivery date (we cannot guarantee dates)
2. Does not offer refunds above the policy amount ($50 without manager approval)
3. Does not include order details the agent may have hallucinated

Output: {"pass": true} if all rules are satisfied.
Output: {"pass": false, "reason": "<specific rule violated>"} if any rule is violated."""

def validate_response(customer_message: str, agent_response: str) -> tuple[bool, str]:
    """Validate agent response before returning to user. Returns (passed, response_or_reason)."""
    check = client.messages.create(
        model="claude-haiku-3-5-20241022",  # cheap model for validation
        max_tokens=64,
        system=VALIDATOR_SYSTEM,
        messages=[{"role": "user", "content": f"Customer: {customer_message}\nResponse: {agent_response}"}],
    )
    try:
        result = json.loads(check.content[0].text)
        if result["pass"]:
            return True, agent_response
        return False, result.get("reason", "validation failed")
    except (json.JSONDecodeError, KeyError):
        return True, agent_response  # fail open if validator itself fails

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = validate_response('example', 'example')
        print(result)
