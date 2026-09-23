# Stora Teatern — house file finish (WS1)

Automation package for Oliver's **Storan-GMa3** fork. Runs on **WS1** against live **NetBird HTTP MCP** or local file IPC. This cloud repo cannot reach NetBird; scripts are shipped for WS1 execution.

## Quick start (WS1)

```powershell
cd C:\Users\o3d\Development\Storan-GMa3\MA3-MCP
git pull
.\storan\scripts\install-windows.ps1
.\storan\scripts\start-onpc-with-mcp.ps1
.\storan\scripts\self-test-ipc.ps1
```

### Reboot without human Menu → Plugins

1. `install-windows.ps1` deploys `mcp_server.lua` + `MCP Server.xml` to **both** `lib_plugins\mcp_server` and `gma3_library\datapools\plugins\mcp_server`.
2. `start-onpc-with-mcp.ps1` writes `go` to `C:\ProgramData\MA3\mcp_autoload.txt`, starts `run_netbird_http.py` (NetBird HTTP bridge on port 8765 by default), launches onPC with `RUNPLUGIN="MCP Server.xml"-1`, and waits for `mcp_autoload.txt` = `done`.
3. `self-test-ipc.ps1` confirms `Version` via file IPC.

NetBird HTTP bridge uses the same IPC dir (`MA3_IPC_DIR`, default `C:\ProgramData\MA3`). Override port with `MA3_HTTP_PORT`.

## Dry-run / offline plan (no onPC required)

```powershell
poetry run python storan/finish_housefile.py plan --dry-run
poetry run python storan/generate_plan.py
```

Outputs under `storan/exports/`:

| File | Purpose |
|------|---------|
| `groups_commands.txt` | Console batch: Store Group per build-plan |
| `labels_commands.txt` | Label Fixture from patch CSV |
| `create_groups.lua` | Lua one-shot (alternative to console batch) |
| `apply_labels.lua` | Lua one-shot labels |
| `plan_summary.json` | Counts and paths |

## Live phases (onPC + plugin required)

```powershell
poetry run python storan/finish_housefile.py probe
poetry run python storan/finish_housefile.py status
poetry run python storan/finish_housefile.py groups
poetry run python storan/finish_housefile.py labels
```

Full non-MVR pass:

```powershell
poetry run python storan/finish_housefile.py all
```

### MVR dimmer import (human required)

See **`HUMAN_CHECKLIST.md`**. Runner does **not** use SendKeys.

```powershell
poetry run python storan/finish_housefile.py mvr-dimmer --mvr-path "C:\path\to\dimmers.mvr"
# Operator clicks Please in onPC, then:
poetry run python storan/finish_housefile.py mvr-dimmer --mvr-path "C:\path\to\dimmers.mvr" --confirm-human
```

## Known blockers (designed around)

| Issue | Mitigation |
|-------|------------|
| Store Fixture 2+ → Cannot Create Object | Prefer **MVR import** / one Lua batch; avoid repeated Store Fixture |
| Lua AddFixtures returns nil | Verify with `List Fixture` / `status` phase; screenshot on stall |
| MVR Import → User Canceled / Illegal object | **Human Please** — single checklist, one Import attempt |
| No SendKeys | Screenshots + logs only |

## Robust helper

`storan/ma3_robust.py` — `probe`, `safe_cmd`, `batch`, `screenshot` on stall.

- Log: `storan/exports/mcp_session.log` (override `STORAN_LOG`)
- Shots: `storan/exports/shots/`
- Fail tokens: Illegal object, Cannot Create Object, User Canceled Command, …

## Data

- `data/patch-channels.csv` — ~362 channels (Eos patch export)
- `data/build-plan.json` — fixture types, groups, palette TODO

## Config

Copy `storan/.env.example` → `storan/.env` or use repo `.env` (`MA3_IPC_DIR`, `MA3_PLUGIN_DIR`, `GMA3_BIN`, `STORAN_MVR_DIMMER`).

## What still needs a human

1. MVR / patch import **Please** dialog
2. Fixture library personality mismatches (Sparx pixel disabled, etc.)
3. Palettes listed in `build-plan.json` → `palettes_todo`
