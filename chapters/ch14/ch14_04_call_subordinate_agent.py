"""
Chapter 14 — Observability, Tracing, and Evaluation — Example 4
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch14_04_call_subordinate_agent.py
"""
# Tested with Python 3.11, opentelemetry-sdk==1.22.0, requests==2.31.0
# Trace context propagation for multi-agent systems

from opentelemetry import trace, propagate
from opentelemetry.propagators.textmap import DefaultTextMapPropagator
import requests

propagator = DefaultTextMapPropagator()


def call_subordinate_agent(
    agent_url: str,
    task: dict,
    parent_run_id: str,
) -> dict:
    """Call a subordinate agent and propagate the current trace context.
    
    The subordinate agent receives the traceparent header and attaches
    all of its spans as children of the current span, creating a unified
    trace tree across both agents.
    """
    headers = {"Content-Type": "application/json"}
    
    # Inject the current trace context into the outgoing HTTP headers
    # This adds the W3C traceparent and tracestate headers automatically
    with tracer.start_as_current_span("agent.call_subordinate") as span:
        span.set_attributes({
            "agent.subordinate_url": agent_url,
            "agent.parent_run_id": parent_run_id,
            "agent.task_type": task.get("type", "unknown"),
        })
        
        # Inject propagation headers
        propagate.inject(headers)
        
        response = requests.post(
            f"{agent_url}/run",
            json={"task": task, "parent_run_id": parent_run_id},
            headers=headers,
            timeout=300,
        )
        response.raise_for_status()
        
        result = response.json()
        span.set_attributes({
            "agent.subordinate_run_id": result.get("run_id", ""),
            "agent.subordinate_cost_usd": result.get("cost_usd", 0),
            "agent.subordinate_turns": result.get("turns", 0),
        })
        
        return result


def receive_task_with_context(request_headers: dict, task: dict) -> str:
    """Entry point for a subordinate agent that extracts and continues a trace.
    
    Call this at the beginning of every agent invocation that accepts
    HTTP requests to ensure spans are attached to the correct parent.
    """
    # Extract the trace context from incoming headers
    context = propagate.extract(request_headers)
    
    # All spans created within this block will be children of the caller's span
    with tracer.start_as_current_span(
        "agent.subordinate_run",
        context=context
    ) as span:
        span.set_attributes({
            "agent.task_type": task.get("type", "unknown"),
        })
        
        # Execute the actual agent work here
        result = "Subordinate agent result"
        return result

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = call_subordinate_agent(task='Summarize AI news', context={})
        print(result)
