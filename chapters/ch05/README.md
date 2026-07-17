# Chapter 5 — LLMs as Reasoning Engines

Code examples from Chapter 5 — LLMs as Reasoning Engines of *The Agentic AI Bible*.

## Files

- `ch05_01_run_research_agent.py`
- `ch05_02_classify_relevance.py`
- `ch05_03_reinjection.py` -- repeats critical constraints on each user turn.

## Setup

```bash
pip install -r ../../requirements.txt
export ANTHROPIC_API_KEY=your_key_here
export TAVILY_API_KEY=your_key_here
```

## Re-injection example

Run the long-loop research example from the repository root:

```bash
python chapters/ch05/ch05_03_reinjection.py Apple
```

The example prefixes both the initial request and every tool-result user message
with two condensed constraints: use search evidence only, and return exactly
three events as valid JSON.
