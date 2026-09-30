#!/usr/bin/env python3
"""Audit source-backed IMB geometry readiness across BFF/ZIP corpora."""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Iterable

from imb_neutral_geometry import build_imb_neutral_geometry
from shift_importer import BFF

FORMAT = "SHIFT.IMBCorpusAudit/1"


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
                tempfile.TemporaryDirectory(prefix="shift-imb-corpus-")
            )
        )
        for name in archive.namelist():
            if not name.lower().endswith(".bff") or name.endswith("/"):
                continue
            target = root / Path(name).name
            target.write_bytes(archive.read(name))
            paths.append(target)
    return paths


def _property_ids(report: dict[str, Any]) -> list[str]:
    mesh = report.get("mesh") or {}
    return [str(value) for value in mesh.get("vertex_properties") or []]


def audit_decoded_imb_rows(
    rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate already-decoded IMB audit rows for deterministic testing."""
    normalized = [dict(row) for row in rows]
    versions = Counter()
    properties = Counter()
    blockers = Counter()
    errors = Counter()
    ready_count = 0
    deferred_streams = 0
    total_primitives = 0
    total_vertices = 0

    for row in normalized:
        version = row.get("version_text")
        if version:
            versions[str(version)] += 1
        for prop in row.get("decoded_properties") or []:
            properties[str(prop)] += 1
        for reason in row.get("blocking_reasons") or []:
            blockers[str(reason)] += 1
        if row.get("error_kind"):
            errors[str(row["error_kind"])] += 1
        if row.get("ready") is True:
            ready_count += 1
        deferred_streams += int(row.get("deferred_stream_count") or 0)
        total_primitives += int(row.get("primitive_count") or 0)
        total_vertices += int(row.get("vertex_count") or 0)

    total = len(normalized)
    blocked_count = total - ready_count
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if total and not blocked_count else (
            "empty" if not total else "partial"
        ),
        "ready": bool(total) and blocked_count == 0,
        "resource_count": total,
        "ready_count": ready_count,
        "blocked_count": blocked_count,
        "total_vertex_count": total_vertices,
        "total_primitive_count": total_primitives,
        "total_deferred_stream_count": deferred_streams,
        "version_counts": dict(sorted(versions.items())),
        "decoded_property_use_counts": dict(sorted(properties.items())),
        "blocking_reason_counts": dict(sorted(blockers.items())),
        "error_kind_counts": dict(sorted(errors.items())),
        "rows": normalized,
        "boundary": {
            "archive_extraction": "BFF Type 0/1/2 through existing importer",
            "geometry_adapter": "SHIFT.IMBNeutralGeometry/1",
            "unknown_stream_policy": "preserve/defer, not an audit failure",
            "ready_meaning": (
                "every selected IMB decoded to neutral geometry without a "
                "geometry blocker"
            ),
            "material_resolution": "not evaluated",
            "render_command_readiness": "not evaluated",
        },
    }


def audit_imb_corpus(
    inputs: Iterable[str | Path],
    *,
    max_per_archive: int = 0,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    archive_summaries: list[dict[str, Any]] = []

    with ExitStack() as stack:
        paths = _materialize_bffs(inputs, stack)
        for bff_path in sorted(paths, key=lambda item: item.name.lower()):
            archive_total = 0
            archive_ready = 0
            archive_blocked = 0
            with BFF(bff_path) as archive:
                entries = [
                    entry
                    for entry in archive.entries
                    if Path(entry.path.replace("\\", "/")).suffix.lower() == ".imb"
                ]
                if max_per_archive:
                    entries = entries[:max_per_archive]

                for entry in entries:
                    archive_total += 1
                    base = {
                        "archive": archive.path.name,
                        "entry_index": int(entry.index),
                        "path": entry.path.replace("\\", "/"),
                        "compression_type": int(entry.type),
                        "compressed_size": int(entry.compressed_size),
                        "uncompressed_size": int(entry.uncompressed_size),
                    }
                    try:
                        payload = archive.extract_entry(entry, type2="lzx")
                        digest = hashlib.sha256(payload).hexdigest()
                        report = build_imb_neutral_geometry(payload)
                        row = {
                            **base,
                            "decoded_sha256": digest,
                            "ready": bool(report.get("ready")),
                            "blocking_reasons": list(
                                report.get("blocking_reasons") or []
                            ),
                            "version_text": (
                                report.get("source") or {}
                            ).get("version_text"),
                            "resource_name": (
                                report.get("source") or {}
                            ).get("resource_name"),
                            "vertex_count": int(
                                (report.get("mesh") or {}).get("vertex_count")
                                or 0
                            ),
                            "primitive_count": int(
                                report.get("primitive_count") or 0
                            ),
                            "decoded_properties": _property_ids(report),
                            "deferred_stream_count": int(
                                report.get("deferred_stream_count") or 0
                            ),
                        }
                    except Exception as exc:
                        row = {
                            **base,
                            "ready": False,
                            "blocking_reasons": ["decode-exception"],
                            "error_kind": type(exc).__name__,
                            "error": str(exc),
                            "decoded_properties": [],
                            "deferred_stream_count": 0,
                            "primitive_count": 0,
                            "vertex_count": 0,
                        }

                    if row["ready"]:
                        archive_ready += 1
                    else:
                        archive_blocked += 1
                    rows.append(row)

            archive_summaries.append({
                "archive": bff_path.name,
                "resource_count": archive_total,
                "ready_count": archive_ready,
                "blocked_count": archive_blocked,
            })

    report = audit_decoded_imb_rows(rows)
    report["archives"] = archive_summaries
    report["archive_count"] = len(archive_summaries)
    report["input_count"] = len(list(inputs)) if isinstance(inputs, list) else None
    report["max_per_archive"] = int(max_per_archive)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit neutral IMB geometry readiness across BFF/ZIP corpora"
    )
    parser.add_argument("inputs", nargs="+", help=".bff or .zip inputs")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--max-per-archive", type=int, default=0)
    parser.add_argument(
        "--require-all-ready",
        action="store_true",
        help="return 2 unless every selected IMB is geometry-ready",
    )
    args = parser.parse_args(argv)

    if args.max_per_archive < 0:
        parser.error("--max-per-archive must be non-negative")

    report = audit_imb_corpus(
        args.inputs,
        max_per_archive=args.max_per_archive,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "archive_count": report["archive_count"],
        "resource_count": report["resource_count"],
        "ready_count": report["ready_count"],
        "blocked_count": report["blocked_count"],
        "version_counts": report["version_counts"],
        "blocking_reason_counts": report["blocking_reason_counts"],
        "error_kind_counts": report["error_kind_counts"],
    }, ensure_ascii=False, indent=2))

    if args.require_all_ready and not report["ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
