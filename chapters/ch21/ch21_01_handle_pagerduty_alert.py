"""
Chapter 21 — Case Studies — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch21_01_handle_pagerduty_alert.py
"""
import json
import httpx
from typing import Optional
import anthropic

client = anthropic.Anthropic()

RUNBOOK_TOOLS = [
    {
        "name": "search_runbooks",
        "description": "Search the internal runbook documentation for the given alert type or service name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "service": {"type": "string", "description": "Optional: specific service name to filter by"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_recent_incidents",
        "description": "Retrieve recent incidents for a given alert name or service from the incident management system.",
        "input_schema": {
            "type": "object",
            "properties": {
                "alert_name": {"type": "string"},
                "limit": {"type": "integer", "default": 3}
            },
            "required": ["alert_name"]
        }
    },
    {
        "name": "get_dashboard_links",
        "description": "Get relevant monitoring dashboard URLs for a given service.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string"}
            },
            "required": ["service"]
        }
    }
]

def handle_pagerduty_alert(alert_payload: dict, runbook_base_url: str) -> dict:
    """
    Process a PagerDuty alert and return a structured incident summary
    with runbook steps, dashboard links, and recent incident context.
    """
    alert_name = alert_payload.get("alert_name", "Unknown Alert")
    service = alert_payload.get("service", {}).get("name", "Unknown Service")
    severity = alert_payload.get("severity", "unknown")
    details = alert_payload.get("body", {}).get("details", {})

    system_prompt = """You are an incident response assistant for a platform engineering team.
When given a PagerDuty alert, your job is to:
1. Search for the relevant runbook for this type of alert
2. Get recent incident history for context
3. Get dashboard links for the affected service
4. Assemble a clear, actionable incident summary

Format your final response as a JSON object with keys:
- summary: one-sentence description of what is alerting and why it matters
- runbook_steps: list of ordered action items from the runbook, adapted to this specific alert
- dashboard_links: list of {name, url} objects
- recent_incidents: list of {date, duration_minutes, resolution_summary} for recent similar incidents
- escalation_note: any special context about when to escalate beyond standard runbook

Respond ONLY with the JSON object, no explanation."""

    user_message = f"""PagerDuty Alert:
Alert Name: {alert_name}
Service: {service}
Severity: {severity}
Details: {json.dumps(details, indent=2)}

Please assemble the incident response context."""

    messages = [{"role": "user", "content": user_message}]

    # Stub implementations for tool execution (replace with real API calls)
    def execute_runbook_tool(name: str, args: dict) -> str:
        if name == "search_runbooks":
            # In production: query Confluence or your docs system
            return json.dumps({"runbook_url": f"{runbook_base_url}/{service.lower()}",
                              "steps": ["Check service health endpoint", "Review recent deployments",
                                       "Check database connection pool", "Escalate if not resolved in 15 min"]})
        elif name == "get_recent_incidents":
            # In production: query your incident management system
            return json.dumps([{"date": "2025-10-15", "duration_minutes": 23,
                                "resolution_summary": "Database connection pool exhaustion, increased pool size"}])
        elif name == "get_dashboard_links":
            return json.dumps([{"name": f"{service} Overview",
                               "url": f"https://grafana.internal/d/{service.lower()}"}])
        return "{}"

    for _ in range(10):  # Max tool call iterations
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            system=system_prompt,
            tools=RUNBOOK_TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    try:
                        return json.loads(block.text)
                    except json.JSONDecodeError:
                        return {"error": "Failed to parse agent response", "raw": block.text}
            break

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_runbook_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        messages.append({"role": "user", "content": tool_results})

    return {"error": "Incident summary generation failed"}

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        alert = {'id': 'INC001', 'severity': 'high', 'summary': 'DB CPU spike', 'service': 'api'}
        result = handle_pagerduty_alert(alert)
        print(result)
