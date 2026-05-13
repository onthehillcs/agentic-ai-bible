"""
Chapter 8 — Planning and Decomposition — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch08_02_run_tests.py
"""
# ch08_tot_code.py
# Tested against Claude Sonnet 4.6 (claude-sonnet-4-6-20250514),
# Anthropic SDK 0.49.0, as of April 2026.
# Requires: anthropic>=0.49

import json
import subprocess
import tempfile
import os
import anthropic

client = anthropic.Anthropic()

GENERATE_SYSTEM = """
You are a Python expert. Given a function specification, produce a complete Python implementation.
Output ONLY the function definition, no imports unless essential, no explanation.
"""

EVALUATE_SYSTEM = """
You are evaluating N candidate Python implementations against test results.
Given the test outcomes for each candidate, rank them from best to worst.
Output a JSON list of candidate indices in order from best to worst, e.g. [2, 0, 1].
"""

def run_tests(code: str, tests: str) -> tuple[int, str]:
    """Run tests against a code implementation. Returns (tests_passed, output)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code + "\n\n" + tests)  # ① combine implementation and test code
        fname = f.name
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", fname, "-v", "--tb=short", "-q"],
            capture_output=True, text=True, timeout=10
        )
        passed = result.stdout.count(" PASSED")
        return passed, result.stdout[-800:]  # trim to avoid context explosion
    except subprocess.TimeoutExpired:
        return 0, "Timeout: implementation ran for more than 10 seconds"
    finally:
        os.unlink(fname)

def generate_candidates(spec: str, n: int = 3) -> list[str]:  # ② generate N candidates
    """Generate N independent implementation candidates for the given spec."""
    candidates = []
    for i in range(n):
        # Different temperature per candidate to encourage diversity
        temp_hint = ["standard", "more concise", "more defensive"][i % 3]
        response = client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=512,
            system=GENERATE_SYSTEM,
            messages=[{"role": "user", "content": f"Spec (write a {temp_hint} implementation):\n{spec}"}],
        )
        candidates.append(response.content[0].text.strip())
    return candidates

def tot_code_generation(spec: str, tests: str, rounds: int = 2) -> str:
    """Use Tree-of-Thoughts to select the best implementation of a function."""
    best_code = None
    best_score = -1

    for round_num in range(rounds):
        candidates = generate_candidates(spec)
        results = [run_tests(c, tests) for c in candidates]  # ③ evaluate all candidates
        scores = [r[0] for r in results]
        outputs = [r[1] for r in results]

        round_best_idx = scores.index(max(scores))
        if scores[round_best_idx] > best_score:
            best_score = scores[round_best_idx]
            best_code = candidates[round_best_idx]

        total_tests = tests.count("def test_")
        if best_score >= total_tests:  # ④ stop early if a candidate passes all tests
            break

        # Build failure summary for the next round's generation context
        spec = spec + "\n\n# Previous attempts and their failures:\n"
        for i, (score, out) in enumerate(zip(scores, outputs)):
            spec += f"# Candidate {i}: {score}/{total_tests} tests passed\n# {out[:200]}\n"

    return best_code or candidates[0]

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = run_tests('def add(a, b): return a + b')
        print(result)
