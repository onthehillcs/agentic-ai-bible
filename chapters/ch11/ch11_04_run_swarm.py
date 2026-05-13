"""
Chapter 11 — Multi-Agent Systems — Example 4
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch11_04_run_swarm.py
"""
# ch11_swarm.py (fragment)
import concurrent.futures
from typing import Callable

def run_swarm(tasks: list[str], worker_fn: Callable[[str], str], max_workers: int = 5) -> list[dict]:
    """Run worker_fn on all tasks in parallel, returning all results."""
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {executor.submit(worker_fn, task): task for task in tasks}
        for future in concurrent.futures.as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result(timeout=60)
                results.append({"task": task, "result": result, "status": "success"})
            except Exception as e:
                results.append({"task": task, "result": None, "status": "failed", "error": str(e)})
    return results

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = run_swarm('Analyze market trends')
        print(result)
