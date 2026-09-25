# services/calendar_service.py
from datetime import datetime, timedelta
import uuid

def create_google_meet(
    calendar_service,
    subject,
    meeting_date,
    meeting_time,
    attendees=None
):
    print("Creating meeting")

    start_dt = datetime.strptime(
        f"{meeting_date} {meeting_time}",
        "%Y-%m-%d %H:%M"
    )

    end_dt = start_dt + timedelta(hours=1)

    event = {
        "summary": subject,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "Asia/Kolkata"
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "Asia/Kolkata"
        },
        "attendees": [
            {"email": email}
            for email in (attendees or [])
        ],
        "conferenceData": {
            "createRequest": {
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {
                    "type": "hangoutsMeet"
                }
            }
        }
    }

    result = calendar_service.events().insert(
        calendarId="primary",
        body=event,
        conferenceDataVersion=1,
        sendUpdates="all"
    ).execute()

    return result