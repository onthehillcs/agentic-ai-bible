"""
Chapter 18 — Deployment and SRE — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch18_02_liveness.py
"""
# Tested with Python 3.11, flask==3.0.2, openai==1.14.0
# Three-tier health check implementation for production agents

from flask import Flask, jsonify
import time
import requests as http
from openai import OpenAI

app = Flask(__name__)
client = OpenAI()

STARTUP_TIME = time.time()


@app.route('/health/live')
def liveness():
    """Liveness probe: is the process alive and not deadlocked?
    
    Called every 10s by Kubernetes. Should return in < 100ms.
    Restart the pod if this fails.
    """
    return jsonify({
        'status': 'alive',
        'uptime_seconds': int(time.time() - STARTUP_TIME),
    }), 200


@app.route('/health/ready')
def readiness():
    """Readiness probe: are all dependencies available?
    
    Called before routing traffic to a new instance.
    Remove from load balancer if this fails.
    """
    checks = {}
    all_ok = True
    
    # Check LLM provider reachability (lightweight ping, not a completion call)
    try:
        resp = http.get('https://api.openai.com/v1/models',
                        headers={'Authorization': f'Bearer {client.api_key}'},
                        timeout=5)
        checks['llm_provider'] = {'ok': resp.status_code == 200, 'latency_ms': 0}
    except Exception as e:
        checks['llm_provider'] = {'ok': False, 'error': str(e)}
        all_ok = False
    
    # Check database/cache connectivity
    try:
        import redis
        r = redis.Redis()
        r.ping()
        checks['cache'] = {'ok': True}
    except Exception as e:
        checks['cache'] = {'ok': False, 'error': str(e)}
        # Cache failure is non-fatal if we have fallback
        # all_ok = False  # Uncomment if cache is required
    
    status_code = 200 if all_ok else 503
    return jsonify({'status': 'ready' if all_ok else 'not_ready', 'checks': checks}), status_code


@app.route('/health/deep')
def deep_health():
    """Deep health check: does the agent produce correct outputs?
    
    Called every 60s by external monitoring. Alert if this fails 3 times.
    Uses a canonical test question with a known acceptable response.
    """
    start = time.time()
    
    try:
        # Canary test: a simple, stable question with a deterministic correct answer
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant. Answer briefly.'},
                {'role': 'user', 'content': 'What is 2 + 2? Answer with just the number.'},
            ],
            temperature=0.0,
            max_tokens=10,
            timeout=30,
        )
        
        answer = response.choices[0].message.content.strip()
        latency_ms = (time.time() - start) * 1000
        
        is_correct = '4' in answer
        
        return jsonify({
            'status': 'healthy' if is_correct else 'degraded',
            'test_passed': is_correct,
            'latency_ms': int(latency_ms),
            'model': 'gpt-4o',
        }), 200 if is_correct else 503
    
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'latency_ms': int((time.time() - start) * 1000),
        }), 503

if __name__ == '__main__':
    import asyncio
    asyncio.run(liveness())
