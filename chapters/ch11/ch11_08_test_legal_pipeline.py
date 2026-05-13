"""
Chapter 11 — Multi-Agent Systems — Example 8
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch11_08__11_8_1_test_suite_for_the_production.py
"""

_TEXT = """
The fault tolerance policy is explicit: extraction and writing are required stages (failure aborts the pipeline), while research is optional (failure produces a memo without precedent analysis, with a logged error). This matches a reasonable business priority: a memo without precedents is better than no memo, but a memo without extracted facts or written prose is not useful. The policy is encoded in the code, not in the model's judgment.

The metrics collected by `StageMetrics` are the minimum I consider necessary for any production pipeline: per-stage latency, attempt count, and token usage. These three numbers, logged for every run, let the team answer the questions that matter most in production: which stage is slowest, which stage is most likely to retry, and which stage is consuming the most of the API budget.

### 11.8.1 Test suite for the production pipeline

The following tests cover the happy path, the optional-stage degradation path, and the required-stage failure path. They use a mock worker function so that the tests run without live API calls.
"""

if __name__ == '__main__':
    print(_TEXT)
