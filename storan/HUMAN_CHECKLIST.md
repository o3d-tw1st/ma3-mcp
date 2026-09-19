# Human checklist — dialog-bound MA3 steps (WS1 / onPC)

Automation stops here. **No SendKeys** — operator clicks in onPC.

## Before import

1. onPC show open: **2026 Base Stora Teatern** (or current house file).
2. MCP plugin running (`Menu → Plugins → MCP Server` started, or `start-onpc-with-mcp.ps1`).
3. IPC self-test green: `poetry run python storan/ma3_robust.py` → `Version` not `None`.
4. Close unrelated modal dialogs (patch wizard, backup prompts).

## Dimmer MVR import (~256 channels)

1. Note MVR path on WS1 (set `--mvr-path` on runner).
2. In onPC: **Setup → Patch → Import** (or run generated `Import "…" /nc` once via automation).
3. When MA3 shows **Please** / confirm: click **Please** (required — automation cannot).
4. If **User Canceled Command** or **Illegal object**: screenshot saved under `storan/exports/shots/`; read `C:\ProgramData\MA3\storan_lua_log.txt` if present.
5. After import: `poetry run python storan/finish_housefile.py status` — expect ~362 fixture lines when full patch is loaded.

## If Store Fixture was used manually

- **First** Store Fixture often works; **second+** may fail with **Cannot Create Object**.
- Prefer **MVR / Import Patch / one Lua batch** instead of repeated Store Fixture.

## After patch is loaded

Run (non-dry-run on WS1):

```powershell
poetry run python storan/finish_housefile.py groups
poetry run python storan/finish_housefile.py labels
```

Optional Lua one-shots (copy into show Lua component or execute via your plugin pool):

- `storan/exports/create_groups.lua`
- `storan/exports/apply_labels.lua`

## Still manual / TODO (from build-plan)

- Position palettes per pipe/boom
- Dimmer palettes Full / 50% / Out
- Color / gobo / beam defaults on movers and Lustr
