#!/usr/bin/env python3
"""Compare exact on-disk BFF payloads for common logical resource paths.

This is deliberately a raw-payload parity layer. It does not decompress Type-2
or invoke Oodle, so a match proves byte identity of the stored payload only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from shift_importer import BFF


def _iter_bffs(inputs: Iterable[str | Path]):
    for source in inputs:
        path = Path(source)
        if path.suffix.lower() != ".zip":
            yield path
            continue
        with zipfile.ZipFile(path) as archive:
            names = [
                name for name in archive.namelist()
                if name.lower().endswith(".bff") and not name.endswith("/")
            ]
            with tempfile.TemporaryDirectory(prefix="shift-bff-parity-") as td:
                root = Path(td)
                for name in names:
                    target = root / Path(name).name
                    target.write_bytes(archive.read(name))
                yield from sorted(root.glob("*.bff"))


def _normalized_path(value: str) -> str:
    return value.replace(chr(92), "/").strip("/").lower()


def _audit_bff(path: Path) -> dict[str, Any]:
    with BFF(path) as archive:
        entries: dict[str, dict[str, Any]] = {}
        for entry in archive.entries:
            raw = archive.raw_payload(entry)
            entries[_normalized_path(entry.path)] = {
                "path": entry.path,
                "type": int(entry.type),
                "compressed_size": int(entry.compressed_size),
                "uncompressed_size": int(entry.uncompressed_size),
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
            }
        return {
            "archive": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "x12d": int(archive.x12d),
            "entries": entries,
        }


def compare_payload_parity(
    inputs: Iterable[str | Path],
    *,
    minimum_archives: int = 3,
) -> dict[str, Any]:
    reports = [_audit_bff(Path(path)) for path in _iter_bffs(inputs)]
    owners: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for report in reports:
        for logical_path, entry in report["entries"].items():
            owners[logical_path].append({
                "archive": report["archive"],
                **entry,
            })

    matches: list[dict[str, Any]] = []
    for logical_path, items in owners.items():
        if len(items) < int(minimum_archives):
            continue
        hashes = {item["raw_sha256"] for item in items}
        if len(hashes) != 1:
            continue
        first = items[0]
        matches.append({
            "path": first["path"],
            "archive_count": len(items),
            "type": first["type"],
            "compressed_size": first["compressed_size"],
            "uncompressed_size": first["uncompressed_size"],
            "raw_sha256": first["raw_sha256"],
            "archives": sorted(item["archive"] for item in items),
        })

    matches.sort(key=lambda row: (-row["archive_count"], row["path"].lower()))

    return {
        "format": "SHIFT.BFFRawPayloadParity/1",
        "version": 1,
        "minimum_archives": int(minimum_archives),
        "archive_count": len(reports),
        "archives": [
            {
                "archive": report["archive"],
                "sha256": report["sha256"],
                "x12d": report["x12d"],
                "entry_count": len(report["entries"]),
            }
            for report in reports
        ],
        "summary": {
            "matching_paths": len(matches),
            "matching_paths_ge5": sum(row["archive_count"] >= 5 for row in matches),
            "matching_paths_ge10": sum(row["archive_count"] >= 10 for row in matches),
            "by_extension": _count_extensions(matches),
        },
        "matches": matches,
        "ready": bool(reports) and bool(matches),
    }


def _count_extensions(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        extension = Path(row["path"]).suffix.lower() or "<none>"
        counts[extension] = counts.get(extension, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--minimum-archives", type=int, default=3)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    if args.minimum_archives < 1:
        parser.error("--minimum-archives must be positive")

    report = compare_payload_parity(
        args.inputs,
        minimum_archives=args.minimum_archives,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
