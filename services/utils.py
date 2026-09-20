import json, base64
from graph.state import EmailState
from email.mime.text import MIMEText

def get_initial_state() -> EmailState:
    return {
        "email_id": "",
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
        "status": "STARTED"
    }

def parse_agent_output(result):
    action_items = []
    meeting = {"meeting_detected": "No", "meeting_date": "N/A", "meeting_time": "N/A", "attendees": []}
    draft_response = ""
    # print("result", result)
    
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
                    data = json.loads(msg_content)
                    action_items = data.get("action_items", [])
                except Exception:
                    pass
            elif msg_name == "schedule_meeting":
                try:
                    meeting = json.loads(msg_content)
                except Exception:
                    pass
            elif msg_name == "detect_meeting_intent":
                try:
                    data = json.loads(msg_content)
                    meeting.update(data)
                except Exception:
                    pass

            elif msg_name == "extract_meeting_details":
                try:
                    data = json.loads(msg_content)
                    meeting.update(data)
                except Exception:
                    pass
            elif msg_name == "response_drafter_tool":
                try:
                    data = json.loads(msg_content)
                    draft_response = data.get("draft_response", "")
                except Exception:
                    pass
                    
    result["parsed_action_items"] = action_items
    result["parsed_meeting"] = meeting
    result["parsed_draft"] = draft_response
    return result

def send_email(service, to_email, subject, body_text, thread_id=None):
    """Creates and sends an email. Optionally attaches to an existing thread."""
    try:
        if thread_id and not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        message = MIMEText(body_text)
        message['to'] = to_email
        message['subject'] = subject

        create_message = {}
        
        if thread_id:
            message['In-Reply-To'] = thread_id
            message['References'] = thread_id
            create_message['threadId'] = thread_id

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        create_message['raw'] = raw_message

        send_status = service.users().messages().send(userId='me', body=create_message).execute()
        print(f"Email sent successfully! Message ID: {send_status['id']}")
        return send_status

    except Exception as e:
        print(f"An error occurred: {e}")
        return None