#!/usr/bin/env python3
"""Audit compiled FXO coverage for source shader families across BFF corpora."""
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

from render_pipeline import shader_family
from shader_ir import parse_shader_blobs
from shift_importer import BFF

FORMAT = "SHIFT.ShaderFamilyFXOInventory/1"


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


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
                tempfile.TemporaryDirectory(prefix="shift-fxo-inventory-")
            )
        )
        for name in archive.namelist():
            if not name.lower().endswith(".bff") or name.endswith("/"):
                continue
            target = root / Path(name).name
            target.write_bytes(archive.read(name))
            paths.append(target)
    return paths


def _program_row(data: bytes, blob: Any) -> dict[str, Any]:
    payload = data[int(blob.offset):int(blob.end)]
    return {
        "stage": str(blob.stage),
        "offset": int(blob.offset),
        "end": int(blob.end),
        "version": [int(blob.major), int(blob.minor)],
        "instruction_count": int(blob.instruction_count),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "samplers": [
            {
                "name": row.get("name"),
                "register": row.get("register"),
                "count": row.get("count"),
            }
            for row in (blob.ctab_samplers or [])
        ],
        "constants": [
            {
                "name": row.get("name"),
                "register_set": row.get("register_set"),
                "register_index": row.get("register_index"),
                "register_count": row.get("register_count"),
            }
            for row in (blob.ctab_constants or [])
            if row.get("name")
        ],
    }


def inspect_fxo_payload(data: bytes) -> dict[str, Any]:
    blobs = parse_shader_blobs(data)
    programs = [_program_row(data, blob) for blob in blobs]
    stages = Counter(row["stage"] for row in programs)
    return {
        "payload_sha256": hashlib.sha256(data).hexdigest(),
        "decoded_size": len(data),
        "program_count": len(programs),
        "vertex_program_count": int(stages.get("vertex", 0)),
        "pixel_program_count": int(stages.get("pixel", 0)),
        "programs": programs,
        "parse_ready": bool(programs),
    }


def summarize_shader_families(
    shader_refs: Iterable[str],
    candidates: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    refs = list(dict.fromkeys(_norm(value) for value in shader_refs if value))
    candidate_rows = [dict(row) for row in candidates]
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in candidate_rows:
        family = str(row.get("family") or "")
        if family:
            by_family.setdefault(family, []).append(row)

    families: list[dict[str, Any]] = []
    for shader_ref in refs:
        family = shader_family(shader_ref)
        rows = list(by_family.get(family, []))
        payload_groups: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            sha = str(row.get("payload_sha256") or "")
            if sha:
                payload_groups.setdefault(sha, []).append(row)

        unique_payloads = []
        for sha, group in sorted(payload_groups.items()):
            representative = dict(group[0])
            unique_payloads.append({
                "payload_sha256": sha,
                "decoded_size": representative.get("decoded_size"),
                "program_count": representative.get("program_count"),
                "vertex_program_count": representative.get("vertex_program_count"),
                "pixel_program_count": representative.get("pixel_program_count"),
                "programs": representative.get("programs") or [],
                "copies": [
                    {
                        "archive": item.get("archive"),
                        "entry_index": item.get("entry_index"),
                        "path": item.get("path"),
                        "type": item.get("type"),
                    }
                    for item in group
                ],
            })

        parse_failures = [
            row for row in rows if row.get("parse_ready") is not True
        ]
        if not rows:
            status = "missing"
        elif parse_failures:
            status = "parse-blocked"
        elif len(unique_payloads) == 1:
            program_count = int(unique_payloads[0].get("program_count") or 0)
            status = (
                "single-payload"
                if program_count == 1
                else "single-payload-multi-program"
            )
        else:
            status = "multi-payload"

        families.append({
            "shader_ref": shader_ref,
            "family": family,
            "status": status,
            "candidate_copy_count": len(rows),
            "unique_payload_count": len(unique_payloads),
            "duplicate_copy_count": max(0, len(rows) - len(unique_payloads)),
            "parse_failure_count": len(parse_failures),
            "unique_payloads": unique_payloads,
        })

    all_present = bool(families) and all(
        row["candidate_copy_count"] > 0 for row in families
    )
    parse_ready = bool(families) and all(
        row["parse_failure_count"] == 0 for row in families
    )
    selection_ready = bool(families) and all(
        row["status"] == "single-payload" for row in families
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": (
            "selection-ready"
            if selection_ready
            else "inventory-ready"
            if all_present and parse_ready
            else "blocked"
        ),
        "ready": all_present and parse_ready,
        "selection_ready": selection_ready,
        "shader_reference_count": len(refs),
        "family_count": len(families),
        "candidate_copy_count": sum(
            row["candidate_copy_count"] for row in families
        ),
        "unique_payload_count": sum(
            row["unique_payload_count"] for row in families
        ),
        "duplicate_copy_count": sum(
            row["duplicate_copy_count"] for row in families
        ),
        "parse_failure_count": sum(
            row["parse_failure_count"] for row in families
        ),
        "families": families,
        "boundary": {
            "family_key": "render_pipeline.shader_family",
            "content_identity": "decoded FXO SHA-256",
            "d3d9_program_parser": "shader_ir.parse_shader_blobs",
            "duplicate_policy": "collapse byte-identical decoded FXO payloads",
            "selection_policy": (
                "inventory only; do not choose among multiple payloads or "
                "multiple programs without material/runtime evidence"
            ),
            "material_permutation_selection": "not evaluated",
            "runtime_same_instance_attribution": "not evaluated",
        },
    }


def audit_shader_family_fxo(
    inputs: Iterable[str | Path],
    shader_refs: Iterable[str],
) -> dict[str, Any]:
    shader_refs = list(shader_refs)
    target_families = {
        shader_family(_norm(ref))
        for ref in shader_refs
        if ref
    }
    candidates: list[dict[str, Any]] = []

    with ExitStack() as stack:
        paths = _materialize_bffs(inputs, stack)
        for path in paths:
            with BFF(path) as archive:
                for entry in archive.entries:
                    norm_path = _norm(entry.path)
                    if not norm_path.endswith(".fxo"):
                        continue
                    family = shader_family(norm_path)
                    if family not in target_families:
                        continue

                    row = {
                        "archive": archive.path.name,
                        "entry_index": int(entry.index),
                        "path": entry.path.replace("\\", "/"),
                        "type": int(entry.type),
                        "family": family,
                    }
                    try:
                        data = archive.extract_entry(entry, type2="lzx")
                        row.update(inspect_fxo_payload(data))
                    except Exception as exc:
                        row.update({
                            "parse_ready": False,
                            "error_kind": type(exc).__name__,
                            "error": str(exc),
                        })
                    candidates.append(row)

    report = summarize_shader_families(shader_refs, candidates)
    report["input_count"] = len(list(inputs)) if not isinstance(inputs, list) else len(inputs)
    report["target_families"] = sorted(target_families)
    report["candidate_rows"] = candidates
    return report


def _shader_refs_from_evidence(path: str | Path) -> list[str]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    refs: list[str] = []
    for row in value.get("shader_sources") or []:
        ref = row.get("path")
        if ref:
            refs.append(str(ref))
    if not refs:
        for ref in (
            (value.get("result") or {}).get("shader_reference_use_counts") or {}
        ):
            refs.append(str(ref))
    return refs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help=".bff or .zip inputs")
    parser.add_argument(
        "--shader-ref",
        action="append",
        default=[],
        help="source FX reference; may be repeated",
    )
    parser.add_argument(
        "--dependency-evidence",
        help="Phase 564-style JSON containing shader_sources",
    )
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--require-inventory-ready", action="store_true")
    parser.add_argument("--require-selection-ready", action="store_true")
    args = parser.parse_args(argv)

    refs = list(args.shader_ref)
    if args.dependency_evidence:
        refs.extend(_shader_refs_from_evidence(args.dependency_evidence))
    refs = list(dict.fromkeys(refs))
    if not refs:
        parser.error("at least one --shader-ref or --dependency-evidence is required")

    report = audit_shader_family_fxo(args.inputs, refs)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "selection_ready": report["selection_ready"],
        "family_count": report["family_count"],
        "candidate_copy_count": report["candidate_copy_count"],
        "unique_payload_count": report["unique_payload_count"],
        "duplicate_copy_count": report["duplicate_copy_count"],
        "parse_failure_count": report["parse_failure_count"],
    }, ensure_ascii=False, indent=2))

    if args.require-selection-ready and not report["selection_ready"]:
        return 2
    if args.require-inventory-ready and not report["ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
