"""
Chapter 14 — Observability, Tracing, and Evaluation — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch14_02_QualityDimension.py
"""
# Tested with Python 3.11, openai==1.14.0, pydantic==2.5.0
# LLM-as-judge evaluation framework with structured scoring

import json
from enum import IntEnum
from pydantic import BaseModel, Field
from openai import OpenAI
from typing import Optional

client = OpenAI()


class QualityDimension(IntEnum):
    """Scoring dimensions for agent response evaluation."""
    FACTUAL_ACCURACY = 1      # 1-5: Are factual claims correct and well-supported?
    TASK_COMPLETION = 2       # 1-5: Does the response actually answer what was asked?
    TONE_APPROPRIATENESS = 3  # 1-5: Is the tone appropriate for the context and user?
    POLICY_COMPLIANCE = 4     # 1-5: Does the response comply with all stated policies?
    CONCISENESS = 5           # 1-5: Is the response appropriately sized (not too long/short)?


class DimensionScore(BaseModel):
    dimension: str
    score: int = Field(ge=1, le=5)
    justification: str = Field(min_length=20)
    evidence: Optional[str] = None  # Specific quote from response supporting the score


class EvaluationResult(BaseModel):
    overall_score: float = Field(ge=1.0, le=5.0)
    dimension_scores: list[DimensionScore]
    pass_fail: bool  # True if overall_score >= threshold
    critical_failure: Optional[str] = None  # Non-None if a policy was violated
    evaluator_model: str
    evaluation_latency_ms: float


RUBRIC_TEMPLATE = """
You are an expert evaluator of AI agent responses. Evaluate the following agent response
against the provided rubric dimensions.

## Context
User Request: {user_request}
Agent Persona: {agent_persona}
Relevant Policies: {policies}

## Agent Response to Evaluate
{agent_response}

## Scoring Rubric

For each dimension, provide a score from 1 (poor) to 5 (excellent) and a brief justification.

**Factual Accuracy (1-5)**
- 5: All factual claims are accurate and well-supported by verifiable information
- 3: Most claims are accurate with minor errors or omissions
- 1: Contains significant factual errors or unsupported claims

**Task Completion (1-5)**
- 5: Fully addresses all aspects of the user's request
- 3: Addresses the main request but misses secondary aspects
- 1: Fails to address the core request

**Tone Appropriateness (1-5)**
- 5: Tone is warm, professional, and matched to the user's emotional state
- 3: Tone is neutral and professional but not particularly attuned
- 1: Tone is dismissive, rude, or inappropriate for the context

**Policy Compliance (1-5)**
- 5: Fully compliant with all stated policies; no violations
- 3: Minor compliance gaps that do not constitute policy violations
- 1: Clear policy violation (mark critical_failure with specific violation)

**Conciseness (1-5)**
- 5: Response is exactly as long as it needs to be
- 3: Slightly verbose or slightly too brief but serviceable
- 1: Severely over- or under-length for the request

Respond with valid JSON matching the provided schema.
"""


def evaluate_response(
    user_request: str,
    agent_response: str,
    agent_persona: str = "helpful customer support agent",
    policies: list[str] = None,
    pass_threshold: float = 3.5,
    evaluator_model: str = "gpt-4o",
) -> EvaluationResult:
    """Evaluate an agent response using LLM-as-judge.
    
    Uses a structured rubric to produce consistent, comparable scores.
    For calibration, run this against your human-labeled ground truth set
    and adjust the rubric descriptions until judge scores correlate with
    human scores at r > 0.8 across all dimensions.
    """
    import time
    
    if policies is None:
        policies = []
    
    prompt = RUBRIC_TEMPLATE.format(
        user_request=user_request,
        agent_persona=agent_persona,
        policies="\n".join(f"- {p}" for p in policies) if policies else "None specified",
        agent_response=agent_response,
    )
    
    start = time.time()
    response = client.chat.completions.create(
        model=evaluator_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,  # Zero temperature for consistent scoring
        response_format={"type": "json_object"},
    )
    latency_ms = (time.time() - start) * 1000
    
    raw = json.loads(response.choices[0].message.content)
    
    # Parse dimension scores from response
    dimension_scores = [
        DimensionScore(
            dimension=d.get("dimension", ""),
            score=int(d.get("score", 3)),
            justification=d.get("justification", "No justification provided"),
            evidence=d.get("evidence"),
        )
        for d in raw.get("dimension_scores", [])
    ]
    
    overall = raw.get("overall_score") or (
        sum(d.score for d in dimension_scores) / len(dimension_scores)
        if dimension_scores else 3.0
    )
    
    return EvaluationResult(
        overall_score=float(overall),
        dimension_scores=dimension_scores,
        pass_fail=float(overall) >= pass_threshold,
        critical_failure=raw.get("critical_failure"),
        evaluator_model=evaluator_model,
        evaluation_latency_ms=latency_ms,
    )


# Example usage
if __name__ == "__main__":
    result = evaluate_response(
        user_request="I've been waiting 3 weeks for my refund and I'm really frustrated!",
        agent_response="Your refund is being processed. Please allow 5-7 business days.",
        agent_persona="empathetic customer support agent for an e-commerce company",
        policies=[
            "Never promise a specific refund date without checking the system",
            "Acknowledge customer frustration before providing information",
            "Offer to escalate to a supervisor if the customer has waited more than 14 days",
        ],
        pass_threshold=3.5,
    )
    print(f"Overall score: {result.overall_score:.1f}")
    print(f"Pass: {result.pass_fail}")
    for d in result.dimension_scores:
        print(f"  {d.dimension}: {d.score}/5 - {d.justification[:80]}")
