"""
Chapter 15 — Safety, Alignment, and Guardrails — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch15_02_OutputGuardrailResult.py
"""
# Tested with Python 3.11, openai==1.14.0
# Output guardrail stack: policy compliance + factual grounding + format validation

import json
import re
from typing import Optional
from openai import OpenAI

client = OpenAI()


@dataclass
class OutputGuardrailResult:
    approved: bool
    violations: list[str]  # List of policy violations found
    modified_response: Optional[str]  # Non-None if response was modified to fix violations
    required_disclaimer_added: bool


# Required disclaimers that must appear in financial wellness responses
FINANCIAL_DISCLAIMERS = [
    "This is not financial advice",
    "consult a licensed financial advisor",
    "past performance does not guarantee",
]

# Patterns that should never appear in output
OUTPUT_BLOCK_PATTERNS = [
    r'\b(buy|sell)\s+[A-Z]{2,5}\b',              # Ticker recommendations
    r'\bI\s+recommend\s+(buying|selling)\b',
    r'\byou\s+should\s+(invest|put)\s+\d+%\b',   # Specific allocation advice
    r'\bguaranteed\s+return\b',
]


def check_output_patterns(response_text: str) -> list[str]:
    """Check for prohibited patterns in the response."""
    violations = []
    for pattern in OUTPUT_BLOCK_PATTERNS:
        if re.search(pattern, response_text, re.IGNORECASE):
            violations.append(f"Prohibited pattern detected: {pattern[:50]}")
    return violations


def check_disclaimer_presence(response_text: str, required: list[str]) -> tuple[bool, str]:
    """Check for required disclaimers; append missing ones."""
    text_lower = response_text.lower()
    missing = [d for d in required if d.lower() not in text_lower]
    
    if not missing:
        return True, response_text
    
    # Append the standard disclaimer block
    disclaimer = (
        "\n\n*Note: This information is for educational purposes only and does not "
        "constitute financial advice. Please consult a licensed financial advisor "
        "before making investment decisions.*"
    )
    return False, response_text + disclaimer


def verify_factual_grounding(
    response_text: str,
    source_documents: list[str],
    claim_threshold: float = 0.8,
) -> list[str]:
    """Use LLM to check whether factual claims in the response are grounded in sources.
    
    Returns a list of ungrounded claims. Empty list means all claims are grounded.
    Only runs when source_documents are available; skips for knowledge-based responses.
    """
    if not source_documents:
        return []  # No sources to check against
    
    sources_text = "\n---\n".join(source_documents[:5])  # Check against top 5 sources
    
    check_prompt = f"""Review this response and the provided source documents.
Identify any specific factual claims in the response that are NOT supported by the sources.
Return JSON: {{"ungrounded_claims": ["claim 1", "claim 2", ...]}}
Return an empty list if all claims are grounded.

Response: {response_text[:1000]}

Sources:\n{sources_text[:3000]}"""
    
    result = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": check_prompt}],
        temperature=0.0,
        response_format={"type": "json_object"},
        max_tokens=200,
    )
    
    raw = json.loads(result.choices[0].message.content)
    return raw.get("ungrounded_claims", [])


def check_output(
    response_text: str,
    source_documents: list[str] = None,
    require_disclaimers: bool = True,
) -> OutputGuardrailResult:
    """Run the full output guardrail stack."""
    violations = []
    modified = response_text
    disclaimer_added = False
    
    # Check for prohibited output patterns
    pattern_violations = check_output_patterns(response_text)
    violations.extend(pattern_violations)
    
    # Check factual grounding (only if sources are provided)
    if source_documents:
        ungrounded = verify_factual_grounding(response_text, source_documents)
        violations.extend([f"Ungrounded claim: {c}" for c in ungrounded])
    
    # Ensure required disclaimers are present (modify response if needed)
    if require_disclaimers and not violations:
        # Only add disclaimers if we're not blocking the response entirely
        has_disclaimers, modified = check_disclaimer_presence(
            modified, FINANCIAL_DISCLAIMERS
        )
        disclaimer_added = not has_disclaimers
    
    return OutputGuardrailResult(
        approved=len(violations) == 0,
        violations=violations,
        modified_response=modified if (modified != response_text) else None,
        required_disclaimer_added=disclaimer_added,
    )

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = check_output_patterns('example')
        print(result)
