#!/usr/bin/env python3
"""Verify IMB primitive MTX references against same-archive BMT resources."""
from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Iterable

from imb_neutral_geometry import build_imb_neutral_geometry
from shift_importer import BFF

FORMAT = "SHIFT.IMBMaterialReferenceParity/1"


def _norm(value: str) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _bmt_reference(material: str) -> tuple[str | None, str | None]:
    value = str(material or "").replace("\\", "/")
    if value.lower().endswith(".mtx"):
        return value[:-4] + ".bmt", None
    if value.lower().endswith(".bmt"):
        return value, None
    return None, "primitive-material-reference-not-mtx-or-bmt"


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
                tempfile.TemporaryDirectory(prefix="shift-imb-material-")
            )
        )
        for name in archive.namelist():
            if not name.lower().endswith(".bff") or name.endswith("/"):
                continue
            target = root / Path(name).name
            target.write_bytes(archive.read(name))
            paths.append(target)
    return paths


def summarize_material_rows(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in rows]
    reasons = Counter()
    referenced = Counter()
    matched = 0
    same_archive_unique = 0
    compression_types = Counter()

    by_resource: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        expected = row.get("expected_bmt")
        if expected:
            referenced[_norm(str(expected))] += 1
            by_resource.setdefault(_norm(str(expected)), []).append(row)
        for reason in row.get("blocking_reasons") or []:
            reasons[str(reason)] += 1
        if row.get("ready") is True:
            matched += 1
            if int(row.get("same_archive_match_count") or 0) == 1:
                same_archive_unique += 1
            match = row.get("same_archive_match") or {}
            if match.get("type") is not None:
                compression_types[str(int(match["type"]))] += 1

    unique_ready = 0
    for material_rows in by_resource.values():
        if material_rows and all(row.get("ready") is True for row in material_rows):
            unique_ready += 1

    total = len(rows)
    ready = bool(total) and matched == total
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else ("empty" if not total else "partial"),
        "ready": ready,
        "primitive_reference_count": total,
        "matched_primitive_reference_count": matched,
        "blocked_primitive_reference_count": total - matched,
        "unique_bmt_reference_count": len(by_resource),
        "ready_unique_bmt_reference_count": unique_ready,
        "same_archive_unique_match_count": same_archive_unique,
        "material_reference_use_counts": dict(sorted(referenced.items())),
        "blocking_reason_counts": dict(sorted(reasons.items())),
        "same_archive_match_type_counts": dict(sorted(compression_types.items())),
        "rows": rows,
        "boundary": {
            "primitive_reference_source": "SHIFT.IMBNeutralGeometry/1",
            "mtx_to_bmt_alias": "replace terminal .mtx with .bmt",
            "archive_scope": "same BFF as source IMB",
            "ready_meaning": (
                "every IMB primitive resolves to exactly one same-archive BMT"
            ),
            "bmt_payload_decode": "not evaluated",
            "shader_texture_resolution": "not evaluated",
        },
    }


def audit_imb_material_parity(
    inputs: Iterable[str | Path],
    *,
    max_per_archive: int = 0,
) -> dict[str, Any]:
    inputs = list(inputs)
    rows: list[dict[str, Any]] = []
    archives: list[dict[str, Any]] = []

    with ExitStack() as stack:
        paths = _materialize_bffs(inputs, stack)
        for bff_path in sorted(paths, key=lambda item: item.name.lower()):
            with BFF(bff_path) as archive:
                by_path: dict[str, list[Any]] = {}
                for entry in archive.entries:
                    by_path.setdefault(_norm(entry.path), []).append(entry)

                imb_entries = [
                    entry
                    for entry in archive.entries
                    if Path(entry.path.replace("\\", "/")).suffix.lower() == ".imb"
                ]
                if max_per_archive:
                    imb_entries = imb_entries[:max_per_archive]

                archive_refs = 0
                archive_ready = 0
                for entry in imb_entries:
                    try:
                        payload = archive.extract_entry(entry, type2="lzx")
                        geometry = build_imb_neutral_geometry(payload)
                    except Exception as exc:
                        rows.append({
                            "archive": archive.path.name,
                            "imb_path": entry.path.replace("\\", "/"),
                            "primitive_index": None,
                            "material_reference": None,
                            "expected_bmt": None,
                            "same_archive_match_count": 0,
                            "ready": False,
                            "blocking_reasons": ["imb-decode-exception"],
                            "error_kind": type(exc).__name__,
                            "error": str(exc),
                        })
                        archive_refs += 1
                        continue

                    for primitive in geometry.get("primitives") or []:
                        archive_refs += 1
                        material = str(primitive.get("material") or "")
                        expected, alias_error = _bmt_reference(material)
                        blockers: list[str] = []
                        matches: list[Any] = []
                        if alias_error:
                            blockers.append(alias_error)
                        elif expected:
                            matches = by_path.get(_norm(expected), [])
                            if not matches:
                                blockers.append("same-archive-bmt-missing")
                            elif len(matches) != 1:
                                blockers.append(
                                    f"same-archive-bmt-ambiguous:{len(matches)}"
                                )

                        match_row = None
                        if len(matches) == 1:
                            match = matches[0]
                            match_row = {
                                "archive": archive.path.name,
                                "entry_index": int(match.index),
                                "path": match.path.replace("\\", "/"),
                                "type": int(match.type),
                                "compressed_size": int(match.compressed_size),
                                "uncompressed_size": int(match.uncompressed_size),
                            }

                        ready = not blockers
                        if ready:
                            archive_ready += 1
                        rows.append({
                            "archive": archive.path.name,
                            "imb_path": entry.path.replace("\\", "/"),
                            "imb_entry_index": int(entry.index),
                            "primitive_index": int(primitive.get("index") or 0),
                            "material_reference": material.replace("\\", "/"),
                            "expected_bmt": expected,
                            "same_archive_match_count": len(matches),
                            "same_archive_match": match_row,
                            "ready": ready,
                            "blocking_reasons": blockers,
                        })

                archives.append({
                    "archive": archive.path.name,
                    "imb_count": len(imb_entries),
                    "primitive_reference_count": archive_refs,
                    "ready_primitive_reference_count": archive_ready,
                    "blocked_primitive_reference_count": archive_refs - archive_ready,
                })

    report = summarize_material_rows(rows)
    report["input_count"] = len(inputs)
    report["archive_count"] = len(archives)
    report["max_per_archive"] = int(max_per_archive)
    report["archives"] = archives
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify IMB primitive MTX/BMT identity inside BFF/ZIP corpora"
    )
    parser.add_argument("inputs", nargs="+", help=".bff or .zip inputs")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--max-per-archive", type=int, default=0)
    parser.add_argument("--require-all-ready", action="store_true")
    args = parser.parse_args(argv)
    if args.max_per_archive < 0:
        parser.error("--max-per-archive must be non-negative")

    report = audit_imb_material_parity(
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
        "primitive_reference_count": report["primitive_reference_count"],
        "matched_primitive_reference_count": (
            report["matched_primitive_reference_count"]
        ),
        "unique_bmt_reference_count": report["unique_bmt_reference_count"],
        "blocking_reason_counts": report["blocking_reason_counts"],
        "same_archive_match_type_counts": (
            report["same_archive_match_type_counts"]
        ),
    }, ensure_ascii=False, indent=2))

    if args.require_all_ready and not report["ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
