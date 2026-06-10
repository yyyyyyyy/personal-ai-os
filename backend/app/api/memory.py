"""Memory API — manage long-term memories and user profile."""

from fastapi import APIRouter, HTTPException

from app.core.agents.memory_engine import memory_engine
from app.core.agents.memory_v2 import user_profile
from app.core.runtime import claim_authority

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/memories")
async def list_memories(category: str | None = None, limit: int = 50):
    """List all memories, optionally filtered by category."""
    return memory_engine.list_memories(category=category, limit=limit)


@router.post("/memories")
async def create_memory(body: dict):
    """Create a new memory manually."""
    content = body.get("content")
    category = body.get("category", "fact")
    source = body.get("source", "manual")

    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    memory_id = memory_engine.store_memory(content, category, source)
    return {"id": memory_id, "status": "ok"}


@router.get("/memories/search")
async def search_memories(q: str, n: int = 5):
    """Search memories semantically."""
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    return memory_engine.search_relevant_memories(q, n_results=n)


@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a specific memory."""
    memory_engine.delete_memory(memory_id)
    return {"status": "ok"}


@router.put("/memories/{memory_id}")
async def update_memory(memory_id: str, body: dict):
    """Update a memory's content or category."""
    content = body.get("content")
    category = body.get("category")

    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    memory_engine.update_memory(memory_id, content, category=category)
    return {"status": "ok"}


# --- Claim authority (Meaning Boundary G1) ---


def _claim_action(memory_id: str, action: str, body: dict | None = None) -> dict:
    body = body or {}
    reason = body.get("reason", "")
    try:
        if action == "ratify":
            claim_authority.ratify(memory_id)
        elif action == "reject":
            claim_authority.reject(memory_id, reason=reason)
        elif action == "contest":
            claim_authority.contest(memory_id, reason=reason)
        elif action == "release":
            claim_authority.release(memory_id, reason=reason)
        elif action == "reopen":
            claim_authority.reopen(memory_id)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"status": "ok", "memory_id": memory_id, "action": action}


@router.post("/memories/{memory_id}/ratify")
async def ratify_claim(memory_id: str):
    """User ratifies a system claim — grants Agency authority."""
    return _claim_action(memory_id, "ratify")


@router.post("/memories/{memory_id}/reject")
async def reject_claim(memory_id: str, body: dict | None = None):
    """User rejects a system claim."""
    return _claim_action(memory_id, "reject", body)


@router.post("/memories/{memory_id}/contest")
async def contest_claim(memory_id: str, body: dict | None = None):
    """User contests a system claim."""
    return _claim_action(memory_id, "contest", body)


@router.post("/memories/{memory_id}/release")
async def release_claim(memory_id: str, body: dict | None = None):
    """User releases influence of a ratified claim."""
    return _claim_action(memory_id, "release", body)


@router.post("/memories/{memory_id}/reopen")
async def reopen_claim(memory_id: str):
    """Reopen a rejected claim into contested state."""
    return _claim_action(memory_id, "reopen")


# --- User Profile endpoints (Memory v2) ---

@router.get("/profile")
async def get_profile():
    """Get the structured user profile."""
    return user_profile.get_profile()


@router.post("/profile/refresh")
async def refresh_profile():
    """Recalculate time decay and refresh profile confidence scores."""
    user_profile.refresh_all()
    return {"status": "ok", "profile": user_profile.get_profile()}
