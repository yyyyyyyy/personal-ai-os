"""Centralized capability risk policy — auto_allow / needs_user / forbidden."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import settings


class CapabilityPolicy:
    def __init__(self):
        self._auto_allow: set[str] = set()
        self._needs_user: set[str] = set()
        self._forbidden: set[str] = set()
        self._external_auto_allow: set[str] = set()
        self._external_needs_user: set[str] = set()
        self._external_forbidden: set[str] = set()
        self._load()

    def _load(self) -> None:
        path = Path(settings.capability_policy_path)
        if not path.is_file():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        self._auto_allow = set(data.get("auto_allow", []))
        self._needs_user = set(data.get("needs_user", []))
        self._forbidden = set(data.get("forbidden", []))

    def register_external_tool(self, name: str, *, risk: str) -> None:
        """Register policy for a dynamically discovered external MCP tool."""
        self._external_auto_allow.discard(name)
        self._external_needs_user.discard(name)
        self._external_forbidden.discard(name)
        if risk == "forbidden":
            self._external_forbidden.add(name)
        elif risk == "high":
            self._external_needs_user.add(name)
        else:
            self._external_auto_allow.add(name)

    def clear_external_tools(self) -> None:
        self._external_auto_allow.clear()
        self._external_needs_user.clear()
        self._external_forbidden.clear()

    def all_registered_tools(self) -> set[str]:
        return (
            self._auto_allow
            | self._needs_user
            | self._forbidden
            | self._external_auto_allow
            | self._external_needs_user
            | self._external_forbidden
        )

    def risk_for(self, name: str, mcp_default_high: bool = False) -> str:
        """Return 'forbidden', 'high' (needs_user), or 'low' (auto_allow)."""
        if name in self._forbidden or name in self._external_forbidden:
            return "forbidden"
        if name in self._needs_user or name in self._external_needs_user:
            return "high"
        if name in self._auto_allow or name in self._external_auto_allow:
            return "low"
        return "high" if mcp_default_high else "low"

    def is_forbidden(self, name: str) -> bool:
        return self.risk_for(name) == "forbidden"


capability_policy = CapabilityPolicy()
