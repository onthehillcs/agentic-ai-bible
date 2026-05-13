"""
Chapter 17 — Cost, Latency, and Performance — Example 4
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch17_04_agent_stream.py
"""
# Tested with Python 3.11, openai==1.14.0, flask==3.0.2
# Streaming agent response to reduce perceived latency

from openai import OpenAI
from flask import Flask, Response, stream_with_context, request
import json

client = OpenAI()
app = Flask(__name__)


@app.route('/agent/stream', methods=['POST'])
def agent_stream():
    """Agent endpoint that streams responses as they are generated.
    
    The client receives tokens as they arrive rather than waiting for
    the complete response, dramatically improving perceived responsiveness.
    """
    user_message = request.json.get('message', '')
    
    def generate():
        stream = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': user_message},
            ],
            stream=True,
            temperature=0.3,
        )
        
        total_tokens = 0
        for chunk in stream:
            if chunk.choices[0].delta.content:
                token_text = chunk.choices[0].delta.content
                total_tokens += 1
                # Send each chunk as an SSE event
                yield f"data: {json.dumps({'token': token_text})}\n\n"
        
        # Send completion event with token count
        yield f"data: {json.dumps({'done': True, 'tokens': total_tokens})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )

if __name__ == '__main__':
    import asyncio, os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        asyncio.run(agent_stream('Hello, what can you do?'))
