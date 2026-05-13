"""
Chapter 13 — Long-Running and Async Agents — Example 4
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch13_04_make_idempotency_key.py
"""
# Tested with Python 3.11, hashlib (stdlib)
# Idempotency key generation and gated external write pattern

import hashlib
import json
from typing import Any, Callable

def make_idempotency_key(run_id: str, stage_name: str, sequence: int = 0) -> str:
    """Generate a stable, short idempotency key for an external write.
    
    The key is deterministic given its inputs, which means that retrying
    the same stage always produces the same key and therefore the same
    idempotency behavior at the receiving API.
    """
    payload = f"{run_id}:{stage_name}:{sequence}"
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


class IdempotentWriteTracker:
    """Track which external writes have already been committed for a run.
    
    Backed by the same SQLite checkpoint DB; in production use Redis with
    a TTL matching your maximum run duration.
    """
    
    def __init__(self, db_path: str):
        import sqlite3
        self.db_path = db_path
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS committed_writes (
                    idempotency_key TEXT PRIMARY KEY,
                    committed_at REAL,
                    result_json TEXT
                )
            """)
            conn.commit()
    
    def execute_once(
        self,
        key: str,
        write_fn: Callable[[], Any]
    ) -> tuple[Any, bool]:
        """Execute write_fn exactly once for the given key.
        
        Returns (result, was_new) where was_new=False means the write
        was already committed and the cached result was returned.
        """
        import sqlite3
        import time
        
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT result_json FROM committed_writes WHERE idempotency_key = ?",
                (key,)
            ).fetchone()
            
            if existing:
                return json.loads(existing[0]), False
            
            # Not yet committed: execute and record atomically
            result = write_fn()
            conn.execute(
                "INSERT OR IGNORE INTO committed_writes VALUES (?, ?, ?)",
                (key, time.time(), json.dumps(result))
            )
            conn.commit()
            return result, True


# Usage in a stage that sends notification emails
def notify_stakeholders(run_id: str, stage: str, message: str, tracker: IdempotentWriteTracker):
    key = make_idempotency_key(run_id, stage, sequence=0)
    result, is_new = tracker.execute_once(
        key,
        lambda: send_email(to="team@example.com", body=message)  # type: ignore
    )
    if not is_new:
        print(f"Email already sent for {run_id}/{stage}, skipping duplicate")
    return result

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = make_idempotency_key('abc-123', 'example', 1)
        print(result)
