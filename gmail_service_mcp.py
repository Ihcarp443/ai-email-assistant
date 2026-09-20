from mcp.server.fastmcp import FastMCP

from config.gmail_auth import (
    verify_calendar_connection,
    verify_gmail_connection
)

from services.calender_service import create_google_meet
from services.utils import send_email

mcp = FastMCP("EmailAssistant")

@mcp.tool()
def create_meeting(
    thread_id: str,
    subject: str,
    meeting_date: str,
    meeting_time: str,
    attendees: list[str]
):
    """
    Schedule a Google Meet meeting.
    """

    calendar_service = verify_calendar_connection()

    event = create_google_meet(
        calendar_service=calendar_service,
        subject=subject,
        meeting_date=meeting_date,
        meeting_time=meeting_time,
        attendees=attendees
    )

    meet_link = (
        event.get("conferenceData", {})
             .get("entryPoints", [{}])[0]
             .get("uri", "")
    )

    return {
        "status": "success",
        "meet_link": meet_link,
        "thread_id": thread_id
    }


@mcp.tool()
def send_reply(
    to_email: str,
    subject: str,
    body_text: str,
    thread_id: str
):
    """
    Send email reply.
    """

    gmail_service = verify_gmail_connection()

    status = send_email(
        service=gmail_service,
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        thread_id=thread_id
    )

    return {
        "status": status
    }

if __name__ == "__main__":
    mcp.run()


