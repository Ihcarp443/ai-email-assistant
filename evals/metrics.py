"""
Metrics used across the eval suite.

- ExactMatchMetric        -> deterministic field checks (category, priority,
                              meeting_intent). No LLM judge, no API cost.
- FieldCoverageMetric     -> deterministic partial-credit check for lists of
                              dicts (action_items, attendees) against a set
                              of required substrings.
- JsonValidityMetric      -> deterministic: does the tool output parse as JSON
                              and contain the expected keys.
- draft_quality_metric()  -> GEval (LLM-judged) factory for response_drafter_tool.
- action_items_geval      -> GEval judge for cases where exact substring
                              matching on action items is too strict.
"""

import json
from deepeval.metrics import BaseMetric, GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
import os
from langchain_groq import ChatGroq
from deepeval.models import DeepEvalBaseLLM


class GroqJudge(DeepEvalBaseLLM):
    def __init__(self, model_name: str = "openai/gpt-oss-20b"):
        self.model_name = model_name
        self.model = ChatGroq(
            model=model_name,
            temperature=0,
            api_key=os.getenv("GROQ_API_KEY"),
        )

    def load_model(self):
        return self.model

    def generate(self, prompt: str) -> str:
        return self.model.invoke(prompt).content

    async def a_generate(self, prompt: str) -> str:
        response = await self.model.ainvoke(prompt)
        return response.content

    def get_model_name(self) -> str:
        return self.model_name


judge_llm = GroqJudge()


# class ExactMatchMetric(BaseMetric):
#     """Case-insensitive exact match between actual_output and expected_output."""

#     def __init__(self, name: str = "Exact Match", threshold: float = 1.0):
#         self.threshold = threshold
#         self.name = name

#     def measure(self, test_case: LLMTestCase):
#         actual = (test_case.actual_output or "").strip().lower()
#         expected = (test_case.expected_output or "").strip().lower()
#         self.success = actual == expected
#         self.score = 1.0 if self.success else 0.0
#         self.reason = (
#             f"expected='{test_case.expected_output}' actual='{test_case.actual_output}'"
#         )
#         return self.score

#     async def a_measure(self, test_case: LLMTestCase):
#         return self.measure(test_case)

#     def is_successful(self):
#         return self.success


class FieldCoverageMetric(BaseMetric):
    """
    Partial-credit check: what fraction of expected substrings (e.g. names,
    emails, task keywords) show up somewhere in the actual JSON output.
    Use for lists where exact structural match is too brittle (LLM extraction
    won't always order fields identically).
    """

    def __init__(self, name: str = "Field Coverage", threshold: float = 0.7):
        self.threshold = threshold
        self.name = name

    def measure(self, test_case: LLMTestCase):
        expected_terms = json.loads(test_case.expected_output or "[]")
        actual_text = (test_case.actual_output or "").lower()

        if not expected_terms:
            # nothing expected -> pass only if actual is also empty/near-empty
            self.score = 1.0 if len(actual_text.strip()) < 5 or actual_text.strip() in ("[]", "{}") else 0.0
            self.success = self.score >= self.threshold
            self.reason = "No terms expected; checked actual output is empty."
            return self.score

        hits = sum(1 for term in expected_terms if term.lower() in actual_text)
        self.score = hits / len(expected_terms)
        self.success = self.score >= self.threshold
        self.reason = f"{hits}/{len(expected_terms)} expected terms found in output."
        return self.score

    async def a_measure(self, test_case: LLMTestCase):
        return self.measure(test_case)

    def is_successful(self):
        return self.success


class JsonValidityMetric(BaseMetric):
    """Checks the tool output is valid JSON and contains the required keys."""

    def __init__(self, required_keys: list[str], name: str = "JSON Validity", threshold: float = 1.0):
        self.required_keys = required_keys
        self.threshold = threshold
        self.name = name

    def measure(self, test_case: LLMTestCase):
        try:
            data = json.loads(test_case.actual_output)
            missing = [k for k in self.required_keys if k not in data]
            self.success = len(missing) == 0
            self.score = 1.0 if self.success else 0.0
            self.reason = "Valid JSON with all required keys." if self.success else f"Missing keys: {missing}"
        except Exception as e:
            self.success = False
            self.score = 0.0
            self.reason = f"Not valid JSON: {e}"
        return self.score

    async def a_measure(self, test_case: LLMTestCase):
        return self.measure(test_case)

    def is_successful(self):
        return self.success


def draft_quality_metric(threshold: float = 0.7) -> GEval:
    """LLM-judged quality check for response_drafter_tool output."""
    return GEval(
        name="Draft Response Quality",
        criteria=(
            "Determine if the 'actual output' is a professional, concise email reply "
            "that appropriately addresses the criteria described in 'expected output', "
            "given the original email in 'input'. It should acknowledge the sender, "
            "not invent facts, dates, or attendees not present in the input, and match "
            "a professional tone."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        threshold=threshold,
        model = judge_llm,
    )


def action_items_geval(threshold: float = 0.7) -> GEval:
    """LLM-judged check for extracted action items when exact match is too strict."""
    return GEval(
        name="Action Item Extraction Correctness",
        criteria=(
            "Compare the action items in 'actual output' (JSON) against the action "
            "items described in 'expected output'. Score high if the same tasks and "
            "deadlines were captured (wording may differ), and score low if items were "
            "missed or invented."
        ),
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        threshold=threshold,
        model = judge_llm,
    )


def classification_reasoning_geval(threshold: float = 0.7) -> GEval:
    """Optional: judge whether category+priority choice is *reasonable*, not just exact-match."""
    return GEval(
        name="Classification Reasonableness",
        criteria=(
            "Given the original email in 'input', judge whether the category and priority "
            "in 'actual output' are a reasonable classification, even if not identical to "
            "'expected output'."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        threshold=threshold,
        model = judge_llm,
    )
