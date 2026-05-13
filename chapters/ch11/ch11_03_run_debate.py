"""
Chapter 11 — Multi-Agent Systems — Example 3
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch11_03_run_debate.py
"""
# ch11_debate.py (fragment)

def run_debate(question: str, n_debaters: int = 2) -> str:
    """Run a two-round debate between n_debaters agents and synthesize a final answer."""
    # Phase 1: Independent proposals
    proposals = []
    for i in range(n_debaters):
        perspective = ["analytical", "skeptical", "contrarian", "empirical"][i % 4]
        proposal = run_worker(
            f"You are a {perspective} analyst. Answer the following question with evidence and reasoning.",
            question
        )
        proposals.append({"debater": i, "perspective": perspective, "proposal": proposal})

    # Phase 2: Cross-critique
    critiques = []
    for i, proposal in enumerate(proposals):
        others = [p for j, p in enumerate(proposals) if j != i]
        critique = run_worker(
            "You are a rigorous critic. Identify factual errors, logical gaps, and missing evidence in the following proposal.",
            f"Proposal to critique:\n{proposal['proposal']}\n\nOther proposals for context:\n{json.dumps([o['proposal'] for o in others])}"
        )
        critiques.append({"debater": i, "critique": critique})

    # Phase 3: Synthesis
    synthesis = run_worker(
        "You are a synthesis expert. Integrate these proposals and critiques into a single well-reasoned answer.",
        f"Question: {question}\n\nProposals:\n{json.dumps(proposals)}\n\nCritiques:\n{json.dumps(critiques)}"
    )
    return synthesis

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = run_debate('Should AI be regulated?')
        print(result)
