"""
Chapter 21 — Case Studies — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch21_02_ExtractedFact.py
"""
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
import anthropic

client = anthropic.Anthropic()

@dataclass
class ExtractedFact:
    competitor: str
    fact: str
    source_url: str
    publication_date: str
    confidence: float  # 0.0 to 1.0
    category: str  # "product", "pricing", "partnership", "regulatory", "marketing"

@dataclass
class WeeklyReport:
    week_ending: str
    facts: list[ExtractedFact] = field(default_factory=list)
    synthesis: str = ""
    diff_from_prior: str = ""

def extract_facts_from_content(
    raw_content: list[dict],
    competitor_name: str
) -> list[ExtractedFact]:
    """
    Given raw content snippets from the search stage,
    extract structured competitive intelligence facts.
    Each content item has: {text, url, date}
    """
    if not raw_content:
        return []

    content_block = "\n\n".join(
        f"Source: {item['url']}\nDate: {item['date']}\nContent:\n{item['text'][:2000]}"
        for item in raw_content
    )

    prompt = f"""You are extracting competitive intelligence facts about {competitor_name}.

Below are raw content snippets gathered this week. Extract distinct, factual claims about:
- New or changed product features
- Pricing changes (new tiers, price increases/decreases, new free tier limits)
- New partnerships or integrations
- Regulatory developments (licenses obtained, compliance certifications)
- Marketing message changes (new positioning, new target segments)

For each fact:
- Write it as a clear, specific claim ("X launched Y feature" not "X may be considering Y")
- Include the source URL and date
- Assign a confidence score: 1.0 = explicitly stated, 0.7 = clearly implied, 0.4 = inferred
- Assign a category from: product, pricing, partnership, regulatory, marketing

If you cannot find any substantive facts, return an empty list.

Respond with a JSON object with key "facts" containing a list of fact objects:
{{"competitor", "fact", "source_url", "publication_date", "confidence", "category"}}

Content to analyze:
{content_block}"""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[\w]*\n", "", text)
            text = re.sub(r"\n```$", "", text)
        data = json.loads(text)
        return [
            ExtractedFact(**f)
            for f in data.get("facts", [])
        ]
    except Exception:
        return []


if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        fact = ExtractedFact(
            competitor='Acme Corp',
            fact='Launched new enterprise tier',
            source_url='https://example.com',
            publication_date='2026-01-01',
            confidence=0.9,
            category='pricing',
        )
        print(fact)
