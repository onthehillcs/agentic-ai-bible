"""
Chapter 16 — Security — Example 3
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch16_03__get_secret_cached.py
"""
# Tested with Python 3.11, boto3==1.34.0 (for AWS Secrets Manager)
# Credential injection at tool call level, keeping secrets out of LLM context

import os
import json
import time
from functools import lru_cache
from typing import Any

# For AWS Secrets Manager (replace with your actual secrets manager client)
try:
    import boto3
    _sm_client = boto3.client('secretsmanager', region_name='us-east-1')
except Exception:
    _sm_client = None  # Fall back to environment variables


@lru_cache(maxsize=32)
def _get_secret_cached(secret_name: str, cache_ttl: int = 300) -> str:
    """Retrieve a secret with in-process caching to reduce Secrets Manager calls.
    
    Note: lru_cache never expires. For TTL-based expiry, use a dict with timestamps.
    In production, use a proper TTL cache or Secrets Manager's SDK caching layer.
    """
    if _sm_client:
        response = _sm_client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    else:
        # Development fallback: read from environment
        return os.environ.get(secret_name.upper().replace('-', '_'), '')


def make_authenticated_api_tool(
    api_name: str,
    secret_name: str,
    base_url: str,
) -> callable:
    """Create a tool function that injects credentials at call time.
    
    The LLM never sees the credential. The tool function retrieves it
    from the secrets manager when called and includes it in the HTTP
    request headers.
    """
    import requests
    
    def call_api(endpoint: str, params: dict = None) -> dict:
        """Call the {api_name} API. Returns parsed JSON response."""
        # Credential retrieved here, at call time, not at agent startup
        api_key = _get_secret_cached(secret_name)
        
        response = requests.get(
            f"{base_url}/{endpoint}",
            params=params or {},
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-Agent-Request": "true",  # Tag for audit logging
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    
    call_api.__name__ = f"call_{api_name}"
    call_api.__doc__ = f"""Call the {api_name} API at {base_url}.
    Required: endpoint (string). Optional: params (dict of query parameters)."""
    
    return call_api


# Usage: tools are created with credentials injected at call time
# The agent never sees the secret_name mapped to an actual key value
data_tool = make_authenticated_api_tool(
    api_name="market_data",
    secret_name="market-data-api-key",  # Name in Secrets Manager
    base_url="https://api.marketdata.example.com/v2",
)

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = _get_secret_cached('example-key', 1)
        print(result)
