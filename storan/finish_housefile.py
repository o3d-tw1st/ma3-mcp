#!/usr/bin/env python3
"""Finish Stora Teatern house file on WS1 via live MA3 MCP (file IPC).

Phases:
  plan       - offline generate command/Lua batches (no IPC)
  probe      - Version / CD Root / List Fixture
  status     - compare fixture count vs build-plan
  groups     - run generated group console batch (robust)
  labels     - run generated label console batch
  mvr-dimmer - print human checklist for MVR import (no SendKeys)

Use --dry-run to print actions without IPC mutation.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

STORAN_ROOT = Path(__file__).resolve().parent
if str(STORAN_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(STORAN_ROOT.parent))

from storan.generate_plan import main as generate_plan_main


def _robust():
    from storan.ma3_robust import batch, log, probe, safe_cmd, screenshot

    return batch, log, probe, safe_cmd, screenshot

DATA = STORAN_ROOT / "data"
EXPORTS = STORAN_ROOT / "exports"
GROUPS_FILE = EXPORTS / "groups_commands.txt"
LABELS_FILE = EXPORTS / "labels_commands.txt"


def load_plan_summary() -> dict:
    path = EXPORTS / "plan_summary.json"
    if not path.exists():
        generate_plan_main()
    return json.loads(path.read_text(encoding="utf-8"))


def load_commands(path: Path) -> list[str]:
    if not path.exists():
        generate_plan_main()
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def count_fixtures(list_fixture: str | None) -> int | None:
    if not list_fixture:
        return None
    lines = [ln for ln in list_fixture.splitlines() if ln.strip()]
    # Header/footer lines vary; count lines mentioning "Fixture"
    hits = [ln for ln in lines if "Fixture" in ln or ln.strip()[0:1].isdigit()]
    return len(hits) if hits else len(lines)


def phase_plan(_: argparse.Namespace) -> None:
    generate_plan_main()
    summary = load_plan_summary()
    print(f"plan ready: {json.dumps(summary, indent=2)}")


def phase_probe(args: argparse.Namespace) -> None:
    if args.dry_run:
        print("DRY-RUN: would probe Version, CD Root, List Fixture")
        return
    _, _, probe, _, _ = _robust()
    info = probe()
    print(json.dumps(info, indent=2))


def phase_status(args: argparse.Namespace) -> None:
    plan = json.loads((DATA / "build-plan.json").read_text(encoding="utf-8"))
    expected = plan.get("total_channels", 362)
    if args.dry_run:
        print(f"DRY-RUN: would List Fixture and compare to expected {expected}")
        return
    _, log, probe, _, screenshot = _robust()
    info = probe()
    got = count_fixtures(info.get("list_fixture"))
    print(f"fixture_lines={got} expected={expected}")
    if got is not None and got < expected - 5:
        log(f"PATCH INCOMPLETE: {got} vs {expected}")
        screenshot("patch_incomplete")


def run_command_file(path: Path, *, chunk: int, dry_run: bool) -> None:
    cmds = load_commands(path)
    if dry_run:
        print(f"DRY-RUN: would run {len(cmds)} commands from {path.name} (chunk={chunk})")
        for c in cmds[:10]:
            print(f"  {c}")
        if len(cmds) > 10:
            print(f"  ... +{len(cmds) - 10} more")
        return

    batch, log, _, _, _ = _robust()
    for i in range(0, len(cmds), chunk):
        chunk_cmds = cmds[i : i + chunk]
        log(f"batch {path.name} {i}-{i + len(chunk_cmds)} / {len(cmds)}")
        results = batch(chunk_cmds, stop_on_fail=True)
        if results and "command failed" in str(results[-1][1]):
            raise RuntimeError(f"batch stopped in {path.name} at index {i + len(results) - 1}")
        time.sleep(0.2)


def phase_groups(args: argparse.Namespace) -> None:
    load_plan_summary()
    run_command_file(GROUPS_FILE, chunk=args.chunk, dry_run=args.dry_run)


def phase_labels(args: argparse.Namespace) -> None:
    load_plan_summary()
    run_command_file(LABELS_FILE, chunk=args.chunk, dry_run=args.dry_run)


def phase_mvr_dimmer(args: argparse.Namespace) -> None:
    mvr = Path(args.mvr_path) if args.mvr_path else None
    checklist = STORAN_ROOT / "HUMAN_CHECKLIST.md"
    print("=== MVR DIMMER IMPORT (human required) ===")
    print(checklist.read_text(encoding="utf-8"))
    if mvr:
        print(f"\nMVR path: {mvr}")
        if not mvr.exists():
            print(f"WARNING: file not found at {mvr}")
    if args.dry_run:
        print("\nDRY-RUN: no Import command sent (dialog-bound).")
        return
    if not args.confirm_human:
        print("\nRe-run with --confirm-human after operator completes checklist.")
        return
    if not mvr or not mvr.exists():
        raise SystemExit("Set --mvr-path to the dimmer .mvr on WS1 before --confirm-human")

    _, _, probe, safe_cmd, screenshot = _robust()
    # Single Import attempt; operator must click Please in onPC UI.
    safe_cmd("CD Root", allow_fail=True)
    safe_cmd(f'Import "{mvr.as_posix()}" /nc', allow_fail=False)
    info = probe(require_ok=True)
    got = count_fixtures(info.get("list_fixture"))
    print(f"post-import fixture_lines={got}")
    screenshot("post_mvr_import")


PHASES = {
    "plan": phase_plan,
    "probe": phase_probe,
    "status": phase_status,
    "groups": phase_groups,
    "labels": phase_labels,
    "mvr-dimmer": phase_mvr_dimmer,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Stora Teatern house-file finish runner")
    parser.add_argument(
        "phase",
        choices=[*PHASES.keys(), "all"],
        help="phase to run (all = plan, probe, status, groups, labels; skips mvr-dimmer)",
    )
    parser.add_argument("--dry-run", action="store_true", help="print plan only, no IPC writes")
    parser.add_argument("--chunk", type=int, default=25, help="commands per IPC batch")
    parser.add_argument(
        "--mvr-path",
        help=r"WS1 path to dimmer MVR, e.g. C:\Users\o3d\...\dimmers.mvr",
    )
    parser.add_argument(
        "--confirm-human",
        action="store_true",
        help="operator completed MVR checklist; attempt Import once",
    )
    args = parser.parse_args()

    if args.phase == "all":
        _, log, _, _, _ = _robust()
        for name in ("plan", "probe", "status", "groups", "labels"):
            log(f"=== phase {name} ===")
            PHASES[name](args)
        print("\nSkipped mvr-dimmer in 'all'; run that phase separately with human present.")
        return

    PHASES[args.phase](args)


if __name__ == "__main__":
    main()
