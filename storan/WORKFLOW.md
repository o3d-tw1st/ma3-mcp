# Robust grandMA3 MCP workflow

Oliver requirement: do not spray illegal commands; read CLI/status; verify visually when stuck; work in efficient batches.

## Before any mutation

1. `Version` / IPC probe must return OK.
2. Know destination: `CD Root` then navigate deliberately (`ShowData` → `LivePatch` → `Stage` → `1` → `Fixtures` for patch adds).
3. Prefer one Lua/script batch over dozens of single MCP calls.
4. Use helper: `storan/ma3_robust.py` (`safe_cmd`, `batch`, `screenshot`, `probe`).

## When a command fails

Illegal object / Not allowed / Cannot Create Object / User Canceled Command:

1. Stop the batch.
2. Screenshot onPC (`ma3_robust.screenshot`).
3. Read `C:\ProgramData\MA3\storan_lua_log.txt` and `storan/exports/mcp_session.log`.
4. Fix mode/destination/dialog — do not retry the same illegal command blindly.
5. Dialog-bound actions (MVR Import confirm) need a human Please/click — ask once, prepare files.

## Efficiency

- Generate MVR/macro/CSV offline; one Import beats 300 Store calls.
- Log once per batch, not per chatter message.
- Milestone updates only when state changes.
