"""
Chapter 9 — Model Context Protocol — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch09_01_example_01.py
"""
data: {"jsonrpc":"2.0","id":"abc123","result":{"content":[{"type":"text","text":"{\"success\":true}"}]}}

data: {"jsonrpc":"2.0","method":"notifications/tools/list_changed"}

if __name__ == '__main__':
    import asyncio
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        asyncio.run(main())
