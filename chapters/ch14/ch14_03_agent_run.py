"""
Chapter 14 — Observability, Tracing, and Evaluation — Example 3
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch14_03_AgentRun.py
"""
# Tested with Python 3.11, opentelemetry-sdk==1.22.0, openai==1.14.0
# Complete observability pipeline: tracing + structured logging + LLM-as-judge eval

import json
import time
import uuid
import logging
from typing import Any
from opentelemetry import trace
from openai import OpenAI

# Assume tracer is configured as in the earlier example
# In this example we use a no-op tracer for portability
trace.set_tracer_provider(trace.NoOpTracerProvider())
tracer = trace.get_tracer("eval-demo")
client = OpenAI()

# Structured logger - in production, configure a JSON handler
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("agent.eval")


class AgentRun:
    """Container for a single agent run with full observability."""
    
    def __init__(self, run_id: str = None):
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.events: list[dict] = []
        self.total_cost = 0.0
        self.total_tokens = 0
    
    def log_event(self, event_type: str, **fields):
        """Append a structured event to the run log."""
        event = {
            "event_type": event_type,
            "run_id": self.run_id,
            "timestamp": time.time(),
            **fields
        }
        self.events.append(event)
        log.info(json.dumps(event))
    
    def execute(
        self,
        user_message: str,
        system_prompt: str,
        tools: list[dict] = None,
    ) -> str:
        """Execute the agent with tracing and structured logging."""
        
        with tracer.start_as_current_span("agent.run") as root_span:
            root_span.set_attributes({
                "agent.run_id": self.run_id,
                "agent.user_message_hash": hash_text(user_message),
            })
            
            self.log_event("run_started", user_message_length=len(user_message))
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
            
            # Agentic loop with tracing
            max_turns = 5
            for turn in range(max_turns):
                with tracer.start_as_current_span(f"agent.turn.{turn}") as turn_span:
                    response = traced_llm_call(
                        messages=messages,
                        model="gpt-4o",
                        run_id=self.run_id,
                        stage=f"turn_{turn}",
                        tools=tools or [],
                    )
                    
                    assistant_message = response.choices[0].message
                    cost = (response.usage.prompt_tokens * 0.000005 +
                            response.usage.completion_tokens * 0.000015)
                    
                    self.total_cost += cost
                    self.total_tokens += response.usage.total_tokens
                    
                    self.log_event(
                        "llm_call",
                        turn=turn,
                        model="gpt-4o",
                        input_tokens=response.usage.prompt_tokens,
                        output_tokens=response.usage.completion_tokens,
                        cost_usd=cost,
                        finish_reason=response.choices[0].finish_reason,
                    )
                    
                    # Check if the agent is calling a tool
                    if (assistant_message.tool_calls and
                            response.choices[0].finish_reason == "tool_calls"):
                        
                        messages.append({
                            "role": "assistant",
                            "content": assistant_message.content,
                            "tool_calls": [
                                {"id": tc.id, "type": tc.type,
                                 "function": {"name": tc.function.name,
                                              "arguments": tc.function.arguments}}
                                for tc in assistant_message.tool_calls
                            ]
                        })
                        
                        # Execute each tool call with tracing
                        for tool_call in assistant_message.tool_calls:
                            tool_result = self._execute_tool(
                                tool_call.function.name,
                                json.loads(tool_call.function.arguments)
                            )
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(tool_result),
                            })
                    else:
                        # Agent is done
                        final_response = assistant_message.content or ""
                        
                        root_span.set_attributes({
                            "agent.total_cost_usd": self.total_cost,
                            "agent.total_tokens": self.total_tokens,
                            "agent.turns": turn + 1,
                        })
                        
                        self.log_event(
                            "run_complete",
                            total_cost_usd=self.total_cost,
                            total_tokens=self.total_tokens,
                            turns=turn + 1,
                            response_length=len(final_response),
                        )
                        
                        return final_response
            
            return "I was unable to complete the task within the allowed number of steps."
    
    def _execute_tool(self, tool_name: str, tool_args: dict) -> Any:
        """Execute a named tool with tracing."""
        with tracer.start_as_current_span(f"tool.{tool_name}") as span:
            span.set_attributes({
                "tool.name": tool_name,
                "agent.run_id": self.run_id,
            })
            start = time.time()
            
            # Tool dispatch table - replace with your actual tool implementations
            tools = {
                "search": lambda q: [{"result": f"Search result for: {q}"}],
                "lookup_order": lambda order_id: {"status": "shipped", "eta": "2 days"},
            }
            
            tool_fn = tools.get(tool_name)
            if tool_fn is None:
                self.log_event("tool_error", tool=tool_name, error="unknown_tool")
                return {"error": f"Unknown tool: {tool_name}"}
            
            try:
                result = tool_fn(**tool_args)
                latency_ms = (time.time() - start) * 1000
                span.set_attributes({"tool.success": True, "tool.latency_ms": latency_ms})
                self.log_event("tool_call", tool=tool_name, success=True, latency_ms=latency_ms)
                return result
            except Exception as e:
                span.record_exception(e)
                self.log_event("tool_call", tool=tool_name, success=False, error=str(e))
                return {"error": str(e)}


def run_eval_batch(
    test_cases: list[dict],
    agent_system_prompt: str,
    pass_threshold: float = 3.5,
) -> dict:
    """Run a batch of test cases through the agent and evaluate each output.
    
    Returns a summary report suitable for CI gate decisions.
    """
    results = []
    
    for tc in test_cases:
        run = AgentRun()
        response = run.execute(
            user_message=tc["input"],
            system_prompt=agent_system_prompt,
        )
        
        eval_result = evaluate_response(
            user_request=tc["input"],
            agent_response=response,
            agent_persona=tc.get("persona", "helpful assistant"),
            policies=tc.get("policies", []),
            pass_threshold=pass_threshold,
        )
        
        results.append({
            "test_case_id": tc.get("id", "unknown"),
            "run_id": run.run_id,
            "overall_score": eval_result.overall_score,
            "pass": eval_result.pass_fail,
            "critical_failure": eval_result.critical_failure,
            "cost_usd": run.total_cost,
            "dimension_scores": {
                d.dimension: d.score for d in eval_result.dimension_scores
            }
        })
    
    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    avg_score = sum(r["overall_score"] for r in results) / total if total > 0 else 0
    
    report = {
        "total_cases": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": passed / total if total > 0 else 0,
        "average_score": avg_score,
        "total_eval_cost_usd": sum(r["cost_usd"] for r in results),
        "critical_failures": [
            r for r in results if r["critical_failure"]
        ],
        "results": results,
    }
    
    print(f"Eval complete: {passed}/{total} passed ({100*passed/total:.0f}%)")
    print(f"Average score: {avg_score:.2f}")
    if report["critical_failures"]:
        print(f"CRITICAL FAILURES: {len(report['critical_failures'])} cases violated policies")
    
    return report

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = run_eval_batch([], 'example', 1.0)
        print(result)
