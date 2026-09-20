import json

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from agents.tools import extract_action_items
from evals.dataset import load_goldens
from evals.metrics import JsonValidityMetric, action_items_geval

GOLDENS = load_goldens()


@pytest.mark.parametrize("golden", GOLDENS, ids=[g.additional_metadata["id"] for g in GOLDENS])
def test_action_items_json_shape(golden):
    meta = golden.additional_metadata
    email_content = f"Subject: {meta['subject']}\n\n{meta['body']}"

    raw = extract_action_items.invoke({"email_content": email_content})

    test_case = LLMTestCase(input=golden.input, actual_output=json.dumps(raw))
    assert_test(test_case, [JsonValidityMetric(required_keys=["action_items"])])


@pytest.mark.parametrize("golden", GOLDENS, ids=[g.additional_metadata["id"] for g in GOLDENS])
def test_action_items_correctness(golden):
    """LLM-judged: did it find the same tasks (wording may vary) without inventing extras?"""
    meta = golden.additional_metadata
    expected_items = meta["expected"].get("action_items", [])
    email_content = f"Subject: {meta['subject']}\n\n{meta['body']}"

    raw = extract_action_items.invoke({"email_content": email_content})

    test_case = LLMTestCase(
        input=golden.input,
        actual_output=json.dumps(raw),
        expected_output=json.dumps(expected_items),
    )
    assert_test(test_case, [action_items_geval(threshold=0.6)])
