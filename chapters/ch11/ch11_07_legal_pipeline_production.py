"""
Chapter 11 — Multi-Agent Systems — Example 7
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch11_07__11_8_worked_example_supervisor_worker.py
"""

_TEXT = """
Inter-agent message passing is the second concern. Agents communicate by passing messages, and those messages must be typed, versioned, and validated. A message that an extractor agent sends to a researcher agent should have a defined schema that both sides agree on, and the schema should be enforced at the boundary. Untyped free-form messages between agents are a source of bugs that are invisible until a specific combination of inputs produces a malformed message that the receiving agent cannot parse.

Fault tolerance is the third. In a multi-agent system with N agents, the probability that at least one agent fails on any given run is higher than in a single-agent system. The system must define what happens when an agent fails: does the pipeline abort, does it retry the failed agent, does it produce partial results, or does it escalate to a human? Each of these choices has tradeoffs, and the right choice depends on the task's error tolerance and the failure's reversibility. Define the fault tolerance policy before you deploy; discovering it ad hoc in production is painful.

## 11.8 Worked example: supervisor-worker for legal document analysis

The following example extends the supervisor-worker code from section 11.2 with the fault tolerance and shared state management infrastructure that a production deployment requires. I have also added metrics collection, which is the most common missing piece when teams move from prototype pipelines to production ones.
"""

if __name__ == '__main__':
    print(_TEXT)
