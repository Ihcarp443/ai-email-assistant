import asyncio
import json
import os
import uuid

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool

from db.db_repo import get_all_emails, save_email_history
from services.utils import get_initial_state, parse_agent_output

graph = None


def set_graph(value):
    global graph
    graph = value

router = APIRouter()

API_TOKEN = os.getenv("EMAIL_ASSISTANT_TOKEN", "")
MAX_PARALLEL = 2            
SYNC_INTERVAL_MIN = 15
SYNC_LIMIT = 14

_sync_lock = asyncio.Lock()

def require_token(x_api_key: str = Header(default="")):
    # print(f"require_token: x_api_key={x_api_key}, API_TOKEN={API_TOKEN}")
    if API_TOKEN and x_api_key != API_TOKEN:
        print(f"Invalid API key: {x_api_key}")
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# Helpers
def unwrap(result):
    """
    MCP tool results arrive as a dict, a JSON string, or a list of content
    blocks depending on the langchain-mcp-adapters version. Always return a dict.
    """
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


def as_dict(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value or {}


def processed_index() -> dict:
    """Map message id -> stored row. Prefers email_id so two mails in one thread don't collide."""
    return {(r.get("email_id") or r.get("thread_id")): r for r in get_all_emails()}


async def fetch_recent(tools: dict, limit: int) -> list[dict]:
    tool = tools.get("list_recent_emails")
    if tool is None:
        raise HTTPException(status_code=500, detail="MCP tool 'list_recent_emails' is not loaded")
    data = unwrap(await tool.ainvoke({"limit": limit}))
    return data.get("emails", [])


async def process_message(message_id: str | None = None) -> dict:
    state = await run_in_threadpool(get_initial_state, message_id)
    run_id = message_id or uuid.uuid4().hex

    result = await graph.ainvoke(state, {"configurable": {"thread_id": run_id}})

    parsed = parse_agent_output(result)
    await run_in_threadpool(save_email_history, parsed)
    return parsed



# Routes
@router.get("/api/inbox")
async def inbox(request: Request, limit: int = Query(SYNC_LIMIT, ge=1, le=50)):
    """Latest N Gmail messages, each flagged with whether it was already processed."""
    recent = await fetch_recent(request.app.state.tools, limit)
    done = processed_index()

    emails = []
    for m in recent:
        row = done.get(m["message_id"])
        item = {**m, "processed": row is not None}
        if row:
            meeting = as_dict(row.get("meeting_details"))
            item.update(
                thread_id=row.get("thread_id") or m.get("thread_id"),
                category=row.get("category"),
                priority=row.get("priority"),
                status=row.get("status"),
                has_meeting=bool(meeting.get("meeting_related")),
            )
        emails.append(item)

    return {"status": "success", "emails": emails}


@router.post("/api/process-email/{message_id}")
async def process_one(message_id: str):
    try:
        parsed = await process_message(message_id)
    except Exception as e:
        print("process_one failed:", e)
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "success", "email": parsed}


async def run_sync(tools: dict, limit: int) -> dict:
    """Process every not-yet-processed mail among the latest `limit`."""
    if _sync_lock.locked():                      # overlapping syncs would double-charge the LLM
        return {"status": "busy", "processed": 0, "failed": 0, "already_processed": 0}

    async with _sync_lock:
        recent = await fetch_recent(tools, limit)
        done = processed_index()
        todo = [m["message_id"] for m in recent if m["message_id"] not in done]

        gate = asyncio.Semaphore(MAX_PARALLEL)

        async def one(message_id: str) -> bool:
            async with gate:
                try:
                    await process_message(message_id)
                    return True
                except Exception as e:
                    print(f"sync: {message_id} failed: {e}")
                    return False

        results = await asyncio.gather(*(one(mid) for mid in todo))
        ok = sum(results)
        return {
            "status": "success",
            "processed": ok,
            "failed": len(results) - ok,
            "already_processed": len(recent) - len(todo),
        }


@router.post("/api/sync")
async def sync(request: Request, limit: int = Query(SYNC_LIMIT, ge=1, le=50)):
    return await run_sync(request.app.state.tools, limit)


def start_scheduler(app):
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    async def job():
        await run_sync(app.state.tools, SYNC_LIMIT)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        job, "interval", minutes=SYNC_INTERVAL_MIN,
        id="inbox-sync", max_instances=1, coalesce=True,
    )
    scheduler.start()
    return scheduler