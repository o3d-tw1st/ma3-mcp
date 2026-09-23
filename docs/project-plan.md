# MA3 MCP — project plan (segment milestones)

One-page overview for the WS1 Storan integration. Git source of truth: [ma3-mcp](https://github.com/o3d-tw1st/ma3-mcp).

## Goal

AI agents (Cursor, Grok Bot, remote scripts) control grandMA3 on WS1 through a single Lua plugin, with reliable cold-start and documented transports.

## Milestones

| Segment | PR / scope | IPC | Status |
|---------|------------|-----|--------|
| **1 — Cold start + single agent** | [PR #2](https://github.com/o3d-tw1st/ma3-mcp/pull/2) | `mcp_command.txt` | WS1 smoke **PASS** |
| **2 — Multi-agent** | TBD | `mcp_queue.jsonl` + `outbox/` | Target |

### Segment 1 deliverables (PR #2)

- `storan/scripts/install-windows.ps1` — deploy plugin to both MA3 paths
- `storan/scripts/start-onpc-with-mcp.ps1` — autoload handshake, NetBird HTTP bridge on `:8765`
- `run_netbird_http.py` — remote `POST /cmd` over NetBird
- `storan/scripts/self-test-ipc.ps1` — file IPC smoke test
- Launcher health-check fix (`18e12d9`) — verify MA3 bridge on 8765, not just port occupancy

**Acceptance:** autoload without manual plugin click; self-test OK; HTTP `/cmd` Version OK.

### Segment 2 deliverables (planned)

- Port queue IPC from house fork (`mcp_queue.jsonl`, `outbox/`)
- NetBird SSE MCP on `:8766` for Grok Bot
- Cursor + Grok Bot safe on one plugin concurrently

## Documentation

| Doc | Contents |
|-----|----------|
| [transport-runbook.md](transport-runbook.md) | Per-client transport paths, ports, cold-start sequence |
| [multi-agent-sharing.md](multi-agent-sharing.md) | Segment 1 vs 2 IPC rules, concurrency, WS1 smoke summary |

## Quick start (segment 1)

```powershell
cd C:\Users\o3d\Development\ma3-mcp
.\storan\scripts\install-windows.ps1
.\storan\scripts\start-onpc-with-mcp.ps1
.\storan\scripts\self-test-ipc.ps1
```

Cursor MCP: see transport runbook §1 (stdio via `ma3_mcp.server`).
