"""
Chapter 11 — Multi-Agent Systems — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch11_02_Fact.py
"""
# ch11_pipeline_typed.py
# Typed pipeline with inter-stage schema validation.
# Requires: anthropic>=0.49, pydantic>=2.0

import json
from pydantic import BaseModel, ValidationError
from typing import Literal
import anthropic

client = anthropic.Anthropic()

# Inter-stage message schemas
class Fact(BaseModel):
    fact: str
    source: str
    relevance: Literal["high", "medium", "low"]

class ExtractionOutput(BaseModel):
    facts: list[Fact]

class Precedent(BaseModel):
    name: str
    relevance: str
    principle: str

class ResearchOutput(BaseModel):
    precedents: list[Precedent]


def stage_extract(document_text: str) -> ExtractionOutput:
    """Stage 1: Extract structured facts from a document."""
    raw = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=1024,
        system=EXTRACTOR_SYSTEM,
        messages=[{"role": "user", "content": f"Extract facts:\n{document_text[:3000]}"}],
    ).content[0].text
    try:
        return ExtractionOutput.model_validate(json.loads(raw))
    except (ValidationError, json.JSONDecodeError) as exc:
        # Wrap unstructured output rather than propagating invalid data
        return ExtractionOutput(facts=[Fact(fact=raw[:500], source="document", relevance="high")])


def stage_research(extraction: ExtractionOutput) -> ResearchOutput:
    """Stage 2: Research precedents for extracted facts."""
    payload = json.dumps([f.model_dump() for f in extraction.facts], indent=2)
    raw = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=1024,
        system=RESEARCHER_SYSTEM,
        messages=[{"role": "user", "content": f"Find precedents for:\n{payload}"}],
    ).content[0].text
    try:
        return ResearchOutput.model_validate(json.loads(raw))
    except (ValidationError, json.JSONDecodeError):
        return ResearchOutput(precedents=[])


def stage_write(extraction: ExtractionOutput, research: ResearchOutput) -> str:
    """Stage 3: Draft the memo from structured inputs."""
    payload = (
        f"FACTS:\n{json.dumps([f.model_dump() for f in extraction.facts], indent=2)}\n\n"
        f"PRECEDENTS:\n{json.dumps([p.model_dump() for p in research.precedents], indent=2)}"
    )
    return client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=2048,
        system=WRITER_SYSTEM,
        messages=[{"role": "user", "content": payload}],
    ).content[0].text


def run_typed_pipeline(document_text: str) -> str:
    extraction = stage_extract(document_text)
    research = stage_research(extraction)
    return stage_write(extraction, research)

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = stage_extract('example')
        print(result)
