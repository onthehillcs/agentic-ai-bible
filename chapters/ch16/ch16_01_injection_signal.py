"""
Chapter 16 — Security — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch16_01_InjectionSignal.py
"""
# Tested with Python 3.11, openai==1.14.0
# Injection detection: output monitoring for anomalous tool calls

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class InjectionSignal:
    detected: bool
    confidence: float
    indicators: list[str]
    recommended_action: str  # 'block', 'alert', 'allow'


# Tools the agent is allowed to call in this context
ALLOWED_TOOLS = {"search_kb", "lookup_order", "get_product_info"}

# Patterns in tool arguments that indicate injection
SUSPICIOUS_ARG_PATTERNS = [
    r'https?://(?!trusted-api\.example\.com)[\w.-]+',  # Unexpected external URLs
    r'\$\{?[A-Z_]{3,}\}?',                              # Environment variable references
    r'/etc/(?:passwd|shadow|hosts)',                     # Sensitive file paths
    r'(?:rm|delete|drop|truncate)\s+',                  # Destructive commands
    r'base64\s*(?:decode|encode)',                       # Data encoding (exfil signal)
    r'curl|wget|fetch.*http',                            # Direct HTTP calls from args
]

# Patterns in agent reasoning text that indicate injection is occurring
SUSPICIOUS_REASONING_PATTERNS = [
    r'new\s+instructions?\s*:',
    r'system\s+override',
    r'ignore\s+(?:previous|all|your)',
    r'as\s+(?:a\s+)?(?:different|new|updated)\s+(?:ai|assistant)',
    r'your\s+(?:true|real|actual)\s+(?:purpose|goal|mission)',
]


def detect_injection_in_tool_call(
    tool_name: str,
    tool_args: dict,
    agent_reasoning: str = "",
) -> InjectionSignal:
    """Analyze a proposed tool call for signs of prompt injection.
    
    This runs before the tool call is executed, providing a pre-execution
    gate that can block suspicious calls before they cause harm.
    """
    indicators = []
    
    # Check if the tool itself is unexpected
    if tool_name not in ALLOWED_TOOLS:
        indicators.append(f"Unexpected tool called: {tool_name} (not in allowed set)")
    
    # Check tool arguments for suspicious patterns
    args_str = str(tool_args)
    for pattern in SUSPICIOUS_ARG_PATTERNS:
        if re.search(pattern, args_str, re.IGNORECASE):
            indicators.append(f"Suspicious argument pattern: {pattern[:40]}")
    
    # Check agent reasoning for injection markers
    for pattern in SUSPICIOUS_REASONING_PATTERNS:
        if re.search(pattern, agent_reasoning, re.IGNORECASE):
            indicators.append(f"Injection language in reasoning: {pattern[:40]}")
    
    if not indicators:
        return InjectionSignal(
            detected=False,
            confidence=0.0,
            indicators=[],
            recommended_action='allow'
        )
    
    # Score by number and severity of indicators
    confidence = min(0.3 * len(indicators), 1.0)
    action = 'block' if confidence >= 0.6 else 'alert'
    
    return InjectionSignal(
        detected=True,
        confidence=confidence,
        indicators=indicators,
        recommended_action=action
    )

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = detect_injection_in_tool_call('example', {}, 'example')
        print(result)
