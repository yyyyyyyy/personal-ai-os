"""System API — health checks, LLM providers, data sovereignty, and system info."""

import secrets

from fastapi import APIRouter, HTTPException, Request

from app.api.models import ExportRequest, ImportRequest
from app.config import settings
from app.core.agents.llm_router import llm_router
from app.core.startup_health import sanitize_startup_for_public
from app.product.digital_legacy import digital_legacy

router = APIRouter(prefix="/api/system", tags=["system"])


def _request_has_valid_auth(request: Request) -> bool:
    expected = settings.auth_token
    if not expected:
        return False
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False
    return secrets.compare_digest(auth_header[7:], expected)

EXPORT_CONFIRM = "EXPORT_ALL_DATA"
DESTROY_CONFIRM = "DESTROY_ALL_DATA"
IMPORT_CONFIRM = "DESTROY_AND_IMPORT"


@router.get("/health")
async def health_check(request: Request):
    """Health check endpoint with startup diagnostics."""
    startup = getattr(request.app.state, "startup_health", None)
    if startup and not _request_has_valid_auth(request):
        startup = sanitize_startup_for_public(startup)
    return {
        "status": startup.get("status", "ok") if startup else "ok",
        "service": "personal-ai-runtime",
        "version": "0.9.0",
        "auth_required": bool(settings.auth_token),
        "startup": startup,
    }


@router.get("/validation-metrics")
async def validation_metrics():
    """User validation cohort metrics (see docs/USER_VALIDATION.md)."""
    from app.product.validation_metrics import get_validation_metrics

    return get_validation_metrics()


@router.get("/llm-providers")
async def list_llm_providers():
    """List all configured LLM providers."""
    return {
        "providers": llm_router.list_providers(),
        "default": llm_router.get_default_model(),
    }


@router.get("/info")
async def system_info():
    """Get system information."""
    from app.core.runtime.kernel_instance import kernel
    from app.store.database import db

    counts = kernel.table_counts(("conversations", "messages", "event_log"))
    with db.get_db() as conn:
        legacy_event_count = conn.execute(
            "SELECT COUNT(*) as c FROM events"
        ).fetchone()["c"]

    goal_count = len(kernel.query_state("goals", limit=10000))
    mem_count = len(kernel.query_state("memories", limit=10000))

    return {
        "conversations": counts["conversations"],
        "messages": counts["messages"],
        "goals": goal_count,
        "event_log": counts["event_log"],
        "events": legacy_event_count,
        "memories": mem_count,
        "llm_providers": len(llm_router.list_providers()),
    }


@router.get("/mcp-status")
async def mcp_status():
    """Return external MCP server connection status."""
    from app.core.harness.mcp_mesh import mcp_mesh

    return mcp_mesh.get_server_status()


@router.post("/export")
async def export_all_data(body: ExportRequest | None = None):
    """Export complete personal data snapshot as JSON."""
    payload = body or ExportRequest()
    if payload.confirm != EXPORT_CONFIRM:
        raise HTTPException(
            status_code=400,
            detail=f"Set confirm='{EXPORT_CONFIRM}' to export",
        )
    return digital_legacy.export_all()


@router.post("/import")
async def import_all_data(body: ImportRequest):
    """Import personal data snapshot. Requires confirm code when not read_only."""
    read_only = body.read_only
    if not read_only and body.confirm != IMPORT_CONFIRM:
        raise HTTPException(
            status_code=400,
            detail=f"Set confirm='{IMPORT_CONFIRM}' for write import",
        )
    return digital_legacy.import_all(body.data, read_only=read_only)


@router.delete("/data")
async def destroy_all_data(body: dict):
    """Destroy all local data. Requires confirm code."""
    if body.get("confirm") != DESTROY_CONFIRM:
        raise HTTPException(status_code=400, detail=f"confirm must be '{DESTROY_CONFIRM}'")
    return digital_legacy.destroy_all()
