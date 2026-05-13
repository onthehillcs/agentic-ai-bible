"""
Chapter 14 — Observability, Tracing, and Evaluation — Example 5
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch14_05_llm_call_with_span.py
"""
# requires ANTHROPIC_API_KEY
# pip install anthropic opentelemetry-sdk
import anthropic, json, time
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# ── Tracer setup (swap InMemory for OTLP exporter in production) ──
exporter = InMemorySpanExporter()
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("research_agent")

client = anthropic.Anthropic()
SONNET = "claude-sonnet-4-5"
HAIKU  = "claude-haiku-4-5"

def llm_call_with_span(model: str, messages: list, system: str = "") -> str:
    # Wrap every LLM call in an OTel span with cost-relevant attributes.
    with tracer.start_as_current_span("llm_call") as span:
        span.set_attribute("llm.model", model)
        span.set_attribute("llm.message_count", len(messages))
        t0 = time.time()
        kwargs = dict(model=model, max_tokens=2048, messages=messages)
        if system:
            kwargs["system"] = system
        response = client.messages.create(**kwargs)
        span.set_attribute("llm.latency_ms", round((time.time() - t0) * 1000))
        span.set_attribute("llm.input_tokens",  response.usage.input_tokens)
        span.set_attribute("llm.output_tokens", response.usage.output_tokens)
        return response.content[0].text

def evaluate_answer(question: str, answer: str, reference: str = "") -> dict:
    # LLM-as-judge: score on relevance (1-5) and groundedness (1-5).
    ref_line = f"Reference: {reference}\n" if reference else ""
    prompt = (
        f"Score this answer on two dimensions (1=poor, 5=excellent).\n"
        f"Question: {question}\nAnswer: {answer}\n"
        + ref_line +
        'Reply with JSON: {"relevance": N, "groundedness": N, "notes": "..."}'
    )
    with tracer.start_as_current_span("eval.llm_judge"):
        raw = llm_call_with_span(HAIKU, [{"role": "user", "content": prompt}])
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"relevance": 0, "groundedness": 0, "notes": "parse error"}

def run_and_evaluate(question: str, reference: str = "") -> dict:
    with tracer.start_as_current_span("research_agent.run") as root:
        root.set_attribute("agent.question", question)
        answer = llm_call_with_span(
            SONNET,
            [{"role": "user", "content": question}],
            system="You are a research assistant. Answer concisely with cited facts.",
        )
        scores = evaluate_answer(question, answer, reference)
        root.set_attribute("eval.relevance",    scores.get("relevance", 0))
        root.set_attribute("eval.groundedness", scores.get("groundedness", 0))
    return {"answer": answer, "scores": scores}

if __name__ == "__main__":
    result = run_and_evaluate(
        question="What caused the 2023 banking crisis?",
        reference="SVB collapsed due to a bank run following unrealised bond losses.",
    )
    print(json.dumps(result, indent=2))
    spans = exporter.get_finished_spans()
    print(f"\nSpans captured: {len(spans)}")
    for s in spans:
        print(f"  {s.name}: {s.attributes}")
