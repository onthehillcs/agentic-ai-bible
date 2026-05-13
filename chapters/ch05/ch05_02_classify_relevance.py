"""
Chapter 5 — LLMs as Reasoning Engines — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch05_02_classify_relevance.py
"""
# requires ANTHROPIC_API_KEY
import anthropic
import json

client = anthropic.Anthropic()

HAIKU  = "claude-haiku-4-5"   # fast, cheap — classification and relevance checks
SONNET = "claude-sonnet-4-5"  # capable — synthesis and multi-step reasoning

def classify_relevance(snippet: str, question: str) -> bool:
    # Use Haiku to quickly decide if a search snippet is worth reading.
    response = client.messages.create(
        model=HAIKU,
        max_tokens=16,
        system="Reply with only YES or NO.",
        messages=[
            {"role": "user",
             "content": f"Is this snippet relevant to the question?\nQuestion: {question}\nSnippet: {snippet}"}
        ],
    )
    return response.content[0].text.strip().upper() == "YES"

def synthesize(question: str, evidence: list) -> str:
    # Use Sonnet to reason over filtered evidence and produce a final answer.
    joined = "\n\n".join(f"- {e}" for e in evidence)
    response = client.messages.create(
        model=SONNET,
        max_tokens=2048,
        messages=[
            {"role": "user",
             "content": f"Answer this question using only the evidence below.\nQuestion: {question}\n\nEvidence:\n{joined}"}
        ],
    )
    return response.content[0].text

def run_tiered_research(question: str, raw_snippets: list) -> str:
    # Haiku filters; Sonnet synthesizes only what passes the filter
    relevant = [s for s in raw_snippets if classify_relevance(s, question)]
    if not relevant:
        return "No relevant evidence found."
    return synthesize(question, relevant)

if __name__ == "__main__":
    snippets = [
        "The Fed raised rates five times in 2023, putting pressure on bank balance sheets.",
        "A recipe for banana bread trending on social media.",
        "Silicon Valley Bank collapsed in March 2023 after a bank run triggered by bond losses.",
    ]
    print(run_tiered_research("What caused the 2023 banking crisis?", snippets))
