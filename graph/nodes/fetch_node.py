from graph.state import EmailState
from config.gmail_auth import verify_gmail_connection
from services.gmail_service import fetch_email


def fetch_email_node(state: EmailState):
    print("fetching")

    service = verify_gmail_connection()

    message_id = state.get("email_id")

    if not message_id:
        return {"status": "NO_EMAIL_ID"}

    email = fetch_email(service, message_id)

    if not email:
        return {"status": "NO_EMAIL_FOUND"}

    print("fetched successfully")

    return {
        "email_id": email.get("email_id", ""),
        "thread_id": email.get("thread_id", ""),
        "sender": email.get("sender", ""),
        "subject": email.get("subject", ""),
        "body": email.get("body", ""),
        "status": "EMAIL_FETCHED"
    }