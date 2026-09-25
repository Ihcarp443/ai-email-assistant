import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from mcp.server.fastmcp import FastMCP
from config.gmail_auth import (
    verify_calendar_connection,
    verify_gmail_connection,
)
from services.calender_service import create_google_meet
from services.utils import send_email
import os

mcp = FastMCP("EmailAssistant")


def _log(message: str) -> None:
    print(message, file=sys.stderr)


@mcp.tool()
def list_recent_emails(limit: int = 14) -> dict:
    """List the most recent inbox emails (metadata and preview only, no full bodies)."""
    service = verify_gmail_connection()

    listing = service.users().messages().list(
        userId="me", labelIds=["INBOX"], maxResults=max(1, min(limit, 50))
    ).execute()

    def header(headers, name):
        return next((h["value"] for h in headers if h["name"].lower() == name), "")

    emails = []
    for ref in listing.get("messages", []):
        msg = service.users().messages().get(
            userId="me",
            id=ref["id"],
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"],
        ).execute()

        headers = msg.get("payload", {}).get("headers", [])
        emails.append(
            {
                "message_id": msg["id"],
                "thread_id": msg["threadId"],
                "subject": header(headers, "subject"),
                "sender": header(headers, "from"),
                "date": header(headers, "date"),
                "snippet": msg.get("snippet", ""),
                "unread": "UNREAD" in msg.get("labelIds", []),
            }
        )

    return {"emails": emails}


@mcp.tool()
def create_meeting(
    thread_id: str,
    subject: str,
    meeting_date: str,
    meeting_time: str,
    attendees: list[str],
) -> dict:
    """Schedule a Google Meet meeting and return its link."""
    try:
        calendar_service = verify_calendar_connection()

        event = create_google_meet(
            calendar_service=calendar_service,
            subject=subject,
            meeting_date=meeting_date,
            meeting_time=meeting_time,
            attendees=attendees,
        )

        meet_link = (
            event.get("conferenceData", {})
            .get("entryPoints", [{}])[0]
            .get("uri", "")
        )

        if not meet_link:
            return {"status": "error", "error": "The event was created but has no Meet link"}

        return {"status": "success", "meet_link": meet_link, "thread_id": thread_id}

    except Exception as e:
        _log(f"create_meeting failed: {e}")
        return {"status": "error", "error": str(e)}


@mcp.tool()
def send_reply(
    to_email: str,
    subject: str,
    body_text: str,
    thread_id: str,
) -> dict:
    """Send an email reply inside an existing Gmail thread."""
    try:
        print(f"send_reply: to={to_email}, subject={subject}, thread_id={thread_id}")
        gmail_service = verify_gmail_connection()

        sent = send_email(
            service=gmail_service,
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            thread_id=thread_id,
        )
        print(f"send_reply: sent={sent}")

        if not sent:
            return {"status": "error", "error": "Gmail rejected the message or the send failed"}

        return {"status": "success", "message_id": sent.get("id", "")}

    except Exception as e:
        _log(f"send_reply failed: {e}")
        return {"status": "error", "error": str(e)}


CALENDAR_TZ = ZoneInfo(os.getenv("CALENDAR_TIMEZONE", "Asia/Kolkata"))
WORK_START_HOUR = 9
WORK_END_HOUR = 18
 
 
@mcp.tool()
def check_calendar_availability(
    meeting_date: str,
    meeting_time: str,
    duration_minutes: int = 30,
) -> dict:
    """
    Check whether the user's primary Google Calendar is free at a given time.
    meeting_date is YYYY-MM-DD, meeting_time is HH:MM (24-hour). Returns any conflicts
    and up to 3 free alternative start times on the same day (09:00-18:00).
    """
    try:
        start = datetime.strptime(f"{meeting_date} {meeting_time}", "%Y-%m-%d %H:%M").replace(
            tzinfo=CALENDAR_TZ
        )
    except ValueError:
        return {
            "status": "error",
            "error": "meeting_date must be YYYY-MM-DD and meeting_time must be HH:MM (24-hour)",
        }
 
    duration = timedelta(minutes=max(5, duration_minutes))
    end = start + duration
 
    # Search window: the working day, widened if the requested slot is outside it.
    day_start = min(start.replace(hour=WORK_START_HOUR, minute=0), start)
    day_end = max(start.replace(hour=WORK_END_HOUR, minute=0), end)
 
    try:
        service = verify_calendar_connection()
        response = service.freebusy().query(
            body={
                "timeMin": day_start.isoformat(),
                "timeMax": day_end.isoformat(),
                "timeZone": str(CALENDAR_TZ),
                "items": [{"id": "primary"}],
            }
        ).execute()
        _log(f"check_calendar_availability called: {meeting_date} {meeting_time} ({duration_minutes}m)")
    except Exception as e:
        _log(f"check_calendar_availability failed: {e}")
        return {"status": "error", "error": str(e)}
 
    def to_local(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(CALENDAR_TZ)
 
    busy = [
        (to_local(b["start"]), to_local(b["end"]))
        for b in response.get("calendars", {}).get("primary", {}).get("busy", [])
    ]
 
    def overlaps(a_start, a_end):
        return any(b_start < a_end and b_end > a_start for b_start, b_end in busy)
 
    conflicts = [
        {"start": b_start.strftime("%H:%M"), "end": b_end.strftime("%H:%M")}
        for b_start, b_end in busy
        if b_start < end and b_end > start
    ]
 
    alternatives = []
    if conflicts:
        
        cursor = day_start.replace(hour=WORK_START_HOUR, minute=0)
        while cursor + duration <= day_end.replace(hour=WORK_END_HOUR, minute=0):
            if not overlaps(cursor, cursor + duration):
                alternatives.append(cursor)
            cursor += timedelta(minutes=30)
        alternatives.sort(key=lambda t: abs(t - start))       # nearest to the requested time first
        alternatives = sorted(alternatives[:3])
    _log(f"check_calendar_availability result: free={not conflicts}, conflicts={conflicts}")
 
    return {
        "status": "success",
        "free": not conflicts,
        "conflicts": conflicts,
        "alternatives": [t.strftime("%H:%M") for t in alternatives],
        "timezone": str(CALENDAR_TZ),
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")
