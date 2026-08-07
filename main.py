from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from config.gmail_auth import verify_gmail_connection, verify_calendar_connection
from graph.builder import graph
from services.calender_service import create_google_meet
from services.utils import get_initial_state, parse_agent_output, send_email
from db.db_conn import initialize_db
from db.db_repo import save_action, save_email_history, get_all_emails, get_email_by_id, get_actions_by_email

initialize_db()

app = FastAPI(title="AI Email Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MeetingRequest(BaseModel):
    thread_id:str
    subject: str
    meeting_date: str
    meeting_time: str
    attendees: List[str]

class ReplyRequest(BaseModel):
    to_email: str
    subject: str
    body_text: str
    thread_id: str 

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/emails")
def fetch_all_emails():
    try:
        emails = get_all_emails()
        return {
            "status": "success",
            "emails": emails
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/emails/{thread_id}")
def fetch_email(thread_id: str):
    try:
        email = get_email_by_id(thread_id)

        if not email:
            raise HTTPException(
                status_code=404,
                detail="Email not found"
            )

        return {
            "status": "success",
            "email": email
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/emails/{thread_id}/actions")
def fetch_actions(thread_id: str):
    try:

        actions = get_actions_by_email(thread_id)

        return {
            "status": "success",
            "actions": actions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/process-email")
def process_email_api():
    """
    Invokes the LangGraph email routing pipeline.
    Returns clean JSON layout data directly to Streamlit.
    """
    try:
        initial_state = get_initial_state()
        # result = graph.invoke(
        #     initial_state, 
        #     config={"configurable": {"thread_id": "demo"}}
        # )
        # print("Result",result)
        global result
        # =========================
        parsed_result = parse_agent_output(result)
        print(parsed_result)
        save_email_history(parsed_result)
        return {"status": "success", "email": parsed_result}
    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/schedule-meeting")
async def schedule_meeting(data: MeetingRequest):
    """
    Handles Google Workspace Calendar and Meet injection.
    Receives JSON body parameters and returns the created event URI link.
    """
    try:
        calendar_service = verify_calendar_connection()

        event = create_google_meet(
            calendar_service=calendar_service,
            subject=data.subject,
            meeting_date=data.meeting_date,
            meeting_time=data.meeting_time,
            attendees=data.attendees
        )

        meet_link = (
            event.get("conferenceData", {})
                 .get("entryPoints", [{}])[0]
                 .get("uri", "")
        )
        save_action(
            thread_id = data.thread_id,
            action_type="meeting_scheduled",
            action_value=meet_link
        )
        
        return {"status": "success", "meet_link": meet_link}
    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/send-reply")
async def handle_send_reply(data: ReplyRequest):
    """
    Dispatches outbound email drafts over the Gmail OAuth client relay.
    """
    try:
        service = verify_gmail_connection()
        if not service:
            raise HTTPException(status_code=401, detail="Gmail authentication service not available.")

        status = send_email(
            service=service,
            to_email=data.to_email,
            subject=data.subject,
            body_text=data.body_text,
            thread_id=data.thread_id
        )
        save_action(
            thread_id=data.thread_id,
            action_type="reply_sent",
            action_value="success"
        )
        if not status:
            raise HTTPException(status_code=500, detail="Failed to deliver message via Gmail Client.")

        return {"status": "success", "message": "Email sent successfully"}
    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))