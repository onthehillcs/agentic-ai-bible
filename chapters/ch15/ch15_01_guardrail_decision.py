"""
Chapter 15 — Safety, Alignment, and Guardrails — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch15_01_GuardrailDecision.py
"""
# Tested with Python 3.11, openai==1.14.0, regex==2023.12.25
# Input guardrail stack for a financial wellness agent

import re
import json
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from openai import OpenAI

client = OpenAI()


class GuardrailDecision(Enum):
    ALLOW = "allow"          # Request is in scope, proceed normally
    ESCALATE = "escalate"    # Request is borderline, route to human
    BLOCK = "block"          # Request is prohibited, return canned refusal


@dataclass
class GuardrailResult:
    decision: GuardrailDecision
    triggered_rule: Optional[str]  # Which rule caused BLOCK or ESCALATE
    confidence: float              # 0.0 to 1.0 confidence in the decision
    explanation: str               # Human-readable reason for the decision


# Hard blocklist: patterns that always block, regardless of context
# These represent absolute prohibitions with no escalation path
HARD_BLOCK_PATTERNS = [
    # Investment advice patterns
    r'\b(buy|sell|short)\s+(\d+\s+shares?\s+of\s+)?[A-Z]{1,5}\b',  # "buy AAPL"
    r'\bspecific\s+(stock|etf|fund|security)\s+recommendation',
    r'\bportfolio\s+allocation\s+percentages?\b',
    # Regulatory red lines
    r'\b(guaranteed|risk.free)\s+(return|profit|gain)\b',
    r'\btax\s+(evasion|avoidance\s+scheme)\b',
    # Prompt injection patterns (see Chapter 16 for full coverage)
    r'ignore\s+(all\s+)?previous\s+instructions',
    r'you\s+are\s+now\s+(a\s+)?different\s+(ai|assistant|agent)',
    r'disregard\s+your\s+system\s+prompt',
]

# Soft escalation triggers: route to human but don't block
SOFT_ESCALATE_PATTERNS = [
    r'\bshould\s+i\s+(invest|buy|sell)\b',
    r'\bwhich\s+(fund|etf|stock)\s+should\b',
    r'\bwhat\s+(would|should)\s+you\s+recommend\s+(for\s+my|as\s+a)\b',
    r'\bam\s+i\s+(taking\s+too\s+much\s+risk|over.?exposed)\b',
]


def check_hard_blocklist(user_message: str) -> Optional[GuardrailResult]:
    """Fast pattern-matching blocklist check. Returns None if message passes."""
    msg_lower = user_message.lower()
    
    for pattern in HARD_BLOCK_PATTERNS:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            return GuardrailResult(
                decision=GuardrailDecision.BLOCK,
                triggered_rule=f"hard_block:{pattern[:40]}",
                confidence=1.0,
                explanation="Request matches a prohibited pattern that cannot be processed."
            )
    return None


def check_soft_escalation(user_message: str) -> Optional[GuardrailResult]:
    """Pattern matching for requests that need human escalation."""
    msg_lower = user_message.lower()
    
    for pattern in SOFT_ESCALATE_PATTERNS:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            return GuardrailResult(
                decision=GuardrailDecision.ESCALATE,
                triggered_rule=f"soft_escalate:{pattern[:40]}",
                confidence=0.8,
                explanation="Request may be seeking specific investment advice. Routing to licensed advisor."
            )
    return None


def classify_with_llm(user_message: str, agent_scope: str) -> GuardrailResult:
    """Use a fast LLM call to classify requests that pass pattern checks.
    
    Uses gpt-4o-mini to minimize latency and cost on this high-frequency path.
    Caching this call by message hash reduces cost by ~70% for repeated queries.
    """
    classification_prompt = f"""You are a content classifier for a {agent_scope}.
    
Classify the following user message into one of three categories:
- ALLOW: clearly within the agent's scope and appropriate to answer
- ESCALATE: borderline; may be seeking advice the agent isn't licensed to give
- BLOCK: clearly outside scope or potentially harmful

Respond with JSON: {{"decision": "ALLOW|ESCALATE|BLOCK", "confidence": 0.0-1.0, "reason": "brief explanation"}}

User message: {user_message[:500]}"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": classification_prompt}],
        temperature=0.0,
        response_format={"type": "json_object"},
        max_tokens=100,
    )
    
    raw = json.loads(response.choices[0].message.content)
    decision_str = raw.get("decision", "ALLOW").upper()
    
    try:
        decision = GuardrailDecision[decision_str]
    except KeyError:
        decision = GuardrailDecision.ALLOW
    
    return GuardrailResult(
        decision=decision,
        triggered_rule="llm_classifier",
        confidence=float(raw.get("confidence", 0.7)),
        explanation=raw.get("reason", "LLM classification")
    )


def check_input(
    user_message: str,
    agent_scope: str = "financial wellness coach that helps with budgeting and saving"
) -> GuardrailResult:
    """Run the full input guardrail stack. Fast path first, LLM last."""
    
    # Layer 1: Hard blocklist (sub-millisecond)
    result = check_hard_blocklist(user_message)
    if result is not None:
        return result
    
    # Layer 2: Soft escalation patterns (sub-millisecond)
    result = check_soft_escalation(user_message)
    if result is not None:
        return result
    
    # Layer 3: LLM classifier (50-150ms) - only reached if layers 1 and 2 pass
    return classify_with_llm(user_message, agent_scope)

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = check_hard_blocklist('example')
        print(result)
