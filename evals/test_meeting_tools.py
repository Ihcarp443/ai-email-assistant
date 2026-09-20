import json

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from agents.tools import detect_meeting_intent, extract_meeting_details
from evals.dataset import load_goldens_where
from evals.metrics import ExactMatchMetric, JsonValidityMetric, FieldCoverageMetric

# Only run meeting-tool evals against emails that are actually meeting-related
MEETING_GOLDENS = load_goldens_where(lambda e: e.get("meeting_related") is True)


def _email_content(meta):
    return f"Subject: {meta['subject']}\n\n{meta['body']}"


@pytest.mark.parametrize(
    "golden", MEETING_GOLDENS, ids=[g.additional_metadata["id"] for g in MEETING_GOLDENS]
)
def test_meeting_intent_json_shape(golden):
    """The tool must always return valid JSON with the expected keys."""
    meta = golden.additional_metadata
    raw = detect_meeting_intent.invoke({"email_content": _email_content(meta)})

    test_case = LLMTestCase(
        input=golden.input,
        actual_output=json.dumps(raw),
    )
    assert_test(
        test_case,
        [JsonValidityMetric(required_keys=["meeting_related", "meeting_intent"])],
    )


@pytest.mark.parametrize(
    "golden", MEETING_GOLDENS, ids=[g.additional_metadata["id"] for g in MEETING_GOLDENS]
)
def test_meeting_intent_value(golden):
    """The classified intent (schedule/reschedule/cancel/availability_check/none) is correct."""
    meta = golden.additional_metadata
    raw = detect_meeting_intent.invoke({"email_content": _email_content(meta)})

    test_case = LLMTestCase(
        input=golden.input,
        actual_output=str(raw.get("meeting_intent", "")),
        expected_output=meta["expected"]["meeting_intent"],
    )
    assert_test(test_case, [ExactMatchMetric(name="Meeting Intent Exact Match")])


@pytest.mark.parametrize(
    "golden", MEETING_GOLDENS, ids=[g.additional_metadata["id"] for g in MEETING_GOLDENS]
)
def test_meeting_details_attendees(golden):
    """Attendee names/emails mentioned in the email should show up in the extraction."""
    meta = golden.additional_metadata
    expected = meta["expected"]
    expected_terms = expected.get("attendees_contains", []) + expected.get(
        "attendee_emails_contains", []
    )
    if not expected_terms:
        pytest.skip("No attendee expectations for this golden.")

    raw = extract_meeting_details.invoke({"email_content": _email_content(meta)})

    test_case = LLMTestCase(
        input=golden.input,
        actual_output=json.dumps(raw),
        expected_output=json.dumps(expected_terms),
    )
    assert_test(test_case, [FieldCoverageMetric(threshold=0.7)])


@pytest.mark.parametrize(
    "golden", MEETING_GOLDENS, ids=[g.additional_metadata["id"] for g in MEETING_GOLDENS]
)
def test_meeting_details_missing_info_flagged(golden):
    """When the email is vague (no explicit date/time), the tool should say so
    rather than inventing a date/time (checks Rule #5/#6 in the tool prompt)."""
    meta = golden.additional_metadata
    expected = meta["expected"]
    if not expected.get("missing_information_nonempty"):
        pytest.skip("This golden has explicit date/time; not testing missing-info flagging.")

    raw = extract_meeting_details.invoke({"email_content": _email_content(meta)})
    missing = raw.get("missing_information", [])

    test_case = LLMTestCase(
        input=golden.input,
        actual_output=json.dumps(raw),
    )
    metric = ExactMatchMetric(name="Missing Info Flagged")
    # Deterministic assertion without going through the metric abstraction,
    # since this is a simple non-empty check:
    assert len(missing) > 0, (
        f"Expected missing_information to be non-empty for vague email, got: {raw}"
    )
