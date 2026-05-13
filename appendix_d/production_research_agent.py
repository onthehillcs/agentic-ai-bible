"""
python research_agent.py

# Custom topic
python research_agent.py "Retrieval-augmented generation in production systems"

# Test graceful degradation for web search
FAIL_SEARCH=1 python research_agent.py "Any topic"
```

The agent will emit JSON log records as it runs. You can pipe these into `jq` for readable output during development:

```bash
python research_agent.py 2>&1 | grep -v '^=' | jq .
```

In production, redirect the JSON records to your log aggregator. The `run_id` field in every record makes it possible to retrieve the complete trace for any run from any logging system that supports structured field filtering.
"""

if __name__ == '__main__':
    print('This file contains shell usage examples for the production research agent.')
    print('See the docstring above for run instructions.')
