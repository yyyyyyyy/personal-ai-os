"""Claim Suggestions — Agency path for Meaning Boundary G1.

Only ratified system claims may drive proactive notifications.
"""

from app.core.runtime.claim_authority import list_actionable_claims
from app.product.notifications import create_notification
from app.store import database

_MEMORY_ID_MARKER = "memory_id:"


def _already_notified_today(memory_id: str) -> bool:
    marker = f"{_MEMORY_ID_MARKER}{memory_id}"
    with database.db.get_db() as conn:
        row = conn.execute(
            """SELECT id FROM notifications
               WHERE type = 'claim_insight'
                 AND content LIKE ?
                 AND date(created_at) = date('now')
               LIMIT 1""",
            (f"%{marker}%",),
        ).fetchone()
    return row is not None


_MAX_PER_RUN = 5


def notify_ratified_claim_insights() -> int:
    """Create notifications for ratified claims not yet notified today.

    Skips already-notified claims before applying the per-run cap so ratified
    claims beyond the first page are not starved.

    Returns the number of notifications created.
    """
    created = 0
    for claim in list_actionable_claims(limit=500):
        if created >= _MAX_PER_RUN:
            break
        memory_id = claim["id"]
        if _already_notified_today(memory_id):
            continue
        content = claim.get("content", "")
        conf = float(claim.get("confidence") or 0.5)
        body = (
            f"{_MEMORY_ID_MARKER}{memory_id}\n"
            f"[已署名推断，置信度 {conf:.2f}] {content}"
        )
        create_notification(
            "claim_insight",
            f"已署名系统推断 ({memory_id})",
            body,
        )
        created += 1
    return created
