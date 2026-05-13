"""
Chapter 8 — Planning and Decomposition — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch08_01_CompanyEvent.py
"""
# ch08_reflexion.py
# Tested against Claude Sonnet 4.6 (claude-sonnet-4-6-20250514),
# Anthropic SDK 0.49.0, as of April 2026.
# Requires: anthropic>=0.49, pydantic>=2.0

import json
import anthropic
from pydantic import BaseModel, ValidationError
from typing import Optional

client = anthropic.Anthropic()

class CompanyEvent(BaseModel):  # ① the target schema the extraction must satisfy
    company_name: str
    event_type: str
    date: str  # YYYY-MM-DD
    financial_impact_usd_millions: Optional[float]
    summary: str

EXTRACT_SYSTEM = """
You are a financial data extraction assistant.
Given a news article, extract the primary company event into a JSON object.
The JSON must match this schema exactly:
{schema}
Output ONLY the JSON object, no explanation.
"""

REFLECT_SYSTEM = """
You are a self-critic reviewing a failed extraction attempt.
You will be given:
1. The original text
2. The extraction attempt that failed
3. The validation error that explains why it failed

Write a brief reflection (3-5 sentences) identifying:
- What was wrong with the extraction
- What specific field or format rule was violated
- What the corrected approach should be

Do not produce JSON. Produce only a plain-text reflection.
"""

def extract_with_reflexion(article_text: str, max_retries: int = 3) -> CompanyEvent:
    """Extract a CompanyEvent from article text, retrying with reflection on validation failure."""
    schema_str = json.dumps(CompanyEvent.model_json_schema(), indent=2)
    system = EXTRACT_SYSTEM.format(schema=schema_str)
    messages = [{"role": "user", "content": article_text}]
    reflections = []  # ② accumulate reflections across retries

    for attempt in range(max_retries):  # ③ bounded retry loop
        response = client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=512,
            system=system,
            messages=messages,
        )
        raw = response.content[0].text.strip()

        try:
            parsed = json.loads(raw)
            event = CompanyEvent(**parsed)  # validate against Pydantic schema
            return event  # success
        except (json.JSONDecodeError, ValidationError) as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Extraction failed after {max_retries} attempts. Last error: {e}")

            # ④ generate a reflection on the failure
            reflect_messages = [
                {"role": "user", "content": (
                    f"Original text:\n{article_text}\n\n"
                    f"Failed extraction:\n{raw}\n\n"
                    f"Validation error:\n{str(e)}"
                )}
            ]
            reflect_response = client.messages.create(
                model="claude-sonnet-4-6-20250514",
                max_tokens=256,
                system=REFLECT_SYSTEM,
                messages=reflect_messages,
            )
            reflection = reflect_response.content[0].text.strip()
            reflections.append(reflection)

            # ⑤ inject the reflection into the extraction context before retrying
            reflection_tag = f"[REFLECTION from attempt {attempt + 1}]: {reflection}"
            messages = [
                {"role": "user", "content": article_text},
                {"role": "assistant", "content": raw},
                {"role": "user", "content": reflection_tag + "\n\nPlease try the extraction again, applying this correction."},
            ]

    raise RuntimeError("Unreachable")

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = extract_with_reflexion('example', 3)
        print(result)
