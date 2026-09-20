"""
Loads evals/golden_dataset.json into DeepEval Goldens.

Each golden's `input` is the raw email (what the pipeline consumes) and
`expected_output` is the structured dict we assert against. We keep the
raw structured `expected` dict in `additional_metadata` so each test file
can pull out just the fields it cares about (category, meeting fields,
action items, draft criteria, etc.) without re-parsing anything.
"""

import json
from pathlib import Path
from deepeval.dataset import Golden

DATASET_PATH = Path(__file__).parent / "golden_dataset.json"


def _email_text(entry: dict) -> str:
    """Same shape the agent/tools receive: subject + sender + body."""
    return (
        f"Subject:\n{entry['subject']}\n\n"
        f"Sender:\n{entry['sender']}\n\n"
        f"Body:\n{entry['body']}"
    )


def load_raw_goldens() -> list[dict]:
    with open(DATASET_PATH) as f:
        return json.load(f)


def load_goldens() -> list[Golden]:
    """All entries as generic DeepEval Goldens (input = email text)."""
    goldens = []
    for entry in load_raw_goldens():
        goldens.append(
            Golden(
                input=_email_text(entry),
                expected_output=json.dumps(entry["expected"]),
                additional_metadata={"id": entry["id"], **entry},
            )
        )
    return goldens


def load_goldens_where(predicate) -> list[Golden]:
    """Filter goldens by a predicate over the raw `expected` dict.

    Example: load_goldens_where(lambda e: e.get("meeting_related"))
    """
    goldens = []
    for entry in load_raw_goldens():
        if predicate(entry["expected"]):
            goldens.append(
                Golden(
                    input=_email_text(entry),
                    expected_output=json.dumps(entry["expected"]),
                    additional_metadata={"id": entry["id"], **entry},
                )
            )
    return goldens
