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


def fetch_email(service, top_k=1):
    if not service:
        print("service not defined")
        return []

    results = service.users().messages().list(
        userId='me',
        maxResults=top_k
    ).execute()

    messages = results.get('messages', [])

    print(f"\n--- Found {len(messages)} Recent Emails ---")

    emails = []

    for msg in messages:

        email_data = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='full'
        ).execute()

        payload = email_data.get("payload", {})
        headers = payload.get("headers", [])

        subject = next(
            (h["value"] for h in headers if h["name"] == "Subject"),
            "(No Subject)"
        )

        sender = next(
            (h["value"] for h in headers if h["name"] == "From"),
            "(Unknown Sender)"
        )

        body = extract_body(payload)

        email_info = {
            "email_id": msg["id"],
            "thread_id": msg.get("threadId", ""),
            "subject": subject,
            "sender": sender,
            "body": body,
        }

        emails.append(email_info)

        print(f"\nSubject: {subject}")
        print(f"\nSender: {sender}")
        print(f"\nBody Preview: {body[:200]}")

    return emails


def send_email(service, to_email, subject, body_text):
    """Creates and sends an email using the Gmail API."""
    try:
        message = MIMEText(body_text)
        message['to'] = to_email
        message['subject'] = subject

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        create_message = {'raw': raw_message}

        send_status = service.users().messages().send(userId='me', body=create_message).execute()
        print(f"Email sent successfully! Message ID: {send_status['id']}")
        return send_status

    except Exception as e:
        print(f"An error occurred: {e}")
        return None
