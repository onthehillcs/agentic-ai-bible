"""
Chapter 19 — Computer-Use and Browser Agents — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch19_02_PricingResult.py
"""
import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout
import anthropic

client = anthropic.Anthropic()

@dataclass
class PricingResult:
    url: str
    plans: list[dict] = field(default_factory=list)
    extracted_at: float = field(default_factory=time.time)
    error: Optional[str] = None
    retries: int = 0

async def get_page_content(page: Page, url: str, max_retries: int = 3) -> tuple[str, str]:
    """
    Navigate to a URL and return (text_content, page_title).
    Retries on timeout, raises on persistent failure.
    """
    for attempt in range(max_retries):
        try:
            await page.goto(url, wait_until="networkidle", timeout=30_000)
            # Wait for any lazy-loaded content
            await page.wait_for_timeout(2000)

            # Extract visible text, preserving some structure
            content = await page.evaluate("""
                () => {
                    // Remove script and style tags before extracting text
                    const clone = document.cloneNode(true);
                    clone.querySelectorAll('script, style, noscript').forEach(el => el.remove());
                    return clone.body ? clone.body.innerText : document.body.innerText;
                }
            """)
            title = await page.title()
            return content, title

        except PlaywrightTimeout:
            if attempt == max_retries - 1:
                raise
            wait_seconds = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            await asyncio.sleep(wait_seconds)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1)

    raise RuntimeError(f"Failed to load {url} after {max_retries} attempts")

def extract_pricing_with_llm(page_text: str, page_title: str, url: str) -> list[dict]:
    """
    Use Claude to extract structured pricing information from page text.
    Returns a list of plan dicts with name, price, billing_period, features.
    """
    prompt = f"""You are extracting pricing information from a competitor's pricing page.

Page URL: {url}
Page Title: {page_title}

Page content (truncated to 8000 chars):
{page_text[:8000]}

Extract all pricing plans mentioned on this page. For each plan, provide:
- name: The plan name (e.g., "Starter", "Pro", "Enterprise")
- price: The numeric price as a string (e.g., "29", "0", "custom")
- currency: Currency symbol or code (e.g., "USD", "$")
- billing_period: "monthly", "annual", "one-time", or "custom"
- features: A list of up to 8 key features mentioned for this plan

If pricing is not clearly stated (e.g., "Contact us"), use "custom" for price.
If you cannot find pricing information, return an empty list.

Respond with a JSON object containing a single key "plans" with a list of plan objects.
Respond ONLY with valid JSON, no explanation."""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text.strip()

    # Strip markdown code fences if present
    if response_text.startswith("```"):
        response_text = re.sub(r"^```[\w]*\n", "", response_text)
        response_text = re.sub(r"\n```$", "", response_text)

    try:
        data = json.loads(response_text)
        return data.get("plans", [])
    except json.JSONDecodeError:
        return []


if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = PricingResult(url='https://example.com/pricing')
        print(result)
