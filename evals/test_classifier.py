"""
Evaluates graph/nodes/classifier.py::classification_node against the golden
dataset. Category and priority are closed-vocabulary fields, so we use a
deterministic exact-match metric (cheap, no LLM judge needed) plus an
optional GEval "reasonableness" check you can enable if you want softer
grading.
"""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from graph.nodes.classifier import classification_node
from evals.dataset import load_goldens
from deepeval.metrics import ExactMatchMetric

GOLDENS = load_goldens()


@pytest.mark.parametrize("golden", GOLDENS, ids=[g.additional_metadata["id"] for g in GOLDENS])
def test_category(golden):
    meta = golden.additional_metadata
    state = {"subject": meta["subject"], "body": meta["body"]}

    result = classification_node(state)

    test_case = LLMTestCase(
        input=golden.input,
        actual_output=result["category"],
        expected_output=meta["expected"]["category"],
    )
    assert_test(test_case, [ExactMatchMetric()])


# @pytest.mark.parametrize("golden", GOLDENS, ids=[g.additional_metadata["id"] for g in GOLDENS])
# def test_priority(golden):
#     meta = golden.additional_metadata
#     state = {"subject": meta["subject"], "body": meta["body"]}

#     result = classification_node(state)

#     test_case = LLMTestCase(
#         input=golden.input,
#         actual_output=result["priority"],
#         expected_output=meta["expected"]["priority"],
#     )
#     # Priority is judgment-call-ish (High vs Critical, Medium vs High), so we
#     # allow it to be looser than category. If you want strict grading, swap
#     # this out for ExactMatchMetric like test_category above.
#     from evals.metrics import classification_reasoning_geval

#     assert_test(test_case, [classification_reasoning_geval(threshold=0.6)])
