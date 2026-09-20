import json

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from agents.tools import response_drafter_tool
from evals.dataset import load_goldens_where
from evals.metrics import draft_quality_metric, JsonValidityMetric

# response_drafter_tool is only ever called for emails that should get a
# reply (the agent's system prompt excludes newsletters/spam upstream), so
# we only eval it against goldens where a draft is expected.
DRAFT_GOLDENS = load_goldens_where(lambda e: e.get("should_draft_response") is True)


@pytest.mark.parametrize(
    "golden", DRAFT_GOLDENS, ids=[g.additional_metadata["id"] for g in DRAFT_GOLDENS]
)
def test_draft_json_shape(golden):
    meta = golden.additional_metadata
    email_content = f"Subject: {meta['subject']}\n\n{meta['body']}"

    raw = response_drafter_tool.invoke({"email_content": email_content})

    test_case = LLMTestCase(input=golden.input, actual_output=json.dumps(raw))
    assert_test(test_case, [JsonValidityMetric(required_keys=["draft_response"])])


@pytest.mark.parametrize(
    "golden", DRAFT_GOLDENS, ids=[g.additional_metadata["id"] for g in DRAFT_GOLDENS]
)
def test_draft_quality(golden):
    meta = golden.additional_metadata
    email_content = f"Subject: {meta['subject']}\n\n{meta['body']}"

    raw = response_drafter_tool.invoke({"email_content": email_content})
    draft_text = raw.get("draft_response", "")

    test_case = LLMTestCase(
        input=email_content,
        actual_output=draft_text,
        expected_output=meta["expected"]["draft_criteria"],
    )
    assert_test(test_case, [draft_quality_metric(threshold=0.7)])
