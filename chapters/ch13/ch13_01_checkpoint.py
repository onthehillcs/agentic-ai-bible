"""
Chapter 13 — Long-Running and Async Agents — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch13_01_Checkpoint.py
"""
# Tested with Python 3.11, openai==1.14.0, sqlite3 (stdlib)
# Checkpoint manager for long-running agents

import sqlite3
import json
import hashlib
import time
from dataclasses import dataclass, asdict
from typing import Any, Optional
from pathlib import Path


@dataclass
class Checkpoint:
    """Represents a single agent execution checkpoint."""
    run_id: str
    stage_name: str
    stage_index: int
    inputs: dict
    outputs: dict
    token_count: int
    cost_usd: float
    wall_time_start: float
    wall_time_end: Optional[float]
    status: str  # 'in_progress', 'complete', 'failed'


class CheckpointManager:
    """Durable checkpoint store backed by SQLite.
    
    For production use, swap the SQLite backend for PostgreSQL or DynamoDB
    by reimplementing save() and load() while keeping the same interface.
    """
    
    def __init__(self, db_path: str = "/tmp/agent_checkpoints.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    run_id TEXT NOT NULL,
                    stage_name TEXT NOT NULL,
                    stage_index INTEGER NOT NULL,
                    data TEXT NOT NULL,
                    saved_at REAL NOT NULL,
                    PRIMARY KEY (run_id, stage_name)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS run_metadata (
                    run_id TEXT PRIMARY KEY,
                    created_at REAL,
                    last_heartbeat REAL,
                    total_cost_usd REAL,
                    status TEXT
                )
            """)
            conn.commit()
    
    def save(self, checkpoint: Checkpoint) -> None:
        """Atomically persist a checkpoint."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO checkpoints
                    (run_id, stage_name, stage_index, data, saved_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    checkpoint.run_id,
                    checkpoint.stage_name,
                    checkpoint.stage_index,
                    json.dumps(asdict(checkpoint)),
                    time.time()
                )
            )
            # Update run metadata atomically in the same transaction
            conn.execute(
                """
                INSERT OR REPLACE INTO run_metadata
                    (run_id, created_at, last_heartbeat, total_cost_usd, status)
                VALUES (
                    ?,
                    COALESCE((SELECT created_at FROM run_metadata WHERE run_id=?), ?),
                    ?,
                    ?,
                    ?
                )
                """,
                (
                    checkpoint.run_id,
                    checkpoint.run_id,
                    time.time(),
                    time.time(),
                    checkpoint.cost_usd,
                    checkpoint.status
                )
            )
            conn.commit()
    
    def load_latest(self, run_id: str) -> Optional[Checkpoint]:
        """Load the most recently completed checkpoint for a run."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT data FROM checkpoints
                WHERE run_id = ? AND json_extract(data, '$.status') = 'complete'
                ORDER BY stage_index DESC
                LIMIT 1
                """,
                (run_id,)
            ).fetchone()
        if row is None:
            return None
        data = json.loads(row[0])
        return Checkpoint(**data)
    
    def load_all(self, run_id: str) -> list[Checkpoint]:
        """Load all checkpoints for a run in stage order."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT data FROM checkpoints WHERE run_id = ? ORDER BY stage_index",
                (run_id,)
            ).fetchall()
        return [Checkpoint(**json.loads(r[0])) for r in rows]
    
    def heartbeat(self, run_id: str) -> None:
        """Record that the agent is still alive. Called every N seconds."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE run_metadata SET last_heartbeat = ? WHERE run_id = ?",
                (time.time(), run_id)
            )
            conn.commit()
    
    def is_stale(self, run_id: str, timeout_seconds: float = 300.0) -> bool:
        """Return True if the agent hasn't sent a heartbeat recently enough."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT last_heartbeat FROM run_metadata WHERE run_id = ?",
                (run_id,)
            ).fetchone()
        if row is None:
            return True
        return (time.time() - row[0]) > timeout_seconds

if __name__ == '__main__':
    # Example instantiation
    example = Checkpoint(run_id='abc-123', stage_name='example', stage_index=1, inputs={}, outputs={}, token_count='example-key', cost_usd=1.0, wall_time_start=1.0, wall_time_end=1.0, status='example')
    print(example)
