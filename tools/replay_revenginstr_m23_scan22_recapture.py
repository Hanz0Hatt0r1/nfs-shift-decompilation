#!/usr/bin/env python3
"""Validate and replay the supplemental M2.3 scan22 Ghidra capture."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


EVIDENCE_ROOT = Path("evidence/revenginstr_m23_direct_call_replay")
RECAPTURE = "scan22-recapture-20261018"
CALLEES = ("009eb3f0", "00a20300", "00a26db0", "00a271a0")
FLOWS = ("00a277d0", *CALLEES)
ROOT_HEADER = (
    "format", "plan_id", "callee_entry", "parameter_index", "caller_entry",
    "caller_call_site", "caller_parameter_index", "argument_node_id", "status",
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _row_count(path: Path) -> int:
    if path.suffix == ".jsonl":
        return len(_read_jsonl(path))
    if path.suffix == ".tsv":
        with path.open(newline="", encoding="utf-8") as stream:
            return max(0, sum(1 for _ in csv.reader(stream, delimiter="\t")) - 1)
    if path.suffix == ".json":
        json.loads(path.read_text())
        return 1
    raise ValueError(f"unsupported evidence artifact: {path}")


def _validate_record(path: Path, expected: dict[str, Any]) -> None:
    payload = path.read_bytes()
    if len(payload) != expected["bytes"]:
        raise ValueError(f"byte count mismatch: {path}")
    if hashlib.sha256(payload).hexdigest() != expected["sha256"]:
        raise ValueError(f"SHA-256 mismatch: {path}")
    if _row_count(path) != expected["rows"]:
        raise ValueError(f"row count mismatch: {path}")


def validate_frozen(evidence_root: Path) -> dict[str, Any]:
    """Validate captured artifacts, source pins, and the fail-closed result."""
    folder = evidence_root / RECAPTURE
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest.get("format") != "NFS.RevenginstrM23Scan22Recapture/1":
        raise ValueError("unsupported scan22 recapture manifest")
    if manifest.get("program_id") != "nfs-shift:SHIFT.exe":
        raise ValueError("scan22 recapture targets an unexpected program")

    for record in manifest.get("artifacts", []):
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"artifact path escapes recapture directory: {relative}")
        _validate_record(folder / relative, record)
    for record in manifest.get("source_artifacts", []):
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"source path escapes evidence root: {relative}")
        _validate_record(evidence_root / relative, record)

    roots_path = folder / "caller-parameter-roots.tsv"
    with roots_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t", strict=True)
        if tuple(reader.fieldnames or ()) != ROOT_HEADER:
            raise ValueError("scan22 caller parameter-root TSV header changed")
        roots = list(reader)
    if sum(row.get("caller_entry") == "00a277d0" for row in roots) != 0:
        raise ValueError("scan22 selected caller unexpectedly acquired an exact formal root")
    if len(roots) != manifest["caller_arguments"]["exact_parameter_root_rows_total"]:
        raise ValueError("scan22 caller-root row count changed")

    cfg = _read_jsonl(folder / "callee-function-pcode-cfg-v3.jsonl")
    if sorted(row.get("function_entry") for row in cfg) != list(CALLEES):
        raise ValueError("scan22 callee CFG set changed")
    memory_counts = Counter(
        row["function_entry"]
        for path in sorted(folder.glob("callee-memory-store-access-*.jsonl"))
        for row in _read_jsonl(path)
    )
    expected_memory_counts = manifest["callee_exports"]["memory_store_access_rows_by_function"]
    if dict(sorted(memory_counts.items())) != expected_memory_counts:
        raise ValueError("scan22 callee memory-store-access counts changed")

    effects = _read_jsonl(folder / "interprocedural-memory-effect-v1.jsonl")
    audits = _read_jsonl(folder / "field-store-load-dominance-v5.jsonl")
    replay = manifest["replay"]
    if dict(sorted(Counter(row["status"] for row in effects).items())) != replay["new_interprocedural_status_counts"]:
        raise ValueError("scan22 interprocedural effect statuses changed")
    if dict(sorted(Counter(row["status"] for row in audits).items())) != replay["new_audit_v5_status_counts"]:
        raise ValueError("scan22 audit statuses changed")
    if replay["audit_v5_status_changes"] != 0 or replay["unique_cfg_store_candidates"] != 0:
        raise ValueError("scan22 recapture summary overstates its audit result")
    return {
        "artifacts": len(manifest["artifacts"]),
        "bytes": sum(record["bytes"] for record in manifest["artifacts"]),
        "caller_parameter_root_rows": len(roots),
        "selected_caller_parameter_root_rows": 0,
        "callee_cfg_rows": len(cfg),
        "callee_memory_store_access_rows": sum(memory_counts.values()),
        "interprocedural_status_counts": replay["new_interprocedural_status_counts"],
        "audit_v5_status_counts": replay["new_audit_v5_status_counts"],
    }


def _run(binary: Path, arguments: list[str]) -> None:
    result = subprocess.run([str(binary), *arguments], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{binary.name} failed:\n{result.stdout}{result.stderr}")


def replay(evidence_root: Path, bin_dir: Path) -> dict[str, Any]:
    """Rebuild the combined CFG/memory inputs and derived `/1` and `/5` rows."""
    summary = validate_frozen(evidence_root)
    folder = evidence_root / RECAPTURE
    scan = evidence_root / "screening-scan22"
    interprocedural = bin_dir / "revenginstr-interprocedural-memory-effects"
    dominance = bin_dir / "revenginstr-receiver-field-store-load-dominance-audit"
    missing = [str(path) for path in (interprocedural, dominance) if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing revenginstr command(s): " + ", ".join(missing))

    with tempfile.TemporaryDirectory(prefix="revenginstr-scan22-recapture-") as temporary:
        scratch = Path(temporary)
        cfg = scratch / "function-pcode-cfg-v3.jsonl"
        cfg.write_bytes(
            (scan / "function-pcode-cfg-v3.jsonl").read_bytes()
            + (folder / "callee-function-pcode-cfg-v3.jsonl").read_bytes()
        )
        memory = scratch / "memory-store-access.jsonl"
        memory.write_bytes(
            (scan / "memory-store-access.jsonl").read_bytes()
            + b"".join(
                path.read_bytes()
                for path in sorted(folder.glob("callee-memory-store-access-*.jsonl"))
            )
        )
        rebuilt_effects = scratch / "interprocedural-memory-effect-v1.jsonl"
        effect_args = [
            str(scan / "field-access-pairs.jsonl"), str(cfg), str(memory),
            str(folder / "caller-parameter-roots.tsv"),
        ]
        for entry in FLOWS:
            flow = (
                scan / "caller-pcode-flow" / f"{entry}.tsv"
                if entry == "00a277d0"
                else scan / "callee-pcode-flow" / f"{entry}.tsv"
            )
            effect_args.extend(["--pcode-flow", entry, str(flow)])
        effect_args.extend(["--output", str(rebuilt_effects)])
        _run(interprocedural, effect_args)
        expected_effects = folder / "interprocedural-memory-effect-v1.jsonl"
        if rebuilt_effects.read_bytes() != expected_effects.read_bytes():
            raise ValueError("scan22 interprocedural memory effects changed on replay")

        rebuilt_audit = scratch / "field-store-load-dominance-v5.jsonl"
        _run(
            dominance,
            [
                str(scan / "field-access-pairs.jsonl"), str(cfg),
                "--memory-store-access-jsonl", str(memory),
                "--interprocedural-memory-effect-jsonl", str(rebuilt_effects),
                "--output", str(rebuilt_audit),
            ],
        )
        if rebuilt_audit.read_bytes() != (folder / "field-store-load-dominance-v5.jsonl").read_bytes():
            raise ValueError("scan22 dominance /5 audit changed on replay")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin-dir", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    summary = replay(args.repository_root / EVIDENCE_ROOT, args.bin_dir)
    print(
        "scan22 recapture replay passed: "
        f"{summary['callee_cfg_rows']} callee CFGs, "
        f"{summary['callee_memory_store_access_rows']} callee memory facts, "
        f"{summary['caller_parameter_root_rows']} exact roots across all callers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
