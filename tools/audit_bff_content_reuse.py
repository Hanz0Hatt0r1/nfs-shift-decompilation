#!/usr/bin/env python3
"""Audit exact raw BFF payload reuse across different logical resource paths.

A matching SHA-256 proves equality of the stored payload bytes for the supplied
archive scope. It does not prove decoded-resource, material, or runtime
semantic equivalence. This audit intentionally does not decompress payloads.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import Counter
from contextlib import ExitStack
import tempfile
from pathlib import Path
from typing import Any, Iterable

from resource_content_index import build_resource_content_index
from shift_importer import BFF


def _normalized_path(value: str) -> str:
    return value.replace("\\", "/").strip("/").lower()


def _materialize_bffs(
    inputs: Iterable[str | Path],
    stack: ExitStack,
) -> list[Path]:
    paths: list[Path] = []
    for source in inputs:
        path = Path(source)
        if path.suffix.lower() != ".zip":
            paths.append(path)
            continue
        archive = zipfile.ZipFile(path)
        stack.callback(archive.close)
        root = Path(
            stack.enter_context(
                tempfile.TemporaryDirectory(prefix="shift-bff-reuse-")
            )
        )
        for name in archive.namelist():
            if not name.lower().endswith(".bff") or name.endswith("/"):
                continue
            target = root / Path(name).name
            target.write_bytes(archive.read(name))
            paths.append(target)
    return paths


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _audit_bffs(
    inputs: Iterable[str | Path],
) -> tuple[list[dict[str, Any]], list[Path]]:
    rows: list[dict[str, Any]] = []
    with ExitStack() as stack:
        paths = _materialize_bffs(inputs, stack)
        for bff_path in paths:
            with BFF(bff_path) as archive:
                for entry in archive.entries:
                    raw = archive.raw_payload(entry)
                    rows.append(
                        {
                            "archive": archive.path.name,
                            "path": entry.path,
                            "normalized_path": _normalized_path(entry.path),
                            "raw_sha256": _sha256(raw),
                            "type": int(entry.type),
                            "compressed_size": int(entry.compressed_size),
                            "uncompressed_size": int(entry.uncompressed_size),
                            "entry_index": int(entry.index),
                        }
                    )
        return rows, paths


def _cross_archive_sha_groups(
    index: dict[str, Any],
    *,
    minimum_archives: int,
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for group in index["sha_groups"]:
        archives = list(group.get("archives") or [])
        if len(archives) < minimum_archives:
            continue
        paths = list(group.get("paths") or [])
        extensions = sorted(
            {
                Path(path).suffix.lower() or "<none>"
                for path in paths
            }
        )
        groups.append(
            {
                "sha256": group["sha256"],
                "archive_count": len(archives),
                "occurrence_count": int(group["occurrences"]),
                "unique_path_count": len(paths),
                "extensions": extensions,
                "archives": archives,
                "paths": paths,
            }
        )
    groups.sort(
        key=lambda row: (
            -row["archive_count"],
            -row["occurrence_count"],
            row["sha256"],
        )
    )
    return groups


def audit_content_reuse(
    inputs: Iterable[str | Path],
    *,
    minimum_archives: int = 2,
) -> dict[str, Any]:
    rows, paths = _audit_bffs(inputs)
    index = build_resource_content_index(rows)
    cross_archive = _cross_archive_sha_groups(
        index,
        minimum_archives=int(minimum_archives),
    )

    extension_counts = Counter(
        Path(row["path"]).suffix.lower() or "<none>"
        for row in rows
    )
    reused_occurrences = sum(
        row["occurrence_count"] for row in cross_archive
    )
    return {
        "format": "SHIFT.BFFRawPayloadReuseAudit/1",
        "version": 1,
        "minimum_archives": int(minimum_archives),
        "archive_count": len(paths),
        "entry_count": len(rows),
        "unique_raw_payloads": int(index["unique_sha256"]),
        "summary": {
            "cross_archive_raw_payload_groups": len(cross_archive),
            "cross_archive_reused_occurrences": reused_occurrences,
            "raw_payload_groups_ge5_archives": sum(
                row["archive_count"] >= 5 for row in cross_archive
            ),
            "raw_payload_groups_ge10_archives": sum(
                row["archive_count"] >= 10 for row in cross_archive
            ),
            "entry_extension_counts": dict(
                sorted(
                    extension_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ),
        },
        "groups": cross_archive,
        "limitations": [
            "A raw SHA-256 proves stored-byte equality for the supplied archives only.",
            "Different logical paths may still resolve to different runtime resources.",
            "No decoded-format, material, shader, or runtime semantic equivalence is inferred.",
        ],
        "ready": bool(rows) and bool(cross_archive),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--minimum-archives", type=int, default=2)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    if args.minimum_archives < 2:
        parser.error("--minimum-archives must be at least 2")

    report = audit_content_reuse(
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
