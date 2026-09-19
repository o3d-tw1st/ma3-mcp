"""Robust MA3 MCP helper: probe, safe_cmd, screenshot on stall, batched ops.

Designed for WS1 / onPC driving via file IPC (local or NetBird HTTP bridge).
Paths are configurable via STORAN_* env vars or storan/.env.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Repo root on sys.path so `ma3_mcp` imports work when run as a script.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / ".env")
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from ma3_mcp.ma3_comm import cmd as raw_cmd

STORAN_ROOT = Path(__file__).resolve().parent
LOG = Path(os.environ.get("STORAN_LOG", STORAN_ROOT / "exports" / "mcp_session.log"))
SHOT_DIR = Path(os.environ.get("STORAN_SHOT_DIR", STORAN_ROOT / "exports" / "shots"))
LUA_LOG = Path(os.environ.get("STORAN_LUA_LOG", "C:/ProgramData/MA3/storan_lua_log.txt"))

FAIL_TOKENS = (
    "Illegal object",
    "Not allowed",
    "Cannot Create Object",
    "Failed",
    "Illegal source list",
    "User Canceled Command",
    "Illegal file name",
)


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
    print(line)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def tail_lua_log(lines: int = 40) -> str:
    if not LUA_LOG.exists():
        return f"(no lua log at {LUA_LOG})"
    text = LUA_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(text[-lines:])


def screenshot(tag: str) -> Path | None:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    out = SHOT_DIR / f"{datetime.now().strftime('%H%M%S')}_{tag}.png"
    out_ps = str(out).replace("'", "''")
    ps = f"""
Add-Type -AssemblyName System.Drawing
$p = Get-Process app_gma3 -ErrorAction SilentlyContinue | Where-Object {{ $_.MainWindowTitle -match 'GMA3App' }} | Select-Object -First 1
if (-not $p) {{ $p = Get-Process app_gma3 -ErrorAction SilentlyContinue | Select-Object -First 1 }}
if (-not $p) {{ exit 2 }}
Add-Type @'
using System; using System.Runtime.InteropServices;
public class W {{
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
  [StructLayout(LayoutKind.Sequential)] public struct RECT {{ public int L; public int T; public int R; public int B; }}
}}
'@
$r = New-Object W+RECT
[void][W]::GetWindowRect($p.MainWindowHandle, [ref]$r)
$w = [Math]::Max(1, $r.R - $r.L); $h = [Math]::Max(1, $r.B - $r.T)
$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.L, $r.T, 0, 0, $bmp.Size)
$bmp.Save('{out_ps}')
"""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            check=False,
            timeout=25,
        )
        if out.exists() and out.stat().st_size > 0:
            log(f"screenshot OK {out}")
            return out
        log("screenshot missing/empty")
    except Exception as exc:
        log(f"screenshot fail {exc}")
    return None


def probe(*, require_ok: bool = True) -> dict:
    info = {
        "version": raw_cmd("Version"),
        "cd_root": raw_cmd("CD Root"),
        "list_fixture": raw_cmd("List Fixture"),
    }
    log(f"probe {info}")
    if require_ok and info["version"] is None:
        screenshot("ipc_dead")
        raise RuntimeError("IPC dead — Version returned None")
    return info


def safe_cmd(command: str, *, allow_fail: bool = False) -> str | None:
    c = command.strip()
    log(f">>> {c}")
    r = raw_cmd(c)
    log(f"<<< {r!r}")
    failed = r is None or any(tok.lower() in str(r).lower() for tok in FAIL_TOKENS)
    if failed and not allow_fail:
        log(f"STALL on {c!r}")
        log(f"lua tail:\n{tail_lua_log()}")
        screenshot("stall")
        raise RuntimeError(f"command failed {c!r} -> {r!r}")
    return r


def batch(
    commands: list[str],
    *,
    stop_on_fail: bool = True,
    probe_first: bool = True,
) -> list[tuple[str, str | None]]:
    if probe_first:
        probe()
    out: list[tuple[str, str | None]] = []
    for c in commands:
        try:
            r = safe_cmd(c, allow_fail=not stop_on_fail)
            out.append((c, r))
        except RuntimeError as exc:
            out.append((c, str(exc)))
            if stop_on_fail:
                break
            screenshot("batch_continue")
    return out


def ensure_root() -> None:
    safe_cmd("CD Root", allow_fail=True)


if __name__ == "__main__":
    log("self-test start")
    print(probe())
    print(batch(["CD Root", "Version", "List Fixture"], stop_on_fail=False))
    screenshot("selftest")
    log("self-test done")
