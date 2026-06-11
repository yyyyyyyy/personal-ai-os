"""Notification generation utilities."""

import uuid
from datetime import UTC, datetime

from app.store import database


def find_notification(notif_type: str, title: str) -> dict | None:
    """Return an existing notification with the same type and title, if any."""
    with database.db.get_db() as conn:
        row = conn.execute(
            "SELECT id, type, title, content, created_at FROM notifications "
            "WHERE type = ? AND title = ? LIMIT 1",
            (notif_type, title),
        ).fetchone()
    return dict(row) if row else None


def create_notification(notif_type: str, title: str, content: str) -> dict:
    """Create a notification and return it (idempotent by type + title)."""
    existing = find_notification(notif_type, title)
    if existing:
        return existing

    nid = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    with database.db.get_db() as conn:
        conn.execute(
            "INSERT INTO notifications (id, type, title, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (nid, notif_type, title, content, now),
        )
    return {"id": nid, "type": notif_type, "title": title, "content": content, "created_at": now}
