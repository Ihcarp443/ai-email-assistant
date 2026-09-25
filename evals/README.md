# DeepEval suite for ai-email-assistant

Evals are split to mirror your LangGraph pipeline (`fetch -> classifier -> agent`),
so a failing test tells you exactly which component regressed instead of just
"the email pipeline is wrong somewhere."

```
evals/
├── golden_dataset.json        # 16 hand-written emails covering every category,
│                              # priority, meeting intent, and the spam/newsletter
│                              # "don't draft" rule
├── dataset.py                 # loads goldens, with filtering helpers
├── metrics.py                 # deterministic + GEval (LLM-judge) metrics
├── conftest.py                # repo import path + env var checks
├── test_classifier.py         # graph/nodes/classifier.py
├── test_meeting_tools.py      # detect_meeting_intent, extract_meeting_details
├── test_action_items.py       # extract_action_items
├── test_response_drafter.py   # response_drafter_tool
└── test_end_to_end_agent.py   # agents/email_agent.py — did it call the right tools?
```

## Why the dataset looks the way it does

Every golden's `expected` block only fills in the fields relevant to it, and
each test file filters the dataset down to the goldens it needs
(`load_goldens_where(...)`). For example, `test_meeting_tools.py` only runs
against the 6 meeting-related emails — there's no point asking
`extract_meeting_details` to grade a newsletter.

The one behavioral rule baked into your `SYSTEM_PROMPT` — *don't draft for
spam/newsletter, but meeting detection and drafting are otherwise
independent* — is exactly what `test_end_to_end_agent.py` checks, since it's
an emergent property of the agent's tool-calling, not something a single
tool test can catch.

## Metric choices

| Field | Metric | Why |
|---|---|---|
| `category`, `meeting_intent` | `ExactMatchMetric` (deterministic) | Closed vocabulary — exact match is the right bar, and it's free/instant. |
| `priority` | `GEval` (LLM judge) | "High" vs "Critical" is a judgment call; exact match is too strict. |
| attendees / action items | `FieldCoverageMetric` or `GEval` | Free-text extraction — wording varies even when correct. |
| draft response | `GEval` | Genuinely needs semantic judgment (tone, doesn't invent facts). |
| tool JSON outputs | `JsonValidityMetric` (deterministic) | Every tool prompt asks for "ONLY valid JSON" — cheap to verify structurally before judging content. |

## Setup

```bash
pip install -r evals/requirements-eval.txt
export GOOGLE_API_KEY=...        # the pipeline itself uses Gemini
export OPENAI_API_KEY=...        # DeepEval's default GEval judge model
# or: deepeval set-local-model ...  /  deepeval set-gemini ...
# to point GEval's judge at Gemini instead of OpenAI
```

Run from the **repo root** (not inside `evals/`), so the `graph`/`agents`/
`config`/`services` imports resolve:

```bash
deepeval test run evals/
# or plain pytest:
pytest evals/ -v
```

Run just one component while iterating on a prompt:

```bash
pytest evals/test_classifier.py -v
pytest evals/test_meeting_tools.py -v -k "meet-reschedule"
```

## Extending the dataset

Add a new object to `golden_dataset.json` with `subject`/`sender`/`body` and
an `expected` block. Only include the keys the relevant tests check for
(see the table above) — you don't need to fill in every field for every
email, e.g. a non-meeting email doesn't need `meeting_intent`.

## Known gaps / things to wire up next

- `test_end_to_end_agent.py` is the most expensive suite (multiple LLM +
  tool calls per case) — run it last, or mark it `@pytest.mark.slow` and
  exclude by default once you add a `pytest.ini`.
- No test currently covers `services/calender_service.py` or Gmail
  send/fetch — those need mocked Google API clients rather than golden
  emails, which is a different kind of test (unit/integration, not an LLM eval).
- If you want CI regression tracking over time, push this dataset to
  Confident AI (`deepeval login`) instead of keeping it as a local JSON file,
  then swap `dataset.py` to `EvaluationDataset(alias=...).pull()`.
