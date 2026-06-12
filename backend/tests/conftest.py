"""Global pytest configuration."""

import os

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("MCP_EXTERNAL_ENABLED", "false")

# Re-read settings after env defaults so tests see MCP_EXTERNAL_ENABLED=false.
from app.config import reset_settings

reset_settings()
