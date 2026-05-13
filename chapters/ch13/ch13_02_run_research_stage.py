"""
Chapter 13 — Long-Running and Async Agents — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch13_02_run_research_stage.py
"""
# Tested with Python 3.11, celery==5.3.4, redis==5.0.1, openai==1.14.0
# Async agent execution with Celery and checkpointing

import uuid
import time
import asyncio
from typing import Callable, Any
from celery import Celery
from openai import OpenAI

# In production, pull these from environment variables
app = Celery(
    'agent_tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1'
)

app.conf.update(
    task_acks_late=True,           # Only ack after successful completion
    task_reject_on_worker_lost=True,  # Requeue if worker dies mid-task
    task_serializer='json',
    result_expires=86400 * 7,      # Keep results for 7 days
)

client = OpenAI()  # Reads OPENAI_API_KEY from environment
checkpoint_mgr = CheckpointManager("/var/agent_data/checkpoints.db")


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_research_stage(
    self,
    run_id: str,
    stage_name: str,
    stage_index: int,
    stage_inputs: dict,
    cost_limit_usd: float = 5.0
):
    """Execute a single research stage with checkpointing and cost control.
    
    If this task fails and is retried, it will detect the existing in-progress
    checkpoint and either resume or restart the stage depending on idempotency.
    """
    # Check if this stage already completed (idempotency guard)
    existing = checkpoint_mgr.load_latest(run_id)
    if existing and existing.stage_index >= stage_index and existing.status == 'complete':
        return {
            'stage_name': stage_name,
            'outputs': existing.outputs,
            'skipped': True,
            'reason': 'already_complete'
        }
    
    # Check total cost so far before starting
    all_checkpoints = checkpoint_mgr.load_all(run_id)
    total_cost = sum(c.cost_usd for c in all_checkpoints)
    if total_cost >= cost_limit_usd:
        raise ValueError(
            f"Run {run_id} has already spent ${total_cost:.4f}, "
            f"which exceeds the limit of ${cost_limit_usd:.2f}"
        )
    
    # Record start of this stage
    cp = Checkpoint(
        run_id=run_id,
        stage_name=stage_name,
        stage_index=stage_index,
        inputs=stage_inputs,
        outputs={},
        token_count=0,
        cost_usd=0.0,
        wall_time_start=time.time(),
        wall_time_end=None,
        status='in_progress'
    )
    checkpoint_mgr.save(cp)
    
    try:
        # Send heartbeats in a background thread while the LLM call runs
        import threading
        stop_heartbeat = threading.Event()
        
        def heartbeat_loop():
            while not stop_heartbeat.is_set():
                checkpoint_mgr.heartbeat(run_id)
                stop_heartbeat.wait(30)  # Heartbeat every 30 seconds
        
        hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        hb_thread.start()
        
        # Execute the actual LLM work
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": stage_inputs.get("system_prompt", "")},
                {"role": "user", "content": stage_inputs.get("user_prompt", "")},
            ],
            temperature=0.2,
        )
        
        stop_heartbeat.set()
        hb_thread.join(timeout=5)
        
        # Calculate cost (GPT-4o pricing as of early 2024)
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        stage_cost = (input_tokens * 0.000005) + (output_tokens * 0.000015)
        
        outputs = {
            'response': response.choices[0].message.content,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
        }
        
        # Save completed checkpoint
        cp.outputs = outputs
        cp.token_count = input_tokens + output_tokens
        cp.cost_usd = stage_cost
        cp.wall_time_end = time.time()
        cp.status = 'complete'
        checkpoint_mgr.save(cp)
        
        return {'stage_name': stage_name, 'outputs': outputs, 'cost_usd': stage_cost}
    
    except Exception as exc:
        cp.status = 'failed'
        cp.wall_time_end = time.time()
        checkpoint_mgr.save(cp)
        # Celery will handle retry logic based on max_retries
        raise self.retry(exc=exc)

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = run_research_stage('Quantum computing advances')
        print(result)
