"""
Chapter 11 — Multi-Agent Systems — Example 6
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch11_06__11_7_shared_infrastructure_for_multi_a.py
"""

_TEXT = """
The parallelism in `review_file` runs the correctness and style workers concurrently on each file, cutting the per-file review time roughly in half. The domain supervisor then aggregates across files, so the top-level coordinator receives one structured summary per domain rather than one result per file. This means the top-level coordinator's context stays bounded regardless of how many files are in the codebase, as long as each domain summary is concise. That is the central design principle of the hierarchical pattern: each level summarizes upward so that higher levels are never overwhelmed by the raw volume of lower-level output.

## 11.7 Shared infrastructure for multi-agent systems

Regardless of which pattern a multi-agent system uses, several infrastructure concerns appear in every production deployment.

Shared state management is the first. Agents that need to read or update shared state (a plan, a shared context, a list of completed tasks) must do so through a mechanism that handles concurrent access correctly. In Python, a simple shared dict with a threading lock works for in-process multi-agent systems. For distributed systems, Redis with its atomic operations (SETNX, GETSET) is the standard choice. The failure mode to avoid is two agents simultaneously updating the same state object and overwriting each other's changes; this requires explicit locking or an optimistic concurrency mechanism.

The following snippet shows the minimal Redis-backed shared state pattern I use in distributed swarms. The key insight is that writes use `SET ... NX` (set if not exists) so that only the first agent to complete a task can record the result for that task ID. Subsequent writes for the same task ID are silently dropped, which prevents a retried agent from overwriting a completed result with a duplicate.
"""

if __name__ == '__main__':
    print(_TEXT)
