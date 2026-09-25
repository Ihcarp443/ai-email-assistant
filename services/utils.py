import base64
import json
import sys
from email.mime.text import MIMEText

from graph.state import EmailState


def _log(message: str) -> None:
    print(message, file=sys.stderr)


def unwrap(result):
    if isinstance(result, dict):
        return result
    if isinstance(result, list):
        result = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in result
        )
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"text": result}
    return {}

def get_initial_state(message_id: str | None = None) -> EmailState:
    return {
        "email_id": message_id or "",
        "thread_id": "",
        "sender": "",
        "recipient": "",
        "subject": "",
        "body": "",
        "messages": [],
        "extracted_entities": {},
        "action_items": [],
        "category": "",
        "priority": "",
        "retrieved_context": {},
        "reasoning": "",
        "agent_actions": [],
        "tool_outputs": {},
        "status": "STARTED",
    }


def _strip_subject_line(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip().lower().startswith("subject:"):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
    return "\n".join(lines)


def parse_agent_output(result):
    action_items = []
    meeting = {"meeting_detected": "No", "meeting_date": "N/A", "meeting_time": "N/A", "attendees": []}
    draft_response = ""

    messages = result.get("messages", [])
    for msg in messages:
        if isinstance(msg, dict):
            msg_type = msg.get("type")
            msg_name = msg.get("name")
            msg_content = msg.get("content", "")
        else:
            msg_type = getattr(msg, "type", None)
            msg_name = getattr(msg, "name", None)
            msg_content = getattr(msg, "content", "")

        if msg_type == "tool":
            if msg_name == "extract_action_items":
                try:
                    action_items = json.loads(msg_content).get("action_items", [])
                except Exception:
                    pass
            elif msg_name == "schedule_meeting":
                try:
                    meeting = json.loads(msg_content)
                except Exception:
                    pass
            elif msg_name in ("detect_meeting_intent", "extract_meeting_details"):
                try:
                    meeting.update(json.loads(msg_content))
                except Exception:
                    pass
            elif msg_name == "response_drafter_tool":
                try:
                    draft_response = json.loads(msg_content).get("draft_response", "")
                except Exception:
                    pass

    meeting["attendees"] = [
        a if isinstance(a, dict) else {"name": str(a), "email": ""}
        for a in meeting.get("attendees", [])
    ]
    if "meeting_related" not in meeting:
        meeting["meeting_related"] = meeting.get("meeting_detected") is True
    else:
        meeting["meeting_detected"] = True if meeting.get("meeting_related") else "No"

    result["parsed_action_items"] = action_items
    result["parsed_meeting"] = meeting
    result["parsed_draft"] = _strip_subject_line(draft_response)
    return result


def send_email(service, to_email, subject, body_text, thread_id=None):
    """Creates and sends an email. Optionally attaches to an existing Gmail thread."""
    try:
        if thread_id and not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        message = MIMEText(body_text)
        message["to"] = to_email
        message["subject"] = subject

        create_message = {}
        create_message["raw"] = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        send_status = service.users().messages().send(userId="me", body=create_message).execute()
        _log(f"Email sent successfully! Message ID: {send_status['id']}")
        return send_status

    except Exception as e:
        _log(f"An error occurred: {type(e).__name__}: {e}")
        raise