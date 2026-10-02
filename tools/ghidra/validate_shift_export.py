#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

EXPECTED = {
    "binary.json": "json",
    "functions.jsonl": "jsonl",
    "callgraph.jsonl": "jsonl",
    "vtables.json": "json",
    "constructors.jsonl": "jsonl",
    "strings_xrefs.jsonl": "jsonl",
    "globals.jsonl": "jsonl",
    "static_tables.jsonl": "jsonl",
    "switches.jsonl": "jsonl",
    "factories.jsonl": "jsonl",
    "manifest.json": "json",
}


def validate_json(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        json.load(handle)
    return 1


def validate_jsonl(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: {exc}") from exc
            count += 1
    return count


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {Path(argv[0]).name} <export-directory>", file=sys.stderr)
        return 2

    root = Path(argv[1])
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1

    failed = False
    for name, kind in EXPECTED.items():
        path = root / name
        if not path.is_file():
            print(f"MISSING {name}")
            failed = True
            continue
        try:
            rows = validate_json(path) if kind == "json" else validate_jsonl(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"INVALID {name}: {exc}")
            failed = True
            continue
        print(f"OK      {name}: {path.stat().st_size} bytes, {rows} record(s)")

    if failed:
        return 1

    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    print("format:", manifest.get("format"))
    print("program:", manifest.get("program"))
    print("counts:", json.dumps(manifest.get("counts", {}), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
