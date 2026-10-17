#!/usr/bin/env python3
"""Verify and replay the frozen M2.3 SHIFT direct-call audit evidence."""

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


EVIDENCE_DIR = Path("evidence/revenginstr_m23_direct_call_replay")
PROGRAM_ID = "nfs-shift:SHIFT.exe"
AUDIT_VERSIONS = ("v1", "v2", "v3")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _row_count(path: Path) -> int:
    if path.suffix == ".jsonl":
        return len(_read_jsonl(path))
    if path.suffix == ".json":
        json.loads(path.read_text())
        return 1
    if path.suffix == ".tsv":
        with path.open(newline="") as stream:
            return max(0, sum(1 for _ in csv.reader(stream, delimiter="\t")) - 1)
    raise ValueError(f"unsupported evidence format: {path}")


def _validate_path_filter_case(evidence_dir: Path, entry: str, expected: dict[str, Any]) -> None:
    """Check write-free calls and retained barriers against exact audit witnesses."""
    folder = evidence_dir / entry
    calls = _read_jsonl(folder / "direct-call-memory-effects.jsonl")
    cfg_rows = _read_jsonl(folder / "function-pcode-cfg-v3.jsonl")
    if len(cfg_rows) != 1 or cfg_rows[0].get("function_entry") != entry:
        raise ValueError(f"path-filter case must use one CFG row for {entry}")
    cfg = cfg_rows[0]

    def call_row(spec: dict[str, Any]) -> dict[str, Any]:
        matches = [
            row for row in calls
            if row.get("address") == spec["address"]
            and row.get("time") == spec["time"]
            and ("callee_entry" not in spec or row.get("callee_entry") == spec["callee_entry"])
            and ("opcode" not in spec or row.get("opcode") == spec["opcode"])
        ]
        if len(matches) != 1:
            raise ValueError(f"path-filter call identity does not resolve exactly once: {entry}/{spec}")
        return matches[0]

    eligible_specs = expected.get("eligible_calls", [expected.get("eligible_call")])
    barrier_specs = expected.get("retained_barriers", [expected.get("retained_barrier")])
    eligible = [call_row(spec) for spec in eligible_specs if spec is not None]
    barriers = [call_row(spec) for spec in barrier_specs if spec is not None]
    if not eligible:
        raise ValueError(f"path-filter case has no eligible write-free call: {entry}")
    if any(row["status"] != "no_explicit_memory_write" for row in eligible):
        raise ValueError(f"path-filter call is not proven write-free: {entry}")
    for spec, row in zip(barrier_specs, barriers):
        if row["status"] != spec["status"] or row["status"] == "no_explicit_memory_write":
            raise ValueError(f"path-filter case does not retain the expected barrier: {entry}")

    def operation_block(fact: dict[str, Any]) -> int:
        matches = [
            block["block_index"]
            for block in cfg["blocks"]
            for operation in block["operations"]
            if operation.get("address") == fact["address"]
            and operation.get("time") == fact["time"]
            and operation.get("opcode") == fact.get("opcode")
        ]
        if len(matches) != 1:
            raise ValueError(f"path-filter call does not join to one CFG CALL: {entry}/{fact['address']}")
        return matches[0]

    eligible_blocks = [operation_block(row) for row in eligible]
    barrier_blocks = [operation_block(row) for row in barriers]
    versions = {version: _read_jsonl(folder / f"audit-{version}.jsonl") for version in ("v2", "v3")}
    pairs = expected.get("pairs", [expected])
    baseline_witnesses: dict[tuple[int, int, str], list[int]] = {}
    for version, rows in versions.items():
        for pair in pairs:
            matches = [
                row for row in rows
                if row["store"]["time"] == pair["store_time"]
                and row["load"]["time"] == pair["load_time"]
                and row["field_offset"] == pair["field_offset"]
            ]
            if len(matches) != 1:
                raise ValueError(f"path-filter pair does not resolve exactly once: {entry}/{version}")
            row = matches[0]
            witness = row["witnesses"]["memory_effect_store_to_load"]
            if witness != pair["witness_blocks"]:
                raise ValueError(f"path-filter witness changed: {entry}/{version}")
            for call, block in zip(eligible, eligible_blocks):
                if not pair["store_time"] < call["time"] < pair["load_time"]:
                    raise ValueError(f"write-free call is outside the paired access interval: {entry}")
                if block not in witness:
                    raise ValueError(f"eligible call is outside the effect witness: {entry}/{version}")
            for call, block in zip(barriers, barrier_blocks):
                if not pair["store_time"] < call["time"] < pair["load_time"]:
                    raise ValueError(f"retained barrier is outside the paired access interval: {entry}")
                if block not in witness:
                    raise ValueError(f"retained barrier is outside the effect witness: {entry}/{version}")
            if row["status"] != pair["audit_status"] or not row["memory_effect_path_exists"]:
                raise ValueError(f"path-filter case did not remain fail-closed: {entry}/{version}")
            pair_key = (pair["store_time"], pair["load_time"], pair["field_offset"])
            if version == "v2":
                baseline_witnesses[pair_key] = witness
            elif witness != baseline_witnesses[pair_key]:
                raise ValueError(f"/3 changed the witness despite a retained memory-effect barrier: {entry}")


def validate_frozen(evidence_dir: Path) -> dict[str, int]:
    """Check the manifest, digests, row counts, and fail-closed result summary."""
    manifest = json.loads((evidence_dir / "manifest.json").read_text())
    if manifest.get("format") != "NFS.RevenginstrM23DirectCallReplay/1":
        raise ValueError("unsupported frozen replay manifest")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("manifest has no artifacts")

    total_bytes = 0
    for record in artifacts:
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"artifact path escapes the evidence directory: {relative}")
        path = evidence_dir / relative
        if not path.is_file():
            raise ValueError(f"missing artifact: {relative}")
        payload = path.read_bytes()
        if len(payload) != record["bytes"]:
            raise ValueError(f"byte count mismatch: {relative}")
        if hashlib.sha256(payload).hexdigest() != record["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {relative}")
        if _row_count(path) != record["rows"]:
            raise ValueError(f"row count mismatch: {relative}")
        total_bytes += len(payload)

    candidates = manifest.get("candidates", {})
    expected_candidate_count = manifest.get("candidate_count")
    if not isinstance(candidates, dict) or len(candidates) != expected_candidate_count:
        raise ValueError(f"expected {expected_candidate_count} frozen candidates, found {len(candidates)}")
    replay_pairs = 0
    replay_calls = 0
    replay_call_statuses: Counter[str] = Counter()
    replay_audit_statuses = {version: Counter() for version in AUDIT_VERSIONS}
    for entry, expected in candidates.items():
        folder = evidence_dir / entry
        pairs = _read_jsonl(folder / "field-access-pairs.jsonl")
        if len(pairs) != expected["field_access_pair_rows"]:
            raise ValueError(f"field-pair row count mismatch for {entry}")
        calls = _read_jsonl(folder / "direct-call-memory-effects.jsonl")
        call_counts = dict(sorted(Counter(row["status"] for row in calls).items()))
        if call_counts != expected["direct_call_effect_status_counts"]:
            raise ValueError(f"direct-call status summary mismatch for {entry}")
        replay_pairs += len(pairs)
        replay_calls += len(calls)
        replay_call_statuses.update(call_counts)
        expected_write_free_rows = expected.get("write_free_direct_call_rows", 0)
        if call_counts.get("no_explicit_memory_write", 0) != expected_write_free_rows:
            raise ValueError(f"write-free direct-call count mismatch for {entry}")

        audit_counts: dict[str, dict[str, int]] = {}
        for version in AUDIT_VERSIONS:
            rows = _read_jsonl(folder / f"audit-{version}.jsonl")
            counts = dict(sorted(Counter(row["status"] for row in rows).items()))
            if counts != expected["audit_status_counts"][version]:
                raise ValueError(f"audit status summary mismatch for {entry}/{version}")
            if any("runtime value-flow claim" not in row["claim_scope"] for row in rows):
                raise ValueError(f"audit scope overclaims value flow for {entry}/{version}")
            audit_counts[version] = counts
            replay_audit_statuses[version].update(counts)
        if audit_counts["v2"] != audit_counts["v3"]:
            raise ValueError(f"unexpected /2-to-/3 status-count change in frozen candidate {entry}")

    computed_summary = {
        "candidate_count": len(candidates),
        "field_access_pair_rows": replay_pairs,
        "direct_call_effect_rows": replay_calls,
        "direct_call_effect_status_counts": dict(sorted(replay_call_statuses.items())),
        "audit_status_counts": {
            version: dict(sorted(counts.items())) for version, counts in replay_audit_statuses.items()
        },
        "per_pair_status_changes_v2_to_v3": 0,
    }
    if manifest.get("replay_summary") != computed_summary:
        raise ValueError("aggregate frozen replay summary does not match its candidate artifacts")

    path_filter_cases = manifest.get("path_filter_cases", {})
    if not isinstance(path_filter_cases, dict) or not path_filter_cases:
        raise ValueError("manifest has no frozen write-free-call path case")
    for entry, expected in path_filter_cases.items():
        if entry not in candidates:
            raise ValueError(f"path-filter case is not a frozen replay candidate: {entry}")
        _validate_path_filter_case(evidence_dir, entry, expected)

    screen = manifest.get("expanded_scan9_screen")
    if not isinstance(screen, dict):
        raise ValueError("manifest has no expanded scan9 screening summary")
    call_status_total = sum(screen.get("direct_call_effect_status_counts", {}).values())
    if call_status_total != screen.get("direct_call_effect_rows"):
        raise ValueError("scan9 direct-call status counts do not match the row total")
    for version in AUDIT_VERSIONS:
        if sum(screen.get("audit_status_counts", {}).get(version, {}).values()) != screen.get("ordered_field_pairs"):
            raise ValueError(f"scan9 {version} status counts do not match the ordered-pair total")
    if (
        screen.get("per_pair_status_changes_v1_to_v2") != 0
        or screen.get("per_pair_status_changes_v2_to_v3") != 0
    ):
        raise ValueError("scan9 screening reports an unexpected audit status change")
    scan9_eligible_calls = sum(
        len(case.get("eligible_calls", [case.get("eligible_call")]))
        for case in path_filter_cases.values() if case.get("screen_source", "scan9") == "scan9"
    )
    if len(screen.get("write_free_calls_on_exact_audit_witness", [])) != scan9_eligible_calls:
        raise ValueError("scan9 write-free-call path count does not match the frozen cases")

    expanded = manifest.get("expanded_scan10_13_screen")
    if not isinstance(expanded, dict) or json.loads((evidence_dir / "screening-scan10-13.json").read_text()) != expanded:
        raise ValueError("scan10–13 screening report does not match the frozen manifest")
    scans = expanded.get("scans", [])
    totals = expanded.get("totals", {})
    for field in (
        "parameter_export_candidates", "roots_with_pairs", "field_pair_rows", "ordered_pairs",
        "roots_with_ordered_pairs", "write_free_calls_on_exact_witness", "per_pair_status_changes_v2_to_v3",
    ):
        if sum(scan.get(field, 0) for scan in scans) != totals.get(field):
            raise ValueError(f"scan10–13 {field} does not match the screening total")
        if field == "per_pair_status_changes_v2_to_v3" and totals.get(field) != 0:
            raise ValueError("scan10–13 screening reports an unexpected /2-to-/3 status change")
    scan12_case = path_filter_cases.get("0060de20", {})
    scan12 = next((scan for scan in scans if scan.get("id") == "scan12"), {})
    if (
        len(scan12_case.get("eligible_calls", [])) != scan12.get("write_free_calls_on_exact_witness")
        or len(scan12_case.get("retained_barriers", [])) != scan12.get("retained_indirect_barriers_on_witness")
        or len(scan12_case.get("pairs", [])) != 2
    ):
        raise ValueError("scan12 path-filter case does not match its screening summary")

    return {"artifacts": len(artifacts), "candidates": len(candidates), "bytes": total_bytes}


def _run(binary: Path, arguments: list[str]) -> None:
    result = subprocess.run([str(binary), *arguments], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{binary.name} failed:\n{result.stdout}{result.stderr}")


def _split_pcode(source: Path, destination: Path) -> dict[str, Path]:
    with source.open(newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"P-code TSV has no header: {source}")
        groups: dict[str, list[dict[str, str]]] = {}
        for row in reader:
            groups.setdefault(row["function_entry"], []).append(row)

    paths: dict[str, Path] = {}
    for entry, rows in groups.items():
        path = destination / f"{entry}.tsv"
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=reader.fieldnames, delimiter="\t", lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
        paths[entry] = path
    return paths


def replay(evidence_dir: Path, bin_dir: Path) -> dict[str, int]:
    """Regenerate all derived pairs, call effects, and audit versions exactly."""
    summary = validate_frozen(evidence_dir)
    names = (
        "revenginstr-receiver-field-access-pairs",
        "revenginstr-direct-call-memory-effects",
        "revenginstr-receiver-field-store-load-dominance-audit",
    )
    binaries = {name: bin_dir / name for name in names}
    missing = [str(path) for path in binaries.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing revenginstr command(s): " + ", ".join(missing))

    manifest = json.loads((evidence_dir / "manifest.json").read_text())
    with tempfile.TemporaryDirectory(prefix="revenginstr-m23-replay-") as temporary:
        temporary_dir = Path(temporary)
        for entry in manifest["candidates"]:
            folder = evidence_dir / entry
            scratch = temporary_dir / entry
            scratch.mkdir()
            pairs = scratch / "field-access-pairs.jsonl"
            _run(
                binaries[names[0]],
                [
                    str(folder / "parameter-stores.tsv"),
                    str(folder / "parameter-loads.tsv"),
                    "--program-id",
                    PROGRAM_ID,
                    "--output",
                    str(pairs),
                ],
            )
            if pairs.read_bytes() != (folder / "field-access-pairs.jsonl").read_bytes():
                raise ValueError(f"field access pairs changed on replay: {entry}")

            flow_dir = scratch / "flows"
            flow_dir.mkdir()
            flows = _split_pcode(folder / "bounded-pcode.tsv", flow_dir)
            caller = flows.get(entry)
            if caller is None:
                raise ValueError(f"bounded P-code export omits caller {entry}")
            with caller.open(newline="") as stream:
                calls = [
                    row["callee_entry"]
                    for row in csv.DictReader(stream, delimiter="\t")
                    if row["opcode"] == "CALL" and row["callee_entry"] not in {"", "-"}
                ]
            call_effects = scratch / "direct-call-memory-effects.jsonl"
            arguments = [str(caller), "--program-id", PROGRAM_ID]
            for target in sorted(set(calls)):
                if target in flows:
                    arguments.extend(["--callee-flow", target, str(flows[target])])
            arguments.extend(["--output", str(call_effects)])
            _run(binaries[names[1]], arguments)
            if call_effects.read_bytes() != (folder / "direct-call-memory-effects.jsonl").read_bytes():
                raise ValueError(f"direct-call effect rows changed on replay: {entry}")

            for version in AUDIT_VERSIONS:
                output = scratch / f"audit-{version}.jsonl"
                command = [str(pairs), str(folder / "function-pcode-cfg-v3.jsonl")]
                if version in {"v2", "v3"}:
                    command.extend(["--memory-store-access-jsonl", str(folder / "memory-store-access.jsonl")])
                if version == "v3":
                    command.extend(["--direct-call-memory-effect-jsonl", str(call_effects)])
                command.extend(["--output", str(output)])
                _run(binaries[names[2]], command)
                if output.read_bytes() != (folder / f"audit-{version}.jsonl").read_bytes():
                    raise ValueError(f"{version} audit changed on replay: {entry}")

    return {
        **summary,
        "replayed_candidates": len(manifest["candidates"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin-dir", type=Path, required=True, help="revenginstr virtualenv bin directory")
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    evidence_dir = arguments.repository_root / EVIDENCE_DIR
    summary = replay(evidence_dir, arguments.bin_dir)
    print(
        f"M2.3 frozen replay passed: {summary['replayed_candidates']} candidates, "
        f"{summary['artifacts']} artifacts, {summary['bytes']} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
