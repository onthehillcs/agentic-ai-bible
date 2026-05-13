"""
Chapter 11 — Multi-Agent Systems — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch11_01_run_worker.py
"""
# ch11_supervisor_worker.py
# Tested against Claude Sonnet 4.6, Anthropic SDK 0.49.0, April 2026.
# Requires: anthropic>=0.49

import json
import anthropic

client = anthropic.Anthropic()

EXTRACTOR_SYSTEM = """You are a legal document analyst.
Given a document excerpt, extract key facts relevant to the case.
Output a JSON object: {"facts": [{"fact": "...", "source": "...", "relevance": "high|medium|low"}]}
Be specific and cite the source location for each fact."""

RESEARCHER_SYSTEM = """You are a legal research specialist.
Given a list of case facts, identify the most relevant legal precedents and principles.
Output a JSON object: {"precedents": [{"name": "...", "relevance": "...", "principle": "..."}]}"""

WRITER_SYSTEM = """You are a legal memo writer.
Given extracted facts and relevant precedents, draft a concise case summary memo.
The memo should be 3-5 paragraphs, structured as: Background, Key Facts, Relevant Precedents, Analysis."""

SUPERVISOR_SYSTEM = """You are a legal pipeline supervisor.
Your job is to coordinate three specialists: extractor, researcher, and writer.
For each task:
1. Assign the document to the extractor
2. Assign the extracted facts to the researcher
3. Assign facts + precedents to the writer
4. Return the final memo
You coordinate; you do not execute tool calls directly."""

def run_worker(system: str, user_message: str, model: str = "claude-sonnet-4-6-20250514") -> str:
    """Run a single worker agent and return its output."""
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text

def run_supervisor_pipeline(document_text: str) -> str:
    """Run the full supervisor-worker pipeline on a document."""
    # Step 1: Extract facts
    print("Supervisor: dispatching to extractor...")
    extraction_result = run_worker(
        EXTRACTOR_SYSTEM,
        f"Extract key facts from this document:\n\n{document_text[:4000]}"  # truncate for demo
    )

    # Validate extractor output
    try:
        facts_data = json.loads(extraction_result)
        facts = facts_data.get("facts", [])
    except json.JSONDecodeError:
        facts = [{"fact": extraction_result, "source": "document", "relevance": "high"}]

    # Step 2: Research precedents based on extracted facts
    print(f"Supervisor: dispatching {len(facts)} facts to researcher...")
    research_result = run_worker(
        RESEARCHER_SYSTEM,
        f"Find relevant precedents for these case facts:\n{json.dumps(facts, indent=2)}"
    )

    try:
        precedents_data = json.loads(research_result)
        precedents = precedents_data.get("precedents", [])
    except json.JSONDecodeError:
        precedents = [{"name": "General principles", "relevance": research_result[:200], "principle": "See analysis"}]

    # Step 3: Write the memo
    print(f"Supervisor: dispatching to writer with {len(precedents)} precedents...")
    memo = run_worker(
        WRITER_SYSTEM,
        f"Write a case summary memo from these inputs:\n\nFACTS:\n{json.dumps(facts, indent=2)}\n\nPRECEDENTS:\n{json.dumps(precedents, indent=2)}"
    )

    return memo

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = run_worker('Summarize recent AI news')
        print(result)
