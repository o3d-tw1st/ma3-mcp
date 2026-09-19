"""Offline plan generator: groups, labels, and Lua snippets for Stora Teatern."""
from __future__ import annotations

import csv
import json
from pathlib import Path

STORAN_ROOT = Path(__file__).resolve().parent
DATA = STORAN_ROOT / "data"
EXPORTS = STORAN_ROOT / "exports"


def compress_channels(channels: list[int]) -> str:
    """Turn sorted fixture IDs into MA3 selection (ranges + singles)."""
    if not channels:
        return ""
    parts: list[str] = []
    start = prev = channels[0]
    for ch in channels[1:]:
        if ch == prev + 1:
            prev = ch
            continue
        parts.append(f"{start} Thru {prev}" if start != prev else str(start))
        start = prev = ch
    parts.append(f"{start} Thru {prev}" if start != prev else str(start))
    return " + ".join(parts)


def load_patch_csv() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with (DATA / "patch-channels.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def load_build_plan() -> dict:
    return json.loads((DATA / "build-plan.json").read_text(encoding="utf-8"))


def fixture_label_commands(rows: list[dict[str, str]]) -> list[str]:
    cmds: list[str] = []
    for row in rows:
        label = (row.get("label") or "").strip()
        if not label:
            continue
        chan = row["chan"].strip()
        ftype = row.get("fixture_type", "").strip()
        text = f"{label} {ftype}".strip() if ftype else label
        cmds.append(f'Label Fixture {chan} "{text}"')
    return cmds


def group_commands(plan: dict) -> list[str]:
    cmds = ["CD Root"]
    for name, channels in plan.get("groups", {}).items():
        sel = compress_channels(sorted(int(c) for c in channels))
        if not sel:
            continue
        safe = name.replace('"', '\\"')
        cmds.extend(
            [
                f"ClearAll",
                f"Fixture {sel}",
                f'Store Group "{safe}" /o /nc',
            ]
        )
    return cmds


def write_lua_groups(plan: dict, out: Path) -> None:
    lines = [
        "-- Generated group creator for Stora Teatern (run inside show via Lua plugin pool)",
        "local log = Printf",
        'local function storan_log(m) log("STORAN: " .. tostring(m)) end',
        "",
    ]
    for name, channels in plan.get("groups", {}).items():
        ids = ", ".join(str(int(c)) for c in sorted(channels))
        safe = name.replace('"', '\\"')
        lines.extend(
            [
                f'storan_log("Group {safe}")',
                "ClearAll()",
                f"local ids = {{{ids}}}",
                "for _, id in ipairs(ids) do",
                "  local fx = GetSubfixture(id)",
                "  if fx then fx:Select(true) end",
                "end",
                f'Cmd(\'Store Group "{safe}" /o /nc\')',
                "",
            ]
        )
    out.write_text("\n".join(lines), encoding="utf-8")


def write_lua_labels(rows: list[dict[str, str]], out: Path) -> None:
    lines = [
        "-- Generated fixture labels for Stora Teatern",
        "local log = Printf",
        'local function storan_log(m) log("STORAN: " .. tostring(m)) end',
        "",
        "local labels = {",
    ]
    for row in rows:
        label = (row.get("label") or "").strip()
        if not label:
            continue
        chan = int(row["chan"])
        ftype = row.get("fixture_type", "").strip()
        text = f"{label} {ftype}".strip() if ftype else label
        text = text.replace('"', '\\"')
        lines.append(f'  [{chan}] = "{text}",')
    lines.extend(
        [
            "}",
            "for id, text in pairs(labels) do",
            '  storan_log("Label " .. id .. " -> " .. text)',
            '  Cmd(\'Label Fixture \' .. id .. \' "\' .. text .. \'"\')',
            "end",
            "",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    EXPORTS.mkdir(parents=True, exist_ok=True)
    rows = load_patch_csv()
    plan = load_build_plan()

    groups_txt = EXPORTS / "groups_commands.txt"
    labels_txt = EXPORTS / "labels_commands.txt"
    groups_lua = EXPORTS / "create_groups.lua"
    labels_lua = EXPORTS / "apply_labels.lua"
    summary = EXPORTS / "plan_summary.json"

    g_cmds = group_commands(plan)
    l_cmds = fixture_label_commands(rows)
    groups_txt.write_text("\n".join(g_cmds) + "\n", encoding="utf-8")
    labels_txt.write_text("\n".join(l_cmds) + "\n", encoding="utf-8")
    write_lua_groups(plan, groups_lua)
    write_lua_labels(rows, labels_lua)

    summary.write_text(
        json.dumps(
            {
                "channels_in_csv": len(rows),
                "expected_channels": plan.get("total_channels"),
                "group_count": len(plan.get("groups", {})),
                "label_command_count": len(l_cmds),
                "group_command_count": len(g_cmds),
                "outputs": {
                    "groups_commands": str(groups_txt),
                    "labels_commands": str(labels_txt),
                    "create_groups_lua": str(groups_lua),
                    "apply_labels_lua": str(labels_lua),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote plan to {EXPORTS}")


if __name__ == "__main__":
    main()
