"""
End-to-end evals against agents/email_agent.py (the tool-calling agent, not
just individual tools). These are the most expensive tests (multiple LLM
calls + tool calls per email) so keep the golden set focused on behavioral
rules that only show up when the agent decides *which* tools to call:

  - spam/newsletter -> must NOT call response_drafter_tool
  - meeting emails -> must call a meeting tool AND response_drafter_tool
    (per the system prompt: "meeting and response drafting are independent")
  - non-meeting action emails -> must call response_drafter_tool
"""

import time

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import GEval

from graph.nodes.agent import agent_node
from evals.dataset import load_goldens
from evals.metrics import judge_llm 

GOLDENS = load_goldens()

@pytest.fixture(autouse=True)
def _throttle_end_to_end():
    """Only applies within this file — the agent makes several LLM calls per
    golden, so this keeps us under Groq's free-tier TPM limit."""
    yield
    time.sleep(8)
    
def _tool_calls_made(result) -> set[str]:
    """Collect the names of tools the agent actually invoked."""
    names = set()
    for msg in result.get("messages", []):
        name = getattr(msg, "name", None) or (msg.get("name") if isinstance(msg, dict) else None)
        msg_type = getattr(msg, "type", None) or (msg.get("type") if isinstance(msg, dict) else None)
        if msg_type == "tool" and name:
            names.add(name)
    return names


@pytest.mark.parametrize("golden", GOLDENS, ids=[g.additional_metadata["id"] for g in GOLDENS])
def test_agent_tool_selection(golden):
    meta = golden.additional_metadata
    state = {"subject": meta["subject"], "sender": meta["sender"], "body": meta["body"]}

    output = agent_node(state)
    result = output["tool_outputs"]["agent_result"]
    tools_called = _tool_calls_made(result)

    expected = meta["expected"]
    should_draft = expected.get("should_draft_response", True)
    is_meeting = expected.get("meeting_related", False)

    violations = []

    if should_draft and "response_drafter_tool" not in tools_called:
        violations.append("Expected response_drafter_tool to be called but it wasn't.")
    if not should_draft and "response_drafter_tool" in tools_called:
        violations.append("response_drafter_tool was called but should NOT have been (spam/newsletter).")

    if is_meeting:
        meeting_tools = {"detect_meeting_intent", "extract_meeting_details"}
        if not (tools_called & meeting_tools):
            violations.append(f"Expected a meeting tool to be called, got: {tools_called}")

    test_case = LLMTestCase(
        input=golden.input,
        actual_output=f"Tools called: {sorted(tools_called)}",
        expected_output=(
            f"should_draft_response={should_draft}, meeting_related={is_meeting}"
        ),
    )

    # Deterministic rule check (fails loudly with exactly what went wrong)
    assert not violations, "; ".join(violations) + f" | full tool_calls={tools_called}"

    # Also run a GEval pass for a softer read on whether the *set* of tool
    # calls makes sense end to end (useful once you loosen the strict
    # assertion above during early prompt iteration).
    reasonableness = GEval(
        name="Tool Selection Reasonableness",
        criteria=(
            "Given the input email, judge whether the tools called (in actual output) "
            "are a sensible set given what the email requires (expected output describes "
            "whether a draft/meeting-tool should have been used)."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        threshold=0.6,
        model =judge_llm,
    )
    assert_test(test_case, [reasonableness])
