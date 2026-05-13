"""
Chapter 10 — Single-Agent Patterns — Example 3
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch10_03_OnboardingStep.py
"""
# ch10_step_machine.py (fragment)
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class OnboardingStep(str, Enum):
    COLLECT_NAME = "collect_name"
    COLLECT_EMAIL = "collect_email"
    COLLECT_COMPANY = "collect_company"
    COLLECT_USE_CASE = "collect_use_case"
    CREATE_ACCOUNT = "create_account"
    COMPLETE = "complete"

@dataclass
class OnboardingState:
    current_step: OnboardingStep = OnboardingStep.COLLECT_NAME
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    use_case: Optional[str] = None
    attempts: dict = field(default_factory=dict)  # step -> attempt count

    def advance(self):
        steps = list(OnboardingStep)
        idx = steps.index(self.current_step)
        if idx + 1 < len(steps):
            self.current_step = steps[idx + 1]

    def is_complete(self) -> bool:
        return self.current_step == OnboardingStep.COMPLETE

def get_step_prompt(state: OnboardingState) -> str:
    """Generate a step-specific system prompt based on current state."""
    collected = []
    if state.name: collected.append(f"Name: {state.name}")
    if state.email: collected.append(f"Email: {state.email}")
    if state.company: collected.append(f"Company: {state.company}")
    if state.use_case: collected.append(f"Use case: {state.use_case}")

    step_instructions = {
        OnboardingStep.COLLECT_NAME: "Ask for the user's full name. Extract it if already provided.",
        OnboardingStep.COLLECT_EMAIL: "Ask for the user's work email address. Extract it if already provided.",
        OnboardingStep.COLLECT_COMPANY: "Ask for the user's company name. Extract it if already provided.",
        OnboardingStep.COLLECT_USE_CASE: "Ask how they plan to use the product. Extract it if already provided.",
        OnboardingStep.CREATE_ACCOUNT: "Confirm all collected information and proceed to create the account.",
    }

    context = "\n".join(collected) if collected else "No information collected yet."
    instruction = step_instructions.get(state.current_step, "Continue onboarding.")
    return f"You are an onboarding assistant. Current step: {state.current_step.value}.\nCollected so far:\n{context}\nInstruction: {instruction}"

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = get_step_prompt(None)
        print(result)
