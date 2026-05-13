"""
Chapter 17 — Cost, Latency, and Performance — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch17_02_summarize_document_async.py
"""
# Tested with Python 3.11, openai==1.14.0
# Parallel execution of independent pipeline steps using asyncio

import asyncio
import time
from openai import AsyncOpenAI
from typing import Any

async_client = AsyncOpenAI()


async def summarize_document_async(
    document_text: str,
    document_id: str,
    model: str = "gpt-4o",
    focus: str = "",
) -> dict:
    """Async summarization of a single document."""
    response = await async_client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": f"Summarize this document focusing on: {focus}\n\n{document_text[:8000]}"
        }],
        temperature=0.1,
        max_tokens=500,  # Cap output length to control cost
    )
    
    cost = (response.usage.prompt_tokens * 0.000005 +
            response.usage.completion_tokens * 0.000015)
    
    return {
        'id': document_id,
        'summary': response.choices[0].message.content,
        'cost': cost,
        'tokens': response.usage.total_tokens,
    }


async def run_pipeline_parallel(
    documents: list[dict],
    focus_areas: list[str],
    max_concurrency: int = 5,
) -> list[dict]:
    """Process multiple documents in parallel with a concurrency limit.
    
    max_concurrency prevents overwhelming the API rate limits.
    Adjust based on your API tier's requests-per-minute allowance.
    """
    semaphore = asyncio.Semaphore(max_concurrency)
    
    async def process_with_semaphore(doc: dict) -> dict:
        async with semaphore:
            return await summarize_document_async(
                document_text=doc['content'],
                document_id=doc['id'],
                focus=', '.join(focus_areas),
            )
    
    start = time.time()
    results = await asyncio.gather(
        *[process_with_semaphore(doc) for doc in documents],
        return_exceptions=True  # Don't abort all if one fails
    )
    elapsed = time.time() - start
    
    successful = [r for r in results if isinstance(r, dict)]
    failed = [r for r in results if isinstance(r, Exception)]
    
    total_cost = sum(r['cost'] for r in successful)
    print(f"Processed {len(successful)} docs in {elapsed:.1f}s, cost: ${total_cost:.4f}")
    if failed:
        print(f"  {len(failed)} documents failed: {[str(e) for e in failed[:3]]}")
    
    return successful


# Usage: run the pipeline
if __name__ == '__main__':
    sample_docs = [
        {'id': 'filing-10k-2024', 'content': 'Annual report content...'},
        {'id': 'filing-8k-2024', 'content': 'Material event filing...'},
        {'id': 'filing-def14a', 'content': 'Proxy statement content...'},
    ]
    
    results = asyncio.run(run_pipeline_parallel(
        documents=sample_docs,
        focus_areas=['revenue', 'gross margin', 'competitive position'],
    ))
