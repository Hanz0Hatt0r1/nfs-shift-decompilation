#!/usr/bin/env python3
"""Validate and replay the supplemental M2.3 exact-root screen."""

from __future__ import annotations

import argparse
import csv
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from tools.replay_revenginstr_m23_scan22_recapture import (
    _read_jsonl,
    _row_count,
    _run,
    _validate_record,
    validate_frozen as validate_scan22_recapture,
)


EVIDENCE_ROOT = Path("evidence/revenginstr_m23_direct_call_replay")
SCAN22 = "screening-scan22"
SCAN22_RECAPTURE = "scan22-recapture-20261018"
SCAN24 = "scan24-exact-root-20261018"
ROOT_HEADER = (
    "format", "plan_id", "callee_entry", "parameter_index", "caller_entry",
    "caller_call_site", "caller_parameter_index", "argument_node_id", "status",
)
CFG_FUNCTIONS = ("009eb3f0", "00a271a0", "00a26ea0", "00a1d2c0")
FLOW_PATHS = {
    "00a271a0": (SCAN22, "callee-pcode-flow", "00a271a0.tsv"),
    "009eb3f0": (SCAN22, "callee-pcode-flow", "009eb3f0.tsv"),
    "00a26ea0": (SCAN24, "callee-pcode-flow-00a26ea0.tsv"),
    "00a1d2c0": (SCAN24, "callee-pcode-flow-00a1d2c0.tsv"),
}


def _safe_relative_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"manifest path escapes its evidence root: {value}")
    return path


def _read_roots(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t", strict=True)
        if tuple(reader.fieldnames or ()) != ROOT_HEADER:
            raise ValueError(f"caller parameter-root TSV header changed: {path}")
        return list(reader)


def validate_frozen(evidence_root: Path) -> dict[str, Any]:
    """Check scan24 hashes, parent lineage, and its bounded negative result."""
    validate_scan22_recapture(evidence_root)
    folder = evidence_root / SCAN24
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest.get("format") != "NFS.RevenginstrM23Scan24ExactRoot/1":
        raise ValueError("unsupported scan24 exact-root manifest")
    if manifest.get("program_id") != "nfs-shift:SHIFT.exe":
        raise ValueError("scan24 targets an unexpected program")

    for record in manifest.get("artifacts", []):
        _validate_record(folder / _safe_relative_path(record["path"]), record)
    for record in manifest.get("source_artifacts", []):
        _validate_record(evidence_root / _safe_relative_path(record["path"]), record)

    selected = manifest["selected_function"]
    roots = _read_roots(folder / "caller-parameter-roots.tsv")
    selected_roots = [row for row in roots if row["caller_entry"] == selected["function_entry"]]
    exact_callees = sorted(
        row["callee_entry"]
        for row in selected_roots
        if row["status"] == "direct_parameter_root"
    )
    if exact_callees != selected["exact_root_callees"]:
        raise ValueError("scan24 exact caller-root set changed")
    root_records = sorted(
        (
            row["caller_call_site"], row["callee_entry"], row["parameter_index"],
            row["caller_parameter_index"], row["status"],
        )
        for row in selected_roots
        if row["status"] == "direct_parameter_root"
    )
    expected_root_records = sorted(
        (
            record["caller_call_site"], record["callee_entry"],
            str(record["callee_parameter_index"]), str(record["caller_parameter_index"]),
            "direct_parameter_root",
        )
        for record in selected["exact_roots"]
    )
    if root_records != expected_root_records:
        raise ValueError("scan24 caller/callee parameter-root mappings changed")
    if selected["unrooted_direct_callee"] in exact_callees:
        raise ValueError("scan24 unexpectedly rooted the previously unresolved callee")
    selected_store_rows = _row_count(folder / "parameter-stores-00a271a0.tsv")
    selected_load_rows = _row_count(folder / "parameter-loads-00a271a0.tsv")
    selected_pair_rows = _row_count(folder / "field-access-pairs-00a271a0.jsonl")
    if (selected_store_rows, selected_load_rows, selected_pair_rows) != (
        selected["parameter_store_rows"], selected["parameter_load_rows"],
        selected["field_pair_rows"],
    ):
        raise ValueError("scan24 selected-function parameter/field counts changed")

    cfg = _read_jsonl(folder / "function-pcode-cfg-v3.jsonl")
    if [row.get("function_entry") for row in cfg] != list(CFG_FUNCTIONS):
        raise ValueError("scan24 CFG closure changed")
    memory_counts = Counter(
        row["function_entry"] for row in _read_jsonl(folder / "memory-store-access.jsonl")
    )
    if dict(sorted(memory_counts.items())) != manifest["memory_store_access_rows_by_function"]:
        raise ValueError("scan24 memory-store-access closure changed")

    effects = _read_jsonl(folder / "interprocedural-memory-effect-v1.jsonl")
    audits = _read_jsonl(folder / "field-store-load-dominance-v5.jsonl")
    effect_counts = dict(sorted(Counter(row["status"] for row in effects).items()))
    audit_counts = dict(sorted(Counter(row["status"] for row in audits).items()))
    if effect_counts != manifest["interprocedural_status_counts"]:
        raise ValueError("scan24 interprocedural status counts changed")
    if audit_counts != manifest["audit_v5_status_counts"]:
        raise ValueError("scan24 audit status counts changed")
    if manifest["unique_cfg_store_candidates"] != 0:
        raise ValueError("scan24 summary overstates its audit result")

    negative = manifest["negative_screen"]
    negative_counts = {
        "pcode_flow_rows": _row_count(folder / "caller-pcode-flow.tsv"),
        "parameter_load_rows": _row_count(folder / "parameter-loads.tsv"),
        "parameter_field_store_rows": _row_count(folder / "parameter-stores.tsv"),
        "memory_store_access_rows": _row_count(folder / "memory-store-access-00a20780.jsonl"),
        "field_pair_rows": _row_count(folder / "field-access-pairs.jsonl"),
    }
    if negative_counts != {key: negative[key] for key in negative_counts}:
        raise ValueError("scan24 negative-screen counts changed")
    return {
        "function_entry": selected["function_entry"],
        "exact_root_callees": exact_callees,
        "selected_parameter_store_rows": selected_store_rows,
        "selected_parameter_load_rows": selected_load_rows,
        "selected_field_pair_rows": selected_pair_rows,
        "cfg_rows": len(cfg),
        "memory_store_access_rows": sum(memory_counts.values()),
        "interprocedural_status_counts": effect_counts,
        "audit_v5_status_counts": audit_counts,
        "negative_screen_counts": negative_counts,
    }


def _filtered_jsonl(source: Path, entries: set[str]) -> bytes:
    selected: list[bytes] = []
    for line in source.read_bytes().splitlines(keepends=True):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("function_entry") in entries:
            selected.append(line if line.endswith(b"\n") else line + b"\n")
    return b"".join(selected)


def _merge_roots(parent: Path, additional: Path) -> bytes:
    parent_lines = parent.read_bytes().splitlines(keepends=True)
    additional_lines = additional.read_bytes().splitlines(keepends=True)
    if not parent_lines or not additional_lines or parent_lines[0] != additional_lines[0]:
        raise ValueError("scan24 parameter-root TSV headers do not match")
    body = b"".join(parent_lines[1:] + additional_lines[1:])
    return parent_lines[0] + body


def replay(evidence_root: Path, bin_dir: Path) -> dict[str, Any]:
    """Rebuild scan24's CFG/memory/root inputs and replay `/1` plus `/5`."""
    summary = validate_frozen(evidence_root)
    folder = evidence_root / SCAN24
    parent = evidence_root / SCAN22_RECAPTURE
    screen = evidence_root / SCAN22
    interprocedural = bin_dir / "revenginstr-interprocedural-memory-effects"
    dominance = bin_dir / "revenginstr-receiver-field-store-load-dominance-audit"
    missing = [str(path) for path in (interprocedural, dominance) if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing revenginstr command(s): " + ", ".join(missing))

    with tempfile.TemporaryDirectory(prefix="revenginstr-scan24-exact-root-") as temporary:
        scratch = Path(temporary)
        cfg = scratch / "function-pcode-cfg-v3.jsonl"
        cfg.write_bytes(
            _filtered_jsonl(parent / "callee-function-pcode-cfg-v3.jsonl", {"009eb3f0", "00a271a0"})
            + (folder / "new-callee-function-pcode-cfg-v3.jsonl").read_bytes()
        )
        if cfg.read_bytes() != (folder / "function-pcode-cfg-v3.jsonl").read_bytes():
            raise ValueError("scan24 combined CFG changed on reconstruction")

        memory = scratch / "memory-store-access.jsonl"
        memory.write_bytes(b"".join(
            path.read_bytes()
            for path in (
                folder / "memory-store-access-00a271a0.jsonl",
                parent / "callee-memory-store-access-009eb3f0.jsonl",
                folder / "callee-memory-store-access-00a26ea0.jsonl",
                folder / "callee-memory-store-access-00a1d2c0.jsonl",
            )
        ))
        if memory.read_bytes() != (folder / "memory-store-access.jsonl").read_bytes():
            raise ValueError("scan24 combined memory-store facts changed on reconstruction")

        roots = scratch / "caller-parameter-roots.tsv"
        roots.write_bytes(
            _merge_roots(parent / "caller-parameter-roots.tsv", folder / "subcall-parameter-roots.tsv")
        )
        if roots.read_bytes() != (folder / "caller-parameter-roots.tsv").read_bytes():
            raise ValueError("scan24 combined parameter roots changed on reconstruction")

        rebuilt_effects = scratch / "interprocedural-memory-effect-v1.jsonl"
        effect_args = [
            str(folder / "field-access-pairs-00a271a0.jsonl"), str(cfg), str(memory), str(roots),
        ]
        for entry, relative_parts in FLOW_PATHS.items():
            flow = evidence_root.joinpath(*relative_parts)
            effect_args.extend(["--pcode-flow", entry, str(flow)])
        effect_args.extend(["--output", str(rebuilt_effects)])
        _run(interprocedural, effect_args)
        if rebuilt_effects.read_bytes() != (folder / "interprocedural-memory-effect-v1.jsonl").read_bytes():
            raise ValueError("scan24 interprocedural memory effects changed on replay")

        rebuilt_audit = scratch / "field-store-load-dominance-v5.jsonl"
        _run(
            dominance,
            [
                str(folder / "field-access-pairs-00a271a0.jsonl"), str(cfg),
                "--memory-store-access-jsonl", str(memory),
                "--interprocedural-memory-effect-jsonl", str(rebuilt_effects),
                "--output", str(rebuilt_audit),
            ],
        )
        if rebuilt_audit.read_bytes() != (folder / "field-store-load-dominance-v5.jsonl").read_bytes():
            raise ValueError("scan24 dominance /5 audit changed on replay")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin-dir", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    summary = replay(args.repository_root / EVIDENCE_ROOT, args.bin_dir)
    print(
        "scan24 exact-root replay passed: "
        f"{len(summary['exact_root_callees'])} exact roots, "
        f"{summary['memory_store_access_rows']} memory facts, "
        f"{summary['audit_v5_status_counts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
