"""
Chapter 12 — Human-in-the-Loop — Example 5
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch12_05_ReviewRecord.py
"""
# ch12_threshold_calibration.py
# Confidence threshold calibration from historical review data.
# Requires: numpy>=1.26

import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass
class ReviewRecord:
    confidence: float
    agent_decision: str
    human_decision: Optional[str]    # None if autonomous (no human review)
    ground_truth: Optional[str]      # None if outcome not yet known

def compute_band_statistics(
    records: list[ReviewRecord],
    band_width: float = 0.1,
) -> list[dict]:
    """
    Compute accuracy and override rate for each confidence band.
    Returns a list of dicts sorted by confidence band lower bound.
    """
    bands = np.arange(0.0, 1.0, band_width)
    results = []
    for lower in bands:
        upper = lower + band_width
        band_records = [r for r in records if lower <= r.confidence < upper]
        if not band_records:
            continue

        reviewed = [r for r in band_records if r.human_decision is not None]
        autonomous_with_gt = [
            r for r in band_records
            if r.human_decision is None and r.ground_truth is not None
        ]

        override_rate = (
            sum(1 for r in reviewed if r.human_decision != r.agent_decision) / len(reviewed)
            if reviewed else None
        )
        autonomous_accuracy = (
            sum(1 for r in autonomous_with_gt if r.agent_decision == r.ground_truth) / len(autonomous_with_gt)
            if autonomous_with_gt else None
        )

        results.append({
            "band": f"{lower:.1f}-{upper:.1f}",
            "count": len(band_records),
            "reviewed_count": len(reviewed),
            "override_rate": round(override_rate, 3) if override_rate is not None else None,
            "autonomous_accuracy": round(autonomous_accuracy, 3) if autonomous_accuracy is not None else None,
        })
    return results

def recommend_threshold(
    band_stats: list[dict],
    min_accuracy: float = 0.90,
    max_override_rate: float = 0.10,
) -> float:
    """
    Recommend the lowest confidence threshold that satisfies the accuracy
    and override rate requirements. Returns 1.0 if no band satisfies both
    (meaning all decisions should be reviewed).
    """
    for band in sorted(band_stats, key=lambda b: float(b["band"].split("-")[0])):
        lower = float(band["band"].split("-")[0])
        acc = band.get("autonomous_accuracy")
        ovr = band.get("override_rate")
        # A band is safe to automate if accuracy is above the minimum
        # and the override rate (where we have it) is below the maximum.
        acc_ok = acc is None or acc >= min_accuracy
        ovr_ok = ovr is None or ovr <= max_override_rate
        if acc_ok and ovr_ok:
            return lower
    return 1.0  # no band qualifies; review everything

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = compute_band_statistics([], 'abc-123')
        print(result)
