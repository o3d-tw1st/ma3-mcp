# Multi-agent sharing on one MA3 plugin

One Lua plugin instance on WS1 serves all agent transports. Do not deploy duplicate plugin pool copies — a single plugin polls IPC and executes console commands.

## Segment 1 (PR #2) — single-slot IPC

**IPC:** `mcp_command.txt` / `mcp_response.txt` (one command at a time).

| Client | Transport | Concurrent with others? |
|--------|-----------|-------------------------|
| **Cursor IDE** | stdio MCP → file IPC | OK alone on WS1 |
| **Scripts / self-test** | direct file IPC (`ma3_robust.py`, `self-test-ipc.ps1`) | OK when no MCP server is writing |
| **Remote HTTP** | NetBird `:8765` POST `/cmd` | OK for single commands; shares same slot |
| **Grok Bot** | SSE MCP (house fork) | **Must not run concurrently** with Cursor stdio on the same plugin |

**Rule:** Only one writer to `mcp_command.txt` at a time. Cursor IDE stdio MCP is safe for local development. Grok Bot (or any second stdio/SSE MCP session) must not run at the same time as Cursor on the same plugin instance — commands can stomp each other.

**Autoload:** `start-onpc-with-mcp.ps1` writes `mcp_autoload.txt=go`, launches onPC with `RUNPLUGIN`, and waits for `done` — no manual Menu → Plugins click required.

## Segment 2 target — queue IPC

**IPC:** `mcp_queue.jsonl` + `outbox/{id}.json` (locked ticket queue).

| Client | Transport | Concurrent? |
|--------|-----------|-------------|
| **Cursor IDE** | stdio MCP → queue | Yes |
| **Grok Bot** | NetBird SSE `:8766` → queue | Yes |
| **Remote HTTP** | optional adapter → queue | Yes |

**Rule:** One plugin, many agents. Each ticket gets a unique ID; the plugin drains the queue and writes per-ticket outbox files. Failed tickets do not block the queue.

**Files (target):**

| File | Purpose |
|------|---------|
| `mcp_queue.jsonl` | Locked ticket queue |
| `mcp_queue.lock` | Exclusive lock for queue rewrite |
| `outbox/{id}.json` | Per-ticket callback |
| `mcp_alive.txt` | Plugin heartbeat |

See [transport-runbook.md](transport-runbook.md) for port and client details.

## WS1 smoke results (2026-09-23)

Branch `cursor/mcp-autoload-start-script-adee` — **all criteria PASS** on WS1:

| Criterion | Result |
|-----------|--------|
| No human plugin menu click | PASS — autoload `go` → `done` in ~16s |
| `start-onpc-with-mcp.ps1` completes | PASS |
| `self-test-ipc.ps1` (Version, CD Root, List Fixture) | PASS |
| HTTP `:8765` `/health` + POST `/cmd` Version | PASS (after launcher health-check fix in `18e12d9`) |
| Plugin files match repo in both deploy targets | PASS |

**Fix included in PR:** launcher now probes `GET /health` for `{"status":"ok"}` before skipping bridge startup — avoids false positive when another process occupies port 8765.
