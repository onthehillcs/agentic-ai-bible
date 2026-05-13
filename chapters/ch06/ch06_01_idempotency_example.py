"""
Chapter 6 — Tool Use and Function Calling — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch06_01_example_01.py
"""
{
    "name": "send_email",
    "description": "Send an email to a customer. Required field: recipient email address.",
    "input_schema": {
        "type": "object",
        "properties": {
            "recipient": {
                "type": "string",
                "description": "The customer's email address."
            },
            "subject": {"type": "string"},
            "body": {"type": "string"}
        },
        "required": ["recipient", "subject", "body"]
    }
}

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        import anthropic
        client = anthropic.Anthropic()
        result = run_tool_use_agent(client)
        print(result)
