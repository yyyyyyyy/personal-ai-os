# MCP Mesh — External Capability Integration

> **Owner:** Runtime  
> **Status:** v0.9 — Active  
> **Depends on:** [RUNTIME_SPEC.md](RUNTIME_SPEC.md), [THREAT_MODEL.md](THREAT_MODEL.md)  

## 1. Design Goal

MCP Mesh connects the Runtime Kernel to real external MCP servers, converting the **23 builtin capabilities** into an extensible **N capabilities** mesh while **preserving the Kernel governance contract unchanged.**

Principle: external tools are indistinguishable from builtin tools after registration—same `invoke_capability`, same approval gating, same taint tracking, same event log audit trail.

---

## 2. Architecture

```text
                  FastAPI lifespan (main.py)
                          │
                          ▼
                ┌─────────────────────┐
                │   mcp_lifecycle     │  harness layer — safe to import from main
                │   start / stop      │  catches exceptions, never fails app startup
                └───────┬─────────────┘
                        │
          ┌─────────────┼─────────────┐
          │             ▼             │
          │    ┌───────────────┐      │
          │    │   MCPMesh     │      │  connection lifecycle
          │    │  (asyncio)    │      │  parallel + lazy connect
          │    └───┬───────┬───┘      │
          │        │       │          │
          │   ┌────▼──┐ ┌──▼──────┐   │
          │   │Server │ │Server   │   │  one `_ServerConnection`
          │   │Conn 1 │ │Conn 2   │   │  per external server
          │   └───┬───┘ └──┬──────┘   │
          │       │        │          │
          └───────┼────────┼────── harness goes here
                  │        │
 Kernel    ┌──────┴────────┴──────────┐
 Space     │        mcp_hub          │  registers ToolDef per discovered tool
           │  register_mesh_tools()  │  → capability_policy + taint
           └─────────────────────────┘
                        │
                        ▼
               invoke_capability()
               (approval / taint / event log / audit)
```

**Key rule:** Kernel only knows `ToolDef` names. Whether a tool came from a builtin Python server or an external npx process is transparent after registration.

---

## 3. Connection Lifecycle

### Startup (fast-path, non-blocking)

```
load mcp_config.json
  ├─ startup_connect=true    → parallel asyncio.gather (context7, tavily)
  └─ startup_connect=false   → asyncio.create_task background lazy connect
                                 (playwright, brave, github, notion)
```

- API is ready as soon as **the lighter startup servers** finish initialising.
- Lazy servers connect in the background. Their tools become available transparently later.
- Missing required credentials → server skipped entirely (logged).

### On-Demand Lazy Connection

```text
call_tool("playwright_browser_navigate", ...)
  → _ensure_server("playwright")
    → server not yet connected → connect now, register tools, return
```

If the first connect attempt fails, `call_tool` retries—failed connections preserve `_pending_configs` so the next invocation re‑attempts.

### Shutdown

```
cancel lazy task
  → unregister tools from mcp_hub
  → clear capability_policy external sets
  → clear taint dynamic sets (ingestion + write)
  → close each server connection (AsyncExitStack)
```

---

## 4. Governance Chain

Every external tool passes through the full Kernel approval chain:

### 4.1 Policy Mapping

```
mcp_config.json         capability_policy
──────────────         ─────────────────
policy_default=auto_allow → risk "low"
needs_user_tool/pattern   → risk "high"      → needs_user
forbidden                  → risk "forbidden"
```

Dynamic registration: `capability_policy.register_external_tool(name, risk)`.

### 4.2 Taint

```
mcp_config.json              taint
──────────────              ─────
ingestion_tool/pattern       → register_external_ingestion_tool(name)
requires_confirmation=true   → register_external_write_tool(name)
```

External write tools participate in taint escalation alongside the builtin `WRITE_CLASS_TOOLS` (`write_file`, `shell_exec`, `send_email`, …).

### 4.3 URL Safety

`browser_navigate` arguments are validated via the existing `url_safety.validate_http_url()` before invocation, covering the Playwright SSRF attack surface.

### 4.4 Audit Trail

All external tool invocations produce `CapabilityInvoked` / `ApprovalGranted` / `ApprovalRequested` events, indistinguishable from builtin tools in the event log.

---

## 5. Configuration

### `mcp_config.json`

Each external server entry describes:

| Field | Meaning |
|-------|---------|
| `name` | stable server id |
| `command` / `args` | stdio command (npx, uvx, …) |
| `startup_connect` | connect at app start or lazily |
| `enabled` | server toggle |
| `enabled_tools` | explicit tool allowlist; empty = expose all |
| `required_env` / `optional_env` | env var keys to resolve (from `Settings` object) |
| `policy_default` | auto_allow / needs_user / forbidden |
| `needs_user_tools/patterns` | which tools need user confirmation |
| `ingestion_tools/patterns` | which tools ingest untrusted content |
| `connect_timeout_seconds` / `call_timeout_seconds` | per-server timeouts |

### Environment Variables

```env
# Master switch
MCP_EXTERNAL_ENABLED=true             # false → no external MCP at all

# Server filter — comma-separated or * for all in config
MCP_SERVERS_ENABLED=context7,tavily   # or *, or playwright

# Optional credentials (servers skip if missing)
BRAVE_API_KEY=                        # Brave Search (2000 queries/mo free)
CONTEXT7_API_KEY=                     # Context7 docs lookup (optional)
GITHUB_PERSONAL_ACCESS_TOKEN=         # GitHub PR/Issue/Code
TAVILY_API_KEY=                       # Tavily research search
NOTION_TOKEN=                         # Notion workspace
```

### Filtering at Runtime

- `MCP_SERVERS_ENABLED=context7,tavily` — only load these servers from the config.
- `MCP_SERVERS_ENABLED=*` (default) — load all.
- `MCP_EXTERNAL_ENABLED=false` — skip the entire mesh.

---

## 6. Tool Naming Convention

```
{server_name}_{normalized_tool_name}

context7_query_docs
playwright_browser_navigate
brave_brave_web_search
github_search_code
tavily_tavily_search
notion_API_post_search
```

Special characters in tool names (hyphens, …) are replaced with `_`. Collision detection: if `{registration_prefix}_{tool_name}` is already taken, falls back to `{server_name}_{tool_name}`.

---

## 7. Exposed Tools (Current)

| Server | Startup | Exposed | Risk | Write |
|--------|---------|---------|------|-------|
| context7 | ✅ startup | 2 (query-docs, resolve-library-id) | low — ingestion | — |
| tavily | ✅ startup | 2 (search, extract) | low — ingestion | — |
| playwright | lazy | 7 (navigate, snapshot, screenshot, click, type, tabs, close) | low / high | click, type |
| brave | lazy | 1 (web_search) | low — ingestion | — |
| github | lazy | 8 (search/repos/code/issues, PR read) | low — ingestion | — |
| notion | lazy | 4 (search, read page, blocks, query) | low — ingestion | — |

**Total builtin tools:** 23 | **Max external tools:** 24 | **Max total:** 47

All write-class tools participate in taint escalation (external content → approve before write).

---

## 8. Error Handling

| Scenario | Behaviour |
|----------|-----------|
| config JSON missing or malformed | mesh skipped, log warning |
| npx not available on PATH | server connection fails, log exception |
| required API key missing | server skipped (logged at INFO) |
| server crashes after successful connect | `call_tool` returns error; lazy task will not restart |
| tool not registered yet (lazy connect still in progress) | `call_tool` triggers on-demand connect |
| call_tool on unregistered name | returns JSON error to LLM, Kernel handles normally |

---

## 9. Testing

```
174 passed, 1 skipped
```

| Layer | Coverage |
|-------|----------|
| config parsing, policy patterns | `test_mcp_config.py` |
| URL validation (SSRF) | `test_mcp_mesh.py` |
| taint escalation for external write tools | `test_mcp_mesh.py` |
| DDG HTML search parsing | `test_web_search_html.py` |
| builtin tools policy contract | `test_capability_approval.py`, `test_taint.py` |
| live MCP stdio integration | pending (requires Docker or npx mock) |
| lazy connect / parallel connect | pending |

---

## 10. Related Docs

- [RUNTIME_SPEC.md](RUNTIME_SPEC.md) — Kernel primitives, governance charter
- [THREAT_MODEL.md](THREAT_MODEL.md) — SSRF, prompt injection, taint
- [ONBOARDING.md](ONBOARDING.md) — Quick-start for first-time users
- [CONTRIBUTING.md](CONTRIBUTING.md) — Tool registration checklist
