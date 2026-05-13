"""
Chapter 14 — Observability, Tracing, and Evaluation — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch14_01_setup_tracing.py
"""
# Tested with Python 3.11, opentelemetry-sdk==1.22.0, openai==1.14.0
# OpenTelemetry tracing for agent LLM calls and tool invocations

import hashlib
import time
import functools
from typing import Any, Callable
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from openai import OpenAI

# Initialize the tracer provider once at application startup
def setup_tracing(service_name: str, otlp_endpoint: str = "http://localhost:4317") -> trace.Tracer:
    """Configure OpenTelemetry with an OTLP exporter.
    
    In production, point otlp_endpoint at your collector (Grafana, Jaeger,
    Honeycomb, etc.). For local development, run the OTEL collector in Docker.
    """
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)


tracer = setup_tracing("customer-support-agent")
client = OpenAI()


def hash_text(text: str) -> str:
    """Create a short, safe hash of potentially sensitive text."""
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def traced_llm_call(
    messages: list[dict],
    model: str = "gpt-4o",
    temperature: float = 0.2,
    span_name: str = "llm.completion",
    run_id: str = "",
    stage: str = "",
    **kwargs
) -> Any:
    """Make an LLM API call wrapped in a tracing span with full cost attribution."""
    
    with tracer.start_as_current_span(span_name) as span:
        # Record pre-call attributes
        span.set_attributes({
            "llm.model": model,
            "llm.temperature": temperature,
            "llm.message_count": len(messages),
            "llm.system_prompt_hash": hash_text(
                next((m["content"] for m in messages if m["role"] == "system"), "")
            ),
            "llm.user_prompt_hash": hash_text(
                next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
            ),
            "agent.run_id": run_id,
            "agent.stage": stage,
        })
        
        start_time = time.time()
        first_token_time = None
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                **kwargs
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Cost calculation (model-dependent; update as pricing changes)
            pricing = {
                "gpt-4o": (0.000005, 0.000015),
                "gpt-4o-mini": (0.00000015, 0.0000006),
                "claude-3-5-sonnet-20241022": (0.000003, 0.000015),
            }
            in_price, out_price = pricing.get(model, (0.000005, 0.000015))
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost_usd = (input_tokens * in_price) + (output_tokens * out_price)
            
            # Record post-call attributes
            span.set_attributes({
                "llm.input_tokens": input_tokens,
                "llm.output_tokens": output_tokens,
                "llm.total_tokens": response.usage.total_tokens,
                "llm.cost_usd": cost_usd,
                "llm.latency_ms": latency_ms,
                "llm.finish_reason": response.choices[0].finish_reason,
                "llm.response_hash": hash_text(response.choices[0].message.content or ""),
            })
            
            span.add_event("completion_received", {
                "tokens_per_second": output_tokens / max(latency_ms / 1000, 0.001)
            })
            
            return response
        
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise


def traced_tool_call(
    tool_name: str,
    tool_fn: Callable,
    run_id: str = "",
    **tool_kwargs
) -> Any:
    """Execute a tool call wrapped in a tracing span."""
    
    with tracer.start_as_current_span(f"tool.{tool_name}") as span:
        span.set_attributes({
            "tool.name": tool_name,
            "tool.input_hash": hash_text(str(sorted(tool_kwargs.items()))),
            "agent.run_id": run_id,
        })
        
        start_time = time.time()
        
        try:
            result = tool_fn(**tool_kwargs)
            latency_ms = (time.time() - start_time) * 1000
            
            span.set_attributes({
                "tool.latency_ms": latency_ms,
                "tool.success": True,
                "tool.result_size_bytes": len(str(result).encode()),
            })
            
            return result
        
        except Exception as e:
            span.record_exception(e)
            span.set_attributes({
                "tool.success": False,
                "tool.error": str(e),
            })
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise

if __name__ == '__main__':
    tracer = setup_tracing(service_name='example-service')
    print('Tracer set up:', tracer)
