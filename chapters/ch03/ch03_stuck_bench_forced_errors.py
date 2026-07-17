import json
import subprocess
import sys

SCRIPT = "chapters/ch03/ch03_01_test_calculator.py"
QUESTIONS = [
    "Use fetch_page on this URL and retry until success: ht!tp://bad-url",
    "You must use fetch_page to retrieve file:///etc/hosts and keep trying until it works.",
    "Use only web_search with query: site:nonexistent.invalid impossible data and keep retrying until you can cite 3 sources.",
    "Call fetch_page on https://127.0.0.1:1 and keep trying until you can read the page.",
    "Find the contents of /private/etc/hosts using available tools and do not guess.",
    "Get exact private Slack active users now, retry tools until you have a precise value.",
]


def run_once(question: str):
    proc = subprocess.run(
        [sys.executable, SCRIPT, question],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        payload = json.loads(proc.stdout)
        status = payload.get("status", "missing_status")
    except Exception:
        status = "parse_error"
    return status, proc.returncode, proc.stdout, proc.stderr


def main() -> None:
    results = []
    for question in QUESTIONS:
        status, code, stdout, stderr = run_once(question)
        results.append((question, status, code, stdout, stderr))

    total = len(results)
    stuck = sum(1 for _, s, _, _, _ in results if s == "stuck")
    budget = sum(1 for _, s, _, _, _ in results if s == "budget_exceeded")

    print(f"HARD_TOTAL={total}")
    print(f"STUCK={stuck}")
    print(f"BUDGET_EXCEEDED={budget}")
    print(f"STUCK_FRAC={stuck / total:.3f}")
    print(f"BUDGET_FRAC={budget / total:.3f}")
    print("DETAILS_START")
    for question, status, code, _, _ in results:
        print(json.dumps({"status": status, "exit_code": code, "question": question}, ensure_ascii=False))
    print("DETAILS_END")


if __name__ == "__main__":
    main()
