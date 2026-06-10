"""Inbox API — proactive inbox app read surface."""

from fastapi import APIRouter, Query

from app.product.inbox import generate_inbox_digest, latest_digest, list_inbox_emails, poll_inbox

router = APIRouter(prefix="/api/inbox", tags=["inbox"])


@router.get("/")
async def get_inbox(
    category: str | None = Query(None, pattern="^(important|actionable|ignorable)$"),
    limit: int = Query(50, ge=1, le=200),
):
    return list_inbox_emails(category=category, limit=limit)


@router.get("/digest")
async def get_digest():
    digest = latest_digest()
    return digest or {"message": "no digest yet"}


@router.post("/poll")
async def trigger_poll(limit: int = Query(20, ge=1, le=50)):
    return await poll_inbox(limit=limit)


@router.post("/digest")
async def trigger_digest():
    digest = generate_inbox_digest()
    return digest or {"message": "no emails to digest"}
