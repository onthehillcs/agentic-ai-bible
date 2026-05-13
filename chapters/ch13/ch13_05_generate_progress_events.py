"""
Chapter 13 — Long-Running and Async Agents — Example 5
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch13_05_generate_progress_events.py
"""
# Tested with Python 3.11, flask==3.0.2
# SSE progress endpoint for long-running agent runs

from flask import Flask, Response, stream_with_context
import json
import time
import sqlite3

app = Flask(__name__)

def generate_progress_events(run_id: str, db_path: str):
    """Generator that yields SSE-formatted progress events for a run.
    
    The client should connect with EventSource and handle reconnection
    using the Last-Event-ID header to request replay from a specific point.
    """
    last_stage_index = -1
    
    while True:
        with sqlite3.connect(db_path) as conn:
            # Fetch any new checkpoints since the last one we reported
            rows = conn.execute(
                """
                SELECT stage_name, stage_index, data FROM checkpoints
                WHERE run_id = ? AND stage_index > ?
                ORDER BY stage_index
                """,
                (run_id, last_stage_index)
            ).fetchall()
            
            meta = conn.execute(
                "SELECT total_cost_usd, status FROM run_metadata WHERE run_id = ?",
                (run_id,)
            ).fetchone()
        
        for stage_name, stage_index, data_json in rows:
            data = json.loads(data_json)
            event_type = 'stage_complete' if data['status'] == 'complete' else 'stage_failed'
            
            event_data = {
                'type': event_type,
                'stage': stage_name,
                'stage_index': stage_index,
                'cost_usd': data.get('cost_usd', 0),
                'summary': data.get('outputs', {}).get('summary', ''),
                'timestamp': time.time()
            }
            
            # SSE format: "id: N\ndata: {...}\n\n"
            yield f"id: {stage_index}\ndata: {json.dumps(event_data)}\n\n"
            last_stage_index = stage_index
        
        # Check if run is complete
        if meta and meta[1] == 'complete':
            yield f"data: {json.dumps({'type': 'run_complete', 'total_cost': meta[0]})}\n\n"
            return
        
        # Send a heartbeat so the client knows the connection is alive
        yield f"data: {json.dumps({'type': 'heartbeat', 'ts': time.time()})}\n\n"
        time.sleep(5)  # Poll every 5 seconds


@app.route('/runs/<run_id>/progress')
def run_progress(run_id: str):
    db_path = "/var/agent_data/checkpoints.db"
    return Response(
        stream_with_context(generate_progress_events(run_id, db_path)),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # Disable nginx buffering
        }
    )

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = generate_progress_events('abc-123', '/tmp/example')
        print(result)
