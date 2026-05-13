"""
Chapter 18 — Deployment and SRE — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch18_01_CanaryConfig.py
"""
# Tested with Python 3.11, redis==5.0.1
# Canary rollout with automated quality gate for agent deployments

import json
import time
import random
from dataclasses import dataclass
from typing import Optional

try:
    import redis
    _redis = redis.Redis(host='localhost', port=6379, db=3, decode_responses=True)
except Exception:
    _redis = None


@dataclass
class CanaryConfig:
    canary_version: str       # New version being tested
    stable_version: str       # Current production version
    canary_traffic_pct: float  # Fraction of traffic to canary (0.0-1.0)
    min_samples: int          # Minimum evaluations before promotion decision
    quality_gate_delta: float  # Max allowed quality drop (e.g., 0.05 = 5%)
    critical_failure_gate: float  # Max allowed critical failure rate


class CanaryRouter:
    """Routes requests to canary or stable agent versions and tracks quality metrics."""
    
    def __init__(self, config: CanaryConfig):
        self.config = config
        self.key_prefix = f"canary:{config.canary_version}"
    
    def get_version_for_request(self, request_id: str) -> str:
        """Deterministically assign a request to canary or stable.
        
        Uses hashing for consistency: the same request_id always routes
        to the same version, preventing evaluation noise from split decisions.
        """
        hash_val = hash(request_id) % 100
        if hash_val < (self.config.canary_traffic_pct * 100):
            return self.config.canary_version
        return self.config.stable_version
    
    def record_evaluation(
        self,
        version: str,
        quality_score: float,
        is_critical_failure: bool,
    ) -> None:
        """Record an evaluation result for quality gate tracking."""
        if not _redis:
            return
        
        key = f"{self.key_prefix}:{version}:scores"
        _redis.lpush(key, json.dumps({
            'score': quality_score,
            'critical': is_critical_failure,
            'ts': time.time(),
        }))
        _redis.expire(key, 86400)  # Keep for 24 hours
    
    def get_promotion_decision(self) -> dict:
        """Check whether the canary should be promoted or rolled back."""
        if not _redis:
            return {'decision': 'insufficient_data', 'reason': 'No Redis connection'}
        
        canary_key = f"{self.key_prefix}:{self.config.canary_version}:scores"
        stable_key = f"{self.key_prefix}:{self.config.stable_version}:scores"
        
        canary_raw = _redis.lrange(canary_key, 0, -1)
        stable_raw = _redis.lrange(stable_key, 0, -1)
        
        if len(canary_raw) < self.config.min_samples:
            return {
                'decision': 'insufficient_data',
                'canary_samples': len(canary_raw),
                'required': self.config.min_samples,
            }
        
        canary_scores = [json.loads(r) for r in canary_raw]
        stable_scores = [json.loads(r) for r in stable_raw]
        
        canary_avg = sum(s['score'] for s in canary_scores) / len(canary_scores)
        stable_avg = sum(s['score'] for s in stable_scores) / len(stable_scores) if stable_scores else canary_avg
        
        canary_critical_rate = sum(1 for s in canary_scores if s['critical']) / len(canary_scores)
        
        quality_drop = stable_avg - canary_avg
        quality_ok = quality_drop <= self.config.quality_gate_delta
        critical_ok = canary_critical_rate <= self.config.critical_failure_gate
        
        if quality_ok and critical_ok:
            decision = 'promote'
        elif not quality_ok:
            decision = 'rollback'
        else:
            decision = 'rollback'
        
        return {
            'decision': decision,
            'canary_avg_score': canary_avg,
            'stable_avg_score': stable_avg,
            'quality_drop': quality_drop,
            'canary_critical_rate': canary_critical_rate,
            'canary_samples': len(canary_scores),
        }

if __name__ == '__main__':
    # Example instantiation
    example = CanaryConfig(canary_version='example', stable_version='example', canary_traffic_pct=1.0, min_samples=3, quality_gate_delta=1.0, critical_failure_gate=1.0)
    print(example)
