"""
Chapter 17 — Cost, Latency, and Performance — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch17_01_CacheStats.py
"""
# Tested with Python 3.11, redis==5.0.1
# Agent result cache with TTL and semantic deduplication

import hashlib
import json
import time
from typing import Any, Callable, Optional
from dataclasses import dataclass

try:
    import redis
    _redis_client = redis.Redis(host='localhost', port=6379, db=2, decode_responses=True)
except Exception:
    _redis_client = None  # Fall back to in-memory dict

_memory_cache: dict[str, tuple[Any, float]] = {}  # Fallback for development


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


_stats = CacheStats()


def cache_key(*args, **kwargs) -> str:
    """Generate a stable cache key from arbitrary inputs."""
    payload = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def cached(
    ttl_seconds: int = 3600,
    key_prefix: str = "",
):
    """Decorator that caches function results with a TTL.
    
    Usage:
        @cached(ttl_seconds=86400, key_prefix='sec_filing')
        def summarize_filing(filing_id: str, filing_text: str) -> str:
            ...
    """
    def decorator(fn: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            key = f"{key_prefix}:{cache_key(*args, **kwargs)}"
            
            # Try to load from cache
            cached_value = _load(key)
            if cached_value is not None:
                _stats.hits += 1
                return cached_value
            
            _stats.misses += 1
            result = fn(*args, **kwargs)
            _store(key, result, ttl_seconds)
            return result
        
        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        return wrapper
    
    return decorator


def _load(key: str) -> Optional[Any]:
    """Load a value from cache, returning None on miss or expiry."""
    if _redis_client:
        try:
            val = _redis_client.get(key)
            return json.loads(val) if val else None
        except Exception:
            pass
    
    # Fallback to in-memory
    if key in _memory_cache:
        value, expiry = _memory_cache[key]
        if time.time() < expiry:
            return value
        del _memory_cache[key]
    return None


def _store(key: str, value: Any, ttl: int) -> None:
    """Store a value in cache with TTL."""
    if _redis_client:
        try:
            _redis_client.setex(key, ttl, json.dumps(value))
            return
        except Exception:
            pass
    
    # Fallback to in-memory
    _memory_cache[key] = (value, time.time() + ttl)


# Apply to expensive pipeline steps
@cached(ttl_seconds=86400 * 7, key_prefix='filing_summary')  # Cache for 7 days
def summarize_sec_filing(filing_id: str, filing_text: str, focus_areas: list) -> str:
    """Summarize an SEC filing. Cached by filing_id + focus areas."""
    # Actual LLM call here
    return f"Summary for {filing_id}"  # Placeholder


@cached(ttl_seconds=3600 * 4, key_prefix='news_synthesis')  # Cache for 4 hours
def synthesize_news(company: str, date_range: str, headlines: list) -> str:
    """Synthesize news for a company. Cached by company + date range + content hash."""
    return f"News synthesis for {company}"  # Placeholder

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = cache_key()
        print(result)
