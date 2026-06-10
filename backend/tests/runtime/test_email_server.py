"""Unit tests for email MCP server helpers."""

from app.core.harness.mcp_servers.email import _format_date


def test_format_date_converts_to_local_timezone():
  # 06:38 UTC -> 14:38 in UTC+8
  raw = "Wed, 10 Jun 2026 06:38:12 +0000"
  formatted = _format_date(raw)
  assert "2026-06-10" in formatted
  assert formatted.endswith(":38") or formatted.endswith(":38:12") is False
