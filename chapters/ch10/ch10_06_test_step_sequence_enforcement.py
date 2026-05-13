"""
Chapter 10 — Single-Agent Patterns — Example 6
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch10_06_make_user_msg.py
"""
# ch10_test_returns_step_machine.py
# Unit tests for the returns step machine workflow.
# Run with: python -m pytest ch10_test_returns_step_machine.py -v

import pytest
from copy import deepcopy
from ch10_returns_step_machine import (
    ReturnState, ReturnStep, handle_return_request, RETURN_TOOLS_BY_STEP
)


def make_user_msg(text: str) -> dict:
    return {"role": "user", "content": text}


class TestStepSequenceEnforcement:
    """Verify that the step machine cannot skip steps."""

    def test_initial_step_is_verify_order(self):
        state = ReturnState()
        assert state.current_step == ReturnStep.VERIFY_ORDER

    def test_initiate_return_tool_not_available_in_verify_step(self):
        # The tool set for VERIFY_ORDER must not include initiate_return.
        # This is the structural guarantee: not in context means cannot be called.
        tools_at_verify = RETURN_TOOLS_BY_STEP.get(ReturnStep.VERIFY_ORDER, [])
        tool_names = [t["name"] for t in tools_at_verify]
        assert "initiate_return" not in tool_names

    def test_initiate_return_tool_not_available_in_eligibility_step(self):
        tools_at_eligibility = RETURN_TOOLS_BY_STEP.get(ReturnStep.CHECK_ELIGIBILITY, [])
        tool_names = [t["name"] for t in tools_at_eligibility]
        assert "initiate_return" not in tool_names

    def test_confirmation_gate_blocks_without_affirmative(self):
        # Simulate state advanced to CONFIRM_WITH_CUSTOMER.
        state = ReturnState(
            current_step=ReturnStep.CONFIRM_WITH_CUSTOMER,
            order_id="ORD-001",
            order_verified=True,
            eligible=True,
        )
        history = [make_user_msg("I want to return my order")]
        # Non-affirmative last message must not advance state.
        response, new_state = handle_return_request(history, state)
        assert new_state.current_step == ReturnStep.CONFIRM_WITH_CUSTOMER
        assert not new_state.customer_confirmed
        assert "confirm" in response.lower() or "yes" in response.lower()

    def test_confirmation_gate_advances_on_affirmative(self):
        state = ReturnState(
            current_step=ReturnStep.CONFIRM_WITH_CUSTOMER,
            order_id="ORD-001",
            order_verified=True,
            eligible=True,
        )
        history = [
            make_user_msg("I want to return my order"),
            make_user_msg("yes, please proceed"),
        ]
        _, new_state = handle_return_request(history, state)
        # After affirmative, state must advance past CONFIRM_WITH_CUSTOMER.
        assert new_state.current_step != ReturnStep.CONFIRM_WITH_CUSTOMER
        assert new_state.customer_confirmed is True

    def test_complete_state_returns_confirmation_message(self):
        state = ReturnState(
            current_step=ReturnStep.COMPLETE,
            order_id="ORD-001",
            order_verified=True,
            eligible=True,
            customer_confirmed=True,
        )
        history = [make_user_msg("proceed")]
        response, new_state = handle_return_request(history, state)
        assert "confirmation" in response.lower() or "return" in response.lower()
        assert new_state.current_step == ReturnStep.COMPLETE

    def test_tool_availability_matches_step(self):
        # Each step in RETURN_TOOLS_BY_STEP must provide exactly the tools for that step.
        expected = {
            ReturnStep.VERIFY_ORDER: {"get_order_by_id"},
            ReturnStep.CHECK_ELIGIBILITY: {"check_return_eligibility"},
            ReturnStep.INITIATE_RETURN: {"initiate_return"},
        }
        for step, expected_tools in expected.items():
            actual = {t["name"] for t in RETURN_TOOLS_BY_STEP.get(step, [])}
            assert actual == expected_tools, f"Tool mismatch at step {step}"

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = make_user_msg('example')
        print(result)
