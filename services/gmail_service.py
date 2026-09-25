# service/gmail_service
import base64
from email.mime.text import MIMEText

def extract_body(payload):
    body = ""

    if payload.get("body", {}).get("data"):
        body = payload["body"]["data"]

    elif "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                body = part["body"].get("data")
                break

    if body:
        return base64.urlsafe_b64decode(body).decode(
            "utf-8",
            errors="ignore"
        )

    return ""


def fetch_email(service, message_id):
    if not service:
        print("service not defined")
        return None

    email_data = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full"
    ).execute()

    payload = email_data.get("payload", {})
    headers = payload.get("headers", [])

    subject = next(
        (h["value"] for h in headers if h["name"].lower() == "subject"),
        "(No Subject)"
    )

    sender = next(
        (h["value"] for h in headers if h["name"].lower() == "from"),
        "(Unknown Sender)"
    )

    body = extract_body(payload)

    return {
        "email_id": email_data["id"],
        "thread_id": email_data.get("threadId", ""),
        "subject": subject,
        "sender": sender,
        "body": body,
    }