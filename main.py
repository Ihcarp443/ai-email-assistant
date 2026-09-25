import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel
from fastapi import Header

from db.db_conn import initialize_db
from db.db_repo import (
    get_actions_by_email,
    get_all_emails,
    get_email_by_id,
    save_action,
)
from inbox_routes import (
    process_message,
    require_token,
    router as inbox_router,
    start_scheduler,
    unwrap,
)
from graph.builder import create_graph
from inbox_routes import set_graph


BASE_DIR = Path(__file__).resolve().parent
EXTENSION_ORIGIN = os.getenv("EXTENSION_ORIGIN", "chrome-extension://hepoanhfpplagbkdndhdeibbobgndooa")
AUTO_SYNC = os.getenv("AUTO_SYNC", "1") == "1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = MultiServerMCPClient(
        {
            "gmail": {
                "command": sys.executable,
                "args": [str(BASE_DIR / "gmail_service_mcp.py")],
                "transport": "stdio",
            }
        }
    )

    tools = await client.get_tools()
    app.state.tools = {t.name: t for t in tools}
    # print("Loaded MCP tools:", list(app.state.tools))
    calendar_tool = app.state.tools.get("check_calendar_availability")

    if calendar_tool is None:
        raise RuntimeError("check_calendar_availability MCP tool not found")

    set_graph(create_graph(calendar_tool))
    # print("Graph created and set in inbox_routes.py")

    scheduler = start_scheduler(app) if AUTO_SYNC else None
    try:
        yield
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)


initialize_db()
print("db initialized")

app = FastAPI(
    title="AI Email Assistant",
    lifespan=lifespan,
    dependencies=[Depends(require_token)],  
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[EXTENSION_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

app.include_router(inbox_router)


class MeetingRequest(BaseModel):
    thread_id: str
    subject: str
    meeting_date: str
    meeting_time: str
    attendees: List[str]


class ReplyRequest(BaseModel):
    to_email: str
    subject: str
    body_text: str
    thread_id: str


def get_tool(request: Request, name: str):
    tool = getattr(request.app.state, "tools", {}).get(name)
    if tool is None:
        raise HTTPException(status_code=503, detail=f"MCP tool '{name}' is not available")
    return tool


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/emails")
def fetch_all_emails():
    try:
        return {"status": "success", "emails": get_all_emails()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/emails/{thread_id}")
def fetch_email(thread_id: str):
    try:
        email = get_email_by_id(thread_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    return {"status": "success", "email": email}


@app.get("/emails/{thread_id}/actions")
def fetch_actions(thread_id: str):
    try:
        return {"status": "success", "actions": get_actions_by_email(thread_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/process-email")
async def process_email_api():
    """
    Original "process the latest email" endpoint, kept for the Streamlit app.
    The side panel uses POST /api/process-email/{message_id} and POST /api/sync
    (both in inbox_routes.py).
    """
    try:
        parsed = await process_message()
        return {"status": "success", "email": parsed}
    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/schedule-meeting")
async def schedule_meeting(data: MeetingRequest, request: Request):
    tool = get_tool(request, "create_meeting")

    try:
        result = unwrap(
            await tool.ainvoke(
                {
                    "thread_id": data.thread_id,
                    "subject": data.subject,
                    "meeting_date": data.meeting_date,
                    "meeting_time": data.meeting_time,
                    "attendees": data.attendees,
                }
            )
        )
    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))

    meet_link = result.get("meet_link", "")
    if result.get("status") != "success" or not meet_link:
        raise HTTPException(
            status_code=502,
            detail=result.get("error") or "Google Calendar did not return a Meet link",
        )

    save_action(thread_id=data.thread_id, action_type="meeting_scheduled", action_value=meet_link)
    return {"status": "success", "meet_link": meet_link}


@app.post("/send-reply")
async def handle_send_reply(data: ReplyRequest, request: Request):
    """Send the reply through the MCP `send_reply` tool."""
    print(f"handle_send_reply: to={data.to_email}, subject={data.subject}, thread_id={data.thread_id}")
    tool = get_tool(request, "send_reply")

    try:
        result = unwrap(
            await tool.ainvoke(
                {
                    "to_email": data.to_email,
                    "subject": data.subject,
                    "body_text": data.body_text,
                    "thread_id": data.thread_id,
                }
            )
        )
        print(f"handle_send_reply: result={result}")
    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))

    if result.get("status") != "success":
        raise HTTPException(
            status_code=502,
            detail=result.get("error") or "Failed to deliver message via Gmail.",
        )

    save_action(thread_id=data.thread_id, action_type="reply_sent", action_value="success")
    return {"status": "success", "message": "Email sent successfully"}