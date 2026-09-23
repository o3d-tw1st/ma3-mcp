# Human checklist — dialog-bound MA3 steps (WS1 / onPC)

Automation stops here. **No SendKeys** — operator clicks in onPC.

## Reboot onPC without Menu → Plugins (one-time setup)

MA3 2.3.2 has no UserPlugin Autostart. Cold-start uses `RUNPLUGIN="MCP Server.xml"-1` plus a one-shot autoload file.

1. Deploy plugin to both `lib_plugins` and `gma3_library` (install script does this):
   ```powershell
   .\storan\scripts\install-windows.ps1
   ```
2. After reboot, launch onPC + MCP automatically:
   ```powershell
   .\storan\scripts\start-onpc-with-mcp.ps1
   ```
   This writes `C:\ProgramData\MA3\mcp_autoload.txt` = `go`, starts the NetBird HTTP bridge (if `run_netbird_http.py` is present), starts onPC with `RUNPLUGIN`, and watches until the plugin writes `done`.
3. Verify IPC:
   ```powershell
   .\storan\scripts\self-test-ipc.ps1
   ```
   Expect `Version` (not `None`) from `ma3_comm` / `ma3_robust`.

**Manual alternative:** write `go` to `C:\ProgramData\MA3\mcp_autoload.txt`, start onPC with `RUNPLUGIN="MCP Server.xml"-1`, or run `ReloadAllPlugins` then `Call Plugin "MCP Server"` if onPC is already open.

## Before import

1. onPC show open: **2026 Base Stora Teatern** (or current house file).
2. MCP plugin running (`start-onpc-with-mcp.ps1` or manual start above).
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
