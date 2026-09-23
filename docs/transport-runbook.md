# MA3 MCP transport runbook

How each client path reaches the single Lua plugin on WS1. **Required** paths must work for segment-1 acceptance; **optional** paths are staged or legacy.

## Summary matrix

| Transport | Port / channel | Client | IPC layer | Status in git SoT (PR #2) | Required? |
|-----------|----------------|--------|-----------|---------------------------|-----------|
| **stdio MCP** | subprocess pipe | Cursor IDE (local WS1) | `mcp_command.txt` → plugin | Implemented | **Required** (local dev) |
| **File IPC direct** | none (filesystem) | `ma3_robust.py`, scripts, tests | `mcp_command.txt` → plugin | Implemented | **Required** (self-test) |
| **NetBird HTTP** | `:8765` POST `/cmd` | Remote HTTP clients | `mcp_command.txt` via `run_netbird_http.py` | Implemented (PR #2) | **Required** (remote probe) |
| **NetBird SSE MCP** | `:8766` `/sse` | Grok Bot, remote MCP clients | `mcp_queue.jsonl` via FastMCP SSE | House fork only | **Target** (segment 2+) |
| **Legacy SSE** | `:8766` | House `start-onpc-with-mcp.ps1` | Queue IPC | House fork only | Deprecated naming; align to queue |
| **OSC `/cmd`** | `127.0.0.1:8000` | Deploy reload, emergency Call | Console commands | Optional helper in deploy | Optional |

## 1. Cursor IDE — stdio MCP (required, local)

**Config** (`.vscode/settings.json` or Cursor MCP settings):

```json
{
  "mcpServers": {
    "grandMA3": {
      "command": "poetry",
      "args": ["run", "python", "-m", "ma3_mcp.server"],
      "cwd": "C:\\Users\\o3d\\Development\\ma3-mcp"
    }
  }
}
```

**Path:** Cursor spawns `ma3_mcp.server` → `ma3_comm.send()` → writes `C:\ProgramData\MA3\mcp_command.txt` → Lua plugin polls → writes `mcp_response.txt`.

**Prerequisites:**

- onPC running with MCP plugin active (`start-onpc-with-mcp.ps1` or manual RUNPLUGIN).
- `poetry install` in repo root.

**Limitation (PR #2):** single-slot command file. Two simultaneous stdio MCP processes can stomp each other. Mitigation: segment 2 queue IPC.

## 2. File IPC — direct Python (required, diagnostics)

**Use for:** smoke tests, `storan/ma3_robust.py`, one-off probes.

```powershell
poetry run python -c "from ma3_mcp.ma3_comm import cmd; print(cmd('Version'))"
# or
.\storan\scripts\self-test-ipc.ps1
```

**Files:**

| File | Direction | Format |
|------|-----------|--------|
| `mcp_command.txt` | Python → Lua | `{request_id}:{command}` |
| `mcp_response.txt` | Lua → Python | `{request_id}:{response}` |
| `mcp_autoload.txt` | Launcher ↔ Lua | `go` (launcher) → `done` (plugin) |

**Env overrides:** `MA3_IPC_DIR`, `MA3_COMMAND_FILE`, `MA3_RESPONSE_FILE`.

## 3. NetBird HTTP bridge (required for remote, PR #2)

**Entry:** `run_netbird_http.py` (also `poetry run run-netbird-http`).

| Endpoint | Method | Body | Response |
|----------|--------|------|----------|
| `/health` | GET | — | `{"status":"ok"}` |
| `/cmd` | POST | `{"command":"Version","timeout":5.0}` | `{"response":"..."}` |

**Defaults:** `MA3_HTTP_HOST=0.0.0.0`, `MA3_HTTP_PORT=8765`.

**Started by:** `storan/scripts/start-onpc-with-mcp.ps1` (if not already listening).

**Use when:** a remote agent has HTTP access over NetBird but cannot spawn local stdio. Still uses legacy single-slot IPC underneath.

**Not the same as:** house fork SSE MCP on `:8766` (full MCP protocol, tool listing, resources).

## 4. NetBird SSE MCP (target, house fork — optional until ported)

**House implementation** (`Storan-GMa3/MA3-MCP/run_netbird_http.py`):

```python
mcp.settings.host = "100.99.192.109"
mcp.settings.port = 8766
mcp.run(transport="sse")
```

**Path:** Remote MCP client → SSE → `ma3_mcp.server` → `mcp_queue.jsonl` → plugin `drainQueue()` → `outbox/{id}.json`.

**Why it matters:** Grok Bot and cloud agents expect MCP over HTTP/SSE, not raw POST `/cmd`. Queue IPC allows concurrent agents.

**Status:** Not in git SoT. Port in segment 2 after cold-start segment merges.

## 5. Multi-agent queue IPC (target — optional until ported)

**Files** (house fork; target architecture):

| File | Purpose |
|------|---------|
| `mcp_queue.jsonl` | Locked ticket queue (`id\x1fagent\x1fcmd...`) |
| `mcp_queue.lock` | Exclusive lock for queue rewrite |
| `outbox/{id}.json` | Per-ticket `{"ok","result","error"}` callback |
| `mcp_alive.txt` | Plugin heartbeat |
| `mcp_status.txt` | Last command status |

**Client env:** `MA3_AGENT_ID` (or auto-generated).

**Rule:** One plugin, many agents. Failed ticket writes its outbox; plugin drains next. Do not add extra plugin pool copies.

**Backward compat:** Legacy `mcp_command.txt` poller can coexist during migration; new clients should use queue only.

## 6. OSC reload (optional)

`deploy-windows.ps1` sends OSC to `127.0.0.1:8000` for `ReloadAllPlugins` / `Call Plugin`. Useful for hot reload during dev; not the primary agent transport.

## Cold-start sequence (all transports)

Regardless of transport, the plugin must be running first:

1. `install-windows.ps1` — deploy Lua + XML to both plugin paths.
2. `start-onpc-with-mcp.ps1`:
   - Write `mcp_autoload.txt` = `go`
   - Start NetBird HTTP bridge (port 8765)
   - Launch `app_gma3.exe RUNPLUGIN="MCP Server.xml"-1`
   - Wait for `mcp_autoload.txt` = `done`
3. `self-test-ipc.ps1` — `Version` probe.

## Choosing a transport

| Scenario | Use |
|----------|-----|
| Cursor on WS1 | stdio MCP |
| Quick probe / CI script | file IPC (`ma3_robust.py`) |
| Remote script, single command | HTTP `:8765` `/cmd` |
| Grok Bot / remote MCP session | SSE `:8766` + queue (after segment 2) |
| Two agents at once | queue IPC only (segment 2) |

## Known mismatches (as of PR #2)

| Issue | Git SoT | House live |
|-------|---------|------------|
| Remote port | 8765 HTTP | 8766 SSE |
| IPC | `mcp_command.txt` | `mcp_queue.jsonl` |
| Launcher script | `ma3-mcp/storan/scripts/start-onpc-with-mcp.ps1` | `Storan-GMa3/start-onpc-with-mcp.ps1` |

Reconcile in segment 2; do not run both launchers against one onPC without understanding port conflicts.
