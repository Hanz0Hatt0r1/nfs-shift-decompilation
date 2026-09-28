#!/usr/bin/env python3
"""Audit a directory or ZIP containing SHIFT vehicle BFF archives.

The tool inventories BFF headers and logical entry tables only; it does not
decode resource payloads. ZIP inputs are unpacked to a temporary directory so
the canonical BFF parser remains the single source of archive semantics.
"""
from __future__ import annotations

import argparse
import json
import re
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from bff_audit import audit_source


def _prepare_source(source: Path):
    if source.suffix.lower() != ".zip":
        yield source
        return

    with zipfile.ZipFile(source) as archive:
        names = [
            name for name in archive.namelist()
            if name.lower().endswith(".bff")
            and not name.endswith("/")
        ]
        with tempfile.TemporaryDirectory(prefix="shift-bff-corpus-") as temp_dir:
            root = Path(temp_dir)
            for name in names:
                target = root / Path(name).name
                target.write_bytes(archive.read(name))
            yield root


def _logical_suffix(entry_path: str) -> str:
    normalized = entry_path.replace(chr(92), "/").strip("/")
    match = re.match(r"^vehicles/[^/]+/(.*)$", normalized, flags=re.IGNORECASE)
    return "vehicles/{vehicle}/" + match.group(1) if match else normalized


def _common_logical_paths(
    reports: list[dict[str, Any]],
    *,
    minimum_archives: int = 2,
) -> list[dict[str, Any]]:
    owners: dict[str, set[str]] = defaultdict(set)
    kinds: dict[str, set[str]] = defaultdict(set)

    for report in reports:
        archive_name = str(report["archive"]["filename"])
        for entry in report.get("entries", []) or []:
            suffix = _logical_suffix(str(entry.get("path", "")))
            owners[suffix].add(archive_name)
            extension = Path(str(entry.get("path", ""))).suffix.lower()
            if extension:
                kinds[suffix].add(extension)

    rows = [
        {
            "path": path,
            "archive_count": len(archives),
            "archives": sorted(archives),
            "extensions": sorted(kinds[path]),
        }
        for path, archives in owners.items()
        if len(archives) >= int(minimum_archives)
    ]
    rows.sort(key=lambda row: (-row["archive_count"], row["path"]))
    return rows


def audit_vehicle_corpus(
    source: str | Path,
    *,
    minimum_archives: int = 2,
) -> dict[str, Any]:
    path = Path(source)
    reports: list[dict[str, Any]] = []
    for prepared in _prepare_source(path):
        reports.extend(audit_source(prepared)["archives"])

    total_entries = sum(
        int(report["summary"]["entries"])
        for report in reports
    )
    type_counts: dict[str, int] = {}
    x12d_values: set[int] = set()
    for report in reports:
        x12d = int(report["archive"]["x12d"])
        x12d_values.add(x12d)
        for key, value in report["summary"]["compression_types"].items():
            key = str(key)
            type_counts[key] = type_counts.get(key, 0) + int(value)

    extension_counts: dict[str, int] = {}
    for report in reports:
        for extension, count in report["summary"].get("extensions", {}).items():
            extension_counts[str(extension)] = (
                extension_counts.get(str(extension), 0) + int(count)
            )

    return {
        "format": "SHIFT.VehicleBFFCorpusAudit/1",
        "version": 1,
        "source": str(path),
        "archive_count": len(reports),
        "total_entries": total_entries,
        "compression_type_counts": dict(
            sorted(type_counts.items(), key=lambda item: int(item[0]))
        ),
        "extension_counts": dict(
            sorted(
                extension_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        "x12d_values": sorted(x12d_values),
        "all_x12d_zero": x12d_values <= {0},
        "archives": reports,
        "common_logical_paths": _common_logical_paths(
            reports,
            minimum_archives=minimum_archives,
        ),
        "ready": bool(reports) and x12d_values <= {0},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument(
        "--minimum-archives",
        type=int,
        default=2,
        help="minimum number of archives that must share a normalized logical path",
    )
    args = parser.parse_args(argv)

    if args.minimum_archives < 1:
        parser.error("--minimum-archives must be positive")

    report = audit_vehicle_corpus(
        args.source,
        minimum_archives=args.minimum_archives,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    print(json.dumps({
        "format": report["format"],
        "archive_count": report["archive_count"],
        "total_entries": report["total_entries"],
        "compression_type_counts": report["compression_type_counts"],
        "x12d_values": report["x12d_values"],
        "ready": report["ready"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
