#!/usr/bin/env python3
"""Scan real SHIFT BFF material corpora for render-state/native coverage."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from material_alpha_test import build_alpha_test_contract
from material_pipeline_state import translate_bmt_pipeline_state
from resource_formats import parse_bmt_material
from shift_importer import BFF

FORMAT = "SHIFT.BMTRenderStateCorpus/1"


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _stable_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _pipeline_input(material: Mapping[str, Any]) -> dict[str, Any]:
    state = dict(material.get("render_state") or {})
    state["cull"] = material.get("cull")
    return state


def _count(
    counter: Counter[str],
    key: str,
    value: Any,
) -> None:
    counter[f"{key}::{_stable_value(value)}"] += 1


def _split_counter(counter: Counter[str]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for composite, count in sorted(counter.items()):
        key, value = composite.split("::", 1)
        result.setdefault(key, {})[value] = count
    return result


def build_corpus_report(
    records: Iterable[Mapping[str, Any]],
    *,
    archives: Iterable[Mapping[str, Any]] = (),
    errors: Iterable[Mapping[str, Any]] = (),
    example_limit: int = 25,
) -> dict[str, Any]:
    rows = [dict(row) for row in records]
    error_rows = [dict(row) for row in errors]
    blockers: list[str] = []
    if error_rows:
        blockers.append("bmt-corpus:decode-errors")

    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        digest = str(row.get("payload_sha256") or "").lower()
        if len(digest) != 64:
            blockers.append(
                f"bmt-corpus:payload-sha256-missing:{_norm(row.get('path'))}"
            )
            continue
        unique.setdefault(digest, row)

    state_counts = Counter()
    values: Counter[str] = Counter()
    native_reasons = Counter()
    alpha_refs = Counter()
    examples: dict[str, list[dict[str, Any]]] = {
        "alpha_test_enabled": [],
        "blend_enabled": [],
        "depth_write_disabled": [],
        "depth_test_disabled": [],
        "native_blocked": [],
    }

    native_ready = 0
    native_blocked = 0
    alpha_test_enabled_count = 0

    for digest, row in sorted(
        unique.items(),
        key=lambda item: (_norm(item[1].get("path")), item[0]),
    ):
        material = (
            row.get("material")
            if isinstance(row.get("material"), Mapping)
            else {}
        )
        state = _pipeline_input(material)
        depth = state.get("depth")
        alpha_test = state.get("alpha_test")
        alpha_blend = state.get("alpha_blend")

        _count(values, "cull", material.get("cull"))
        if isinstance(depth, Mapping):
            state_counts["depth"] += 1
            _count(values, "depth.enabled", depth.get("enabled"))
            _count(values, "depth.write_enabled", depth.get("write_enabled"))
            if depth.get("function") is not None:
                _count(
                    values,
                    "depth.function",
                    (depth.get("function") or {}).get("raw")
                    if isinstance(depth.get("function"), Mapping)
                    else depth.get("function"),
                )
            if depth.get("enabled") is False:
                state_counts["depth_test_disabled"] += 1
                if len(examples["depth_test_disabled"]) < example_limit:
                    examples["depth_test_disabled"].append({
                        "path": row.get("path"),
                        "sha256": digest,
                    })
            if depth.get("write_enabled") is False:
                state_counts["depth_write_disabled"] += 1
                if len(examples["depth_write_disabled"]) < example_limit:
                    examples["depth_write_disabled"].append({
                        "path": row.get("path"),
                        "sha256": digest,
                    })

        if isinstance(alpha_blend, Mapping):
            state_counts["alpha_blend"] += 1
            _count(values, "alpha_blend.enabled", alpha_blend.get("enabled"))
            for field in ("source_blend", "dest_blend", "blend_op"):
                value = alpha_blend.get(field)
                if isinstance(value, Mapping):
                    value = value.get("raw")
                if value is not None:
                    _count(values, f"alpha_blend.{field}", value)
            if alpha_blend.get("enabled") is True:
                state_counts["blend_enabled"] += 1
                if len(examples["blend_enabled"]) < example_limit:
                    examples["blend_enabled"].append({
                        "path": row.get("path"),
                        "sha256": digest,
                    })

        if isinstance(alpha_test, Mapping):
            state_counts["alpha_test"] += 1
            contract = build_alpha_test_contract(alpha_test)
            _count(values, "alpha_test.enabled", contract.get("enabled"))
            _count(
                values,
                "alpha_test.function",
                (contract.get("compare") or {}).get("engine_name"),
            )
            ref = (contract.get("reference") or {}).get("d3d9_u8")
            if ref is not None:
                alpha_refs[str(ref)] += 1
            if contract.get("enabled") is True:
                alpha_test_enabled_count += 1
                if len(examples["alpha_test_enabled"]) < example_limit:
                    examples["alpha_test_enabled"].append({
                        "path": row.get("path"),
                        "sha256": digest,
                        "function": (
                            contract.get("compare") or {}
                        ).get("engine_name"),
                        "reference_u8": ref,
                    })

        pipeline = translate_bmt_pipeline_state(state)
        if pipeline.get("ready") is True:
            native_ready += 1
        else:
            native_blocked += 1
            reasons = list(pipeline.get("blocking_reasons") or [])
            for reason in reasons:
                native_reasons[str(reason)] += 1
            if len(examples["native_blocked"]) < example_limit:
                examples["native_blocked"].append({
                    "path": row.get("path"),
                    "sha256": digest,
                    "blocking_reasons": reasons,
                })

    archive_rows = [dict(row) for row in archives]
    unique_count = len(unique)
    ready = not blockers
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "partial",
        "ready": ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "archive_count": len(archive_rows),
        "archives": archive_rows,
        "stats": {
            "bmt_instances": len(rows),
            "unique_payloads": unique_count,
            "duplicate_instances": max(0, len(rows) - unique_count),
            "depth_groups": state_counts["depth"],
            "alpha_blend_groups": state_counts["alpha_blend"],
            "alpha_test_groups": state_counts["alpha_test"],
            "depth_test_disabled": state_counts["depth_test_disabled"],
            "depth_write_disabled": state_counts["depth_write_disabled"],
            "blend_enabled": state_counts["blend_enabled"],
            "alpha_test_enabled": alpha_test_enabled_count,
            "native_ready_unique_payloads": native_ready,
            "native_blocked_unique_payloads": native_blocked,
            "decode_errors": len(error_rows),
        },
        "values": _split_counter(values),
        "alpha_test_reference_u8": dict(sorted(alpha_refs.items())),
        "native_blocking_reasons": dict(
            sorted(native_reasons.items())
        ),
        "examples": examples,
        "errors": error_rows[:100],
        "boundary": {
            "payload_deduplication": "decoded-sha256",
            "alpha_test_d3d9_state": "source-backed",
            "alpha_test_native_execution": (
                "blocked-until-fragment-alpha-quantization-proof"
            ),
            "raw_payloads_embedded": False,
        },
    }


def _expand_inputs(paths: Iterable[Path]) -> list[Path]:
    archives: list[Path] = []
    for path in paths:
        if path.is_dir():
            archives.extend(
                p for p in path.rglob("*")
                if p.is_file() and p.suffix.lower() == ".bff"
            )
        elif path.is_file() and path.suffix.lower() == ".bff":
            archives.append(path)
        else:
            raise ValueError(f"not a BFF file/directory: {path}")
    return sorted(dict.fromkeys(p.resolve() for p in archives))


def scan_bff_corpus(paths: Iterable[Path]) -> dict[str, Any]:
    archive_paths = _expand_inputs(paths)
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    archives_meta: list[dict[str, Any]] = []

    for path in archive_paths:
        archive = BFF(path)
        try:
            bmt_entries = [
                entry for entry in archive.entries
                if _norm(entry.path).endswith(".bmt")
            ]
            archives_meta.append({
                "name": path.name,
                "file_count": len(archive.entries),
                "bmt_count": len(bmt_entries),
                "x12d": archive.x12d,
            })
            for entry in bmt_entries:
                try:
                    raw = archive.extract_entry(entry)
                    digest = hashlib.sha256(raw).hexdigest()
                    parsed = parse_bmt_material(raw)
                    records.append({
                        "archive": path.name,
                        "entry_index": entry.index,
                        "path": entry.path,
                        "compression_type": entry.type,
                        "decoded_size": len(raw),
                        "payload_sha256": digest,
                        "material": parsed.get("material") or {},
                    })
                except Exception as exc:
                    errors.append({
                        "archive": path.name,
                        "entry_index": entry.index,
                        "path": entry.path,
                        "error": f"{type(exc).__name__}: {exc}",
                    })
        finally:
            archive.close()

    return build_corpus_report(
        records,
        archives=archives_meta,
        errors=errors,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="BFF files and/or directories containing BFF files",
    )
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    result = scan_bff_corpus(args.inputs)
    encoded = json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
