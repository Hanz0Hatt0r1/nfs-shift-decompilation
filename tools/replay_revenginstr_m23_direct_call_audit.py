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



def _validate_screening_scan(
    evidence_dir: Path, manifest: dict[str, Any], *, scan_number: int, indirect_call_count: int
) -> None:
    label = f"scan{scan_number}"
    report_path = evidence_dir / f"screening-{label}.json"
    report = manifest.get(f"expanded_{label}_screen")
    if not isinstance(report, dict) or json.loads(report_path.read_text()) != report:
        raise ValueError(f"{label} screening report does not match the frozen manifest")
    if report.get("format") != "NFS.RevenginstrM23Screening/2" or report.get("program_id") != PROGRAM_ID:
        raise ValueError(f"{label} has an unsupported report format or program id")

    folder = evidence_dir / f"screening-{label}"
    for relative, expected in report.get("replay_inputs", {}).items():
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"{label} input path escapes its evidence directory: {relative}")
        path = folder / relative_path
        if not path.is_file():
            raise ValueError(f"{label} replay input is missing: {relative}")
        payload = path.read_bytes()
        if (
            len(payload) != expected.get("bytes")
            or hashlib.sha256(payload).hexdigest() != expected.get("sha256")
            or _row_count(path) != expected.get("rows")
        ):
            raise ValueError(f"{label} replay input digest/count mismatch: {relative}")

    source_path = folder / "selection-source.json"
    source = json.loads(source_path.read_text())
    selection = report.get("selection", {})
    selected = selection.get("candidates", [])
    if (
        report.get("source", {}).get("rows") != source.get("source_rows")
        or report.get("source", {}).get("sha256") != source.get("source_sha256")
        or selection.get("candidate_count") != source.get("candidate_count")
        or selection.get("previously_scanned_distinct_roots_excluded")
        != source.get("previously_scanned_distinct_roots_excluded")
        or len(selected) != selection.get("candidate_count")
    ):
        raise ValueError(f"{label} selection metadata does not match its frozen source")
    source_candidates = {row["function_entry"]: row for row in source.get("selection", [])}
    entries = [row.get("function_entry") for row in selected]
    if len(entries) != len(set(entries)) or set(entries) != set(source_candidates):
        raise ValueError(f"{label} candidate roots do not match the frozen selection source")

    stores_path = folder / "parameter-stores.tsv"
    loads_path = folder / "parameter-loads.tsv"
    with stores_path.open(newline="") as stream:
        store_rows = list(csv.DictReader(stream, delimiter="\t"))
    with loads_path.open(newline="") as stream:
        load_rows = list(csv.DictReader(stream, delimiter="\t"))
    memory_rows = _read_jsonl(folder / "memory-store-access.jsonl")
    pair_rows = _read_jsonl(folder / "field-access-pairs.jsonl")
    call_rows = _read_jsonl(folder / "direct-call-memory-effects.jsonl")
    audit_v2_rows = _read_jsonl(folder / "field-store-load-dominance-v2.jsonl")
    audit_rows = _read_jsonl(folder / "field-store-load-dominance-v3.jsonl")
    cfg_rows = _read_jsonl(folder / "function-pcode-cfg-v3.jsonl")
    relevant_memory_rows = _read_jsonl(folder / "memory-store-access-relevant.jsonl")

    counts = {
        "parameter_store_field": Counter(row["function_entry"] for row in store_rows),
        "parameter_load_field": Counter(row["function_entry"] for row in load_rows),
        "memory_store_access": Counter(row["function_entry"] for row in memory_rows),
    }
    pair_counts: Counter[str] = Counter()
    for pair in pair_rows:
        source_ids = []
        for edge in pair.get("edges", []):
            for provenance in edge.get("provenance", []):
                try:
                    identity = json.loads(provenance.get("source_id", ""))
                except (TypeError, json.JSONDecodeError):
                    continue
                if isinstance(identity, list) and len(identity) > 2 and identity[0] == PROGRAM_ID:
                    source_ids.append(identity)
        if not source_ids:
            raise ValueError(f"{label} field-pair graph has no exact source-row provenance")
        pair_counts[source_ids[0][1]] += 1
    counts["field_access_pairs"] = pair_counts

    selected_set = set(entries)
    for row in (*store_rows, *load_rows):
        if row.get("function_entry") not in selected_set:
            raise ValueError(f"{label} parameter export contains a root outside its selection")
    for row in memory_rows:
        if row.get("program_id") != PROGRAM_ID or row.get("function_entry") not in selected_set:
            raise ValueError(f"{label} memory-store export contains a foreign program/root")
    for candidate in selected:
        entry = candidate["function_entry"]
        source_candidate = source_candidates[entry]
        metrics = candidate["pcode_metrics"]
        if (
            candidate.get("source_name") != source_candidate.get("source_name")
            or candidate.get("parameter_count") != source_candidate.get("parameter_count")
            or metrics != source_candidate.get("metrics")
        ):
            raise ValueError(f"{label} source selection record changed: {entry}")
        if (
            candidate["parameter_count"] < 1
            or metrics["calls"] <= metrics["indirect_calls"]
            or metrics["indirect_calls"] != indirect_call_count
            or metrics["loads"] < 1
            or metrics["stores"] < 1
            or metrics["truncated"]
            or candidate["source_name"].startswith("thunk_")
        ):
            raise ValueError(f"{label} candidate does not satisfy the recorded selection: {entry}")
        actual_rows = {key: counts[key][entry] for key in counts}
        if candidate.get("export_rows") != actual_rows:
            raise ValueError(f"{label} per-root export counts changed: {entry}")

    totals = {
        "candidate_roots": len(selected),
        "parameter_store_field_rows": len(store_rows),
        "parameter_load_field_rows": len(load_rows),
        "memory_store_access_rows": len(memory_rows),
        "field_access_pair_rows": len(pair_rows),
        "roots_with_field_pairs": len(pair_counts),
        "audit_roots": len(cfg_rows),
        "audit_rows": len(audit_rows),
        "audit_v2_rows": len(audit_v2_rows),
        "audit_memory_store_access_rows": len(relevant_memory_rows),
        "audit_status_counts": dict(sorted(Counter(row["status"] for row in audit_rows).items())),
        "audit_v2_status_counts": dict(
            sorted(Counter(row["status"] for row in audit_v2_rows).items())
        ),
        "unique_cfg_store_candidate_rows": sum(row["status"] == "unique_cfg_store_candidate" for row in audit_rows),
        "unique_cfg_store_candidate_v2_rows": sum(
            row["status"] == "unique_cfg_store_candidate" for row in audit_v2_rows
        ),
        "per_pair_status_changes_v2_to_v3": 0,
        "direct_call_effect_rows": len(call_rows),
        "direct_call_effect_status_counts": dict(sorted(Counter(row["status"] for row in call_rows).items())),
        "write_free_direct_call_rows": sum(row["status"] == "no_explicit_memory_write" for row in call_rows),
    }
    expected_summary = report.get("summary", {})
    if any(expected_summary.get(key) != value for key, value in totals.items()):
        raise ValueError(f"{label} aggregate summary does not match the frozen rows")

    audit_roots = {row.get("function_entry") for row in cfg_rows}
    pair_roots = {entry for entry, count in pair_counts.items() if count}
    if len(cfg_rows) != len(audit_roots) or audit_roots != pair_roots:
        raise ValueError(f"{label} CFG roots do not match the field-pair roots")
    if any(row.get("function_entry") not in audit_roots for row in (*audit_v2_rows, *audit_rows)):
        raise ValueError(f"{label} audit contains a root without CFG evidence")
    if any(row.get("function_entry") not in audit_roots for row in relevant_memory_rows):
        raise ValueError(f"{label} audit memory sidecar contains a root without CFG evidence")
    if any("runtime value-flow claim" not in row.get("claim_scope", "") for row in (*audit_v2_rows, *audit_rows)):
        raise ValueError(f"{label} audit scope overclaims value flow")
    def audit_key(row: dict[str, Any]) -> tuple[str, str, str]:
        return (row["function_entry"], row["store"]["source_id"], row["load"]["source_id"])

    audit_v2_by_key = {audit_key(row): row for row in audit_v2_rows}
    audit_v3_by_key = {audit_key(row): row for row in audit_rows}
    if audit_v2_by_key.keys() != audit_v3_by_key.keys():
        raise ValueError(f"{label} /2 and /3 audits do not cover the same exact pairs")
    status_changes = sum(
        audit_v2_by_key[key]["status"] != audit_v3_by_key[key]["status"]
        for key in audit_v2_by_key
    )
    totals["per_pair_status_changes_v2_to_v3"] = status_changes
    if status_changes != report.get("summary", {}).get("per_pair_status_changes_v2_to_v3"):
        raise ValueError(f"{label} /2-to-/3 per-pair status change count is incorrect")
    if (
        totals["unique_cfg_store_candidate_rows"]
        or totals["unique_cfg_store_candidate_v2_rows"]
        or totals["write_free_direct_call_rows"]
    ):
        raise ValueError(f"{label} records an unsupported unique candidate or write-free call")

    caller_dir = folder / "caller-pcode-flow"
    caller_paths = sorted(caller_dir.glob("*.tsv"))
    if {path.stem for path in caller_paths} != audit_roots:
        raise ValueError(f"{label} caller-flow files do not match the audited roots")
    call_rows_by_root: dict[str, list[dict[str, Any]]] = {}
    for row in call_rows:
        call_rows_by_root.setdefault(row.get("function_entry", ""), []).append(row)
    for caller_path in caller_paths:
        entry = caller_path.stem
        with caller_path.open(newline="") as stream:
            flow_rows = list(csv.DictReader(stream, delimiter="\t"))
        if not flow_rows or any(row.get("function_entry") != entry for row in flow_rows):
            raise ValueError(f"{label} caller flow is not exact for {entry}")
        expected_calls = []
        for row in flow_rows:
            if row.get("opcode") not in {"CALL", "CALLIND"}:
                continue
            target = row.get("callee_entry")
            expected_target = target if target not in {"", "-"} else None
            expected_calls.append(
                (row["op_address"], int(row["op_time"]), row["opcode"], expected_target)
            )
        actual_calls = [
            (row.get("address"), row.get("time"), row.get("opcode"), row.get("callee_entry"))
            for row in call_rows_by_root.get(entry, [])
        ]
        if actual_calls != expected_calls:
            raise ValueError(f"{label} direct-call facts do not match caller P-code: {entry}")
        for _, _, opcode, target in expected_calls:
            if opcode == "CALL" and target != entry and not (folder / "callee-pcode-flow" / f"{target}.tsv").is_file():
                raise ValueError(f"{label} direct callee flow is missing: {entry} -> {target}")

    for name, expected in report.get("aggregated_exports", {}).items():
        path = folder / name
        payload = path.read_bytes()
        if (
            len(payload) != expected.get("bytes")
            or hashlib.sha256(payload).hexdigest() != expected.get("sha256")
            or _row_count(path) != expected.get("rows")
        ):
            raise ValueError(f"{label} aggregate export metadata changed: {name}")


def _validate_empty_screen(
    evidence_dir: Path, manifest: dict[str, Any], *, scan_number: int, indirect_call_count: int
) -> None:
    label = f"scan{scan_number}"
    report_path = evidence_dir / f"screening-{label}.json"
    report = manifest.get(f"expanded_{label}_screen")
    if not isinstance(report, dict) or json.loads(report_path.read_text()) != report:
        raise ValueError(f"{label} screening report does not match the frozen manifest")
    if report.get("format") != "NFS.RevenginstrM23Screening/2" or report.get("program_id") != PROGRAM_ID:
        raise ValueError(f"{label} has an unsupported report format or program id")

    folder = evidence_dir / f"screening-{label}"
    for relative, expected in report.get("replay_inputs", {}).items():
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"{label} input path escapes its evidence directory: {relative}")
        path = folder / relative_path
        if not path.is_file():
            raise ValueError(f"{label} replay input is missing: {relative}")
        payload = path.read_bytes()
        if (
            len(payload) != expected.get("bytes")
            or hashlib.sha256(payload).hexdigest() != expected.get("sha256")
            or _row_count(path) != expected.get("rows")
        ):
            raise ValueError(f"{label} replay input digest/count mismatch: {relative}")

    source = json.loads((folder / "selection-source.json").read_text())
    selection = report.get("selection", {})
    selected = selection.get("candidates", [])
    if (
        report.get("source", {}).get("rows") != source.get("source_rows")
        or report.get("source", {}).get("sha256") != source.get("source_sha256")
        or selection.get("candidate_count") != source.get("candidate_count")
        or selection.get("previously_scanned_distinct_roots_excluded")
        != source.get("previously_scanned_distinct_roots_excluded")
        or len(selected) != selection.get("candidate_count")
    ):
        raise ValueError(f"{label} selection metadata does not match its frozen source")
    source_candidates = {row["function_entry"]: row for row in source.get("selection", [])}
    entries = [row.get("function_entry") for row in selected]
    if len(entries) != len(set(entries)) or set(entries) != set(source_candidates):
        raise ValueError(f"{label} candidate roots do not match the frozen selection source")

    with (folder / "parameter-stores.tsv").open(newline="") as stream:
        store_rows = list(csv.DictReader(stream, delimiter="\t"))
    with (folder / "parameter-loads.tsv").open(newline="") as stream:
        load_rows = list(csv.DictReader(stream, delimiter="\t"))
    memory_rows = _read_jsonl(folder / "memory-store-access.jsonl")
    pair_rows = _read_jsonl(folder / "field-access-pairs.jsonl")
    if store_rows or pair_rows:
        raise ValueError(f"{label} empty screen contains a parameter-field store or pair")
    selected_set = set(entries)
    if any(row.get("function_entry") not in selected_set for row in (*store_rows, *load_rows)):
        raise ValueError(f"{label} parameter export contains a root outside its selection")
    if any(row.get("program_id") != PROGRAM_ID or row.get("function_entry") not in selected_set for row in memory_rows):
        raise ValueError(f"{label} memory-store export contains a foreign program/root")

    loads_by_entry = Counter(row["function_entry"] for row in load_rows)
    memory_by_entry = Counter(row["function_entry"] for row in memory_rows)
    contract = report.get("empty_export_contract", {})
    store_hashes = set(contract.get("parameter_stores_sha256_values", []))
    pair_hashes = set(contract.get("field_access_pairs_sha256_values", []))
    empty_store_hash = hashlib.sha256((folder / "parameter-stores.tsv").read_bytes()).hexdigest()
    empty_pair_hash = hashlib.sha256((folder / "field-access-pairs.jsonl").read_bytes()).hexdigest()
    if (
        contract.get("parameter_store_field_rows_per_candidate") != 0
        or contract.get("field_access_pair_rows_per_candidate") != 0
        or store_hashes != {empty_store_hash}
        or pair_hashes != {empty_pair_hash}
    ):
        raise ValueError(f"{label} empty-export contract does not match its frozen outputs")

    for candidate in selected:
        entry = candidate["function_entry"]
        source_candidate = source_candidates[entry]
        metrics = candidate["pcode_metrics"]
        hashes = candidate.get("source_export_sha256", {})
        if (
            candidate.get("source_name") != source_candidate.get("source_name")
            or candidate.get("parameter_count") != source_candidate.get("parameter_count")
            or metrics != source_candidate.get("metrics")
        ):
            raise ValueError(f"{label} source selection record changed: {entry}")
        if (
            candidate["parameter_count"] < 1
            or metrics["calls"] <= metrics["indirect_calls"]
            or metrics["indirect_calls"] != indirect_call_count
            or metrics["loads"] < 1
            or metrics["stores"] < 1
            or metrics["truncated"]
            or candidate["source_name"].startswith("thunk_")
        ):
            raise ValueError(f"{label} candidate does not satisfy the recorded selection: {entry}")
        actual_rows = {
            "parameter_store_field": 0,
            "parameter_load_field": loads_by_entry[entry],
            "memory_store_access": memory_by_entry[entry],
            "field_access_pairs": 0,
        }
        if (
            candidate.get("export_rows") != actual_rows
            or hashes.get("parameter_stores") not in store_hashes
            or hashes.get("field_access_pairs") not in pair_hashes
        ):
            raise ValueError(f"{label} per-root export summary mismatch: {entry}")

    totals = report.get("summary", {})
    actual_totals = {
        "candidate_roots": len(selected),
        "parameter_store_field_rows": len(store_rows),
        "parameter_load_field_rows": len(load_rows),
        "memory_store_access_rows": len(memory_rows),
        "field_access_pair_rows": len(pair_rows),
        "roots_with_field_pairs": 0,
        "dominance_audits_run": 0,
    }
    if any(totals.get(key) != value for key, value in actual_totals.items()):
        raise ValueError(f"{label} aggregate summary does not match its frozen rows")
    for name, expected in report.get("aggregated_exports", {}).items():
        path = folder / name
        payload = path.read_bytes()
        if (
            len(payload) != expected.get("bytes")
            or hashlib.sha256(payload).hexdigest() != expected.get("sha256")
            or _row_count(path) != expected.get("rows")
        ):
            raise ValueError(f"{label} aggregate export metadata changed: {name}")


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

    scan14 = manifest.get("expanded_scan14_screen")
    if not isinstance(scan14, dict) or json.loads((evidence_dir / "screening-scan14.json").read_text()) != scan14:
        raise ValueError("scan14 screening report does not match the frozen manifest")
    exported = scan14.get("selection", {}).get("candidates", [])
    if len(exported) != scan14.get("selection", {}).get("candidate_count"):
        raise ValueError("scan14 candidate count does not match its selection rows")
    totals = Counter()
    for candidate in exported:
        entry = candidate["function_entry"]
        metrics = candidate["pcode_metrics"]
        if (
            candidate["parameter_count"] < 1
            or metrics["calls"] <= metrics["indirect_calls"]
            or metrics["loads"] < 1
            or metrics["stores"] < 1
            or metrics["truncated"]
            or candidate["source_name"].startswith("thunk_")
        ):
            raise ValueError(f"scan14 candidate does not satisfy the recorded selection: {entry}")
        folder = evidence_dir / "screening-scan14" / entry
        for filename, key in (
            ("parameter-stores.tsv", "parameter_store_rows"),
            ("parameter-loads.tsv", "parameter_load_rows"),
            ("memory-store-access.jsonl", "memory_store_access_rows"),
            ("field-access-pairs.jsonl", "field_access_pair_rows"),
        ):
            count = _row_count(folder / filename)
            if count != candidate["exports"][key]:
                raise ValueError(f"scan14 export row count mismatch: {entry}/{filename}")
            totals[key] += count
    if any(totals[key] != scan14["summary"].get(key) for key in totals):
        raise ValueError("scan14 export totals do not match the screening report")
    if totals["parameter_store_rows"] or totals["field_access_pair_rows"]:
        raise ValueError("scan14 reports field pairs without parameter-store-field rows")
    if (
        scan14["summary"].get("candidate_roots") != len(exported)
        or scan14["summary"].get("roots_with_field_pairs") != 0
        or scan14["summary"].get("dominance_audits_run") != 0
    ):
        raise ValueError("scan14 screening conclusion is inconsistent with its exports")

    scan15 = manifest.get("expanded_scan15_screen")
    if not isinstance(scan15, dict) or json.loads((evidence_dir / "screening-scan15.json").read_text()) != scan15:
        raise ValueError("scan15 screening report does not match the frozen manifest")
    selected = scan15.get("selection", {}).get("candidates", [])
    if len(selected) != scan15.get("selection", {}).get("candidate_count"):
        raise ValueError("scan15 candidate count does not match its selection rows")
    entries = [candidate["function_entry"] for candidate in selected]
    if len(entries) != len(set(entries)):
        raise ValueError("scan15 contains duplicate function entries")
    load_path = evidence_dir / "screening-scan15" / "parameter-loads.tsv"
    store_path = evidence_dir / "screening-scan15" / "memory-store-access.jsonl"
    with load_path.open(newline="") as stream:
        load_rows = list(csv.DictReader(stream, delimiter="\t"))
    memory_rows = _read_jsonl(store_path)
    loads_by_entry = Counter(row["function_entry"] for row in load_rows)
    stores_by_entry = Counter(row["function_entry"] for row in memory_rows)
    expected_empty_hashes = scan15.get("empty_export_contract", {})
    store_hashes = set(expected_empty_hashes.get("parameter_stores_sha256_values", []))
    pair_hashes = set(expected_empty_hashes.get("field_access_pairs_sha256_values", []))
    for candidate in selected:
        entry = candidate["function_entry"]
        metrics = candidate["pcode_metrics"]
        rows = candidate["export_rows"]
        hashes = candidate["source_export_sha256"]
        if (
            candidate["parameter_count"] < 1
            or metrics["calls"] <= metrics["indirect_calls"]
            or metrics["indirect_calls"] != 0
            or metrics["loads"] < 1
            or metrics["stores"] < 1
            or metrics["truncated"]
            or candidate["source_name"].startswith("thunk_")
        ):
            raise ValueError(f"scan15 candidate does not satisfy the recorded selection: {entry}")
        if (
            rows["parameter_store_field"] != 0
            or rows["field_access_pairs"] != 0
            or rows["parameter_load_field"] != loads_by_entry[entry]
            or rows["memory_store_access"] != stores_by_entry[entry]
            or hashes["parameter_stores"] not in store_hashes
            or hashes["field_access_pairs"] not in pair_hashes
        ):
            raise ValueError(f"scan15 per-function export summary mismatch: {entry}")
    totals = scan15["summary"]
    if (
        totals.get("candidate_roots") != len(selected)
        or totals.get("parameter_store_field_rows") != 0
        or totals.get("parameter_load_field_rows") != len(load_rows)
        or totals.get("memory_store_access_rows") != len(memory_rows)
        or totals.get("field_access_pair_rows") != 0
        or totals.get("roots_with_field_pairs") != 0
        or totals.get("dominance_audits_run") != 0
        or sum(loads_by_entry.values()) != totals.get("parameter_load_field_rows")
        or sum(stores_by_entry.values()) != totals.get("memory_store_access_rows")
    ):
        raise ValueError("scan15 export totals do not match the screening report")

    _validate_screening_scan(evidence_dir, manifest, scan_number=16, indirect_call_count=1)
    _validate_screening_scan(evidence_dir, manifest, scan_number=17, indirect_call_count=2)
    _validate_screening_scan(evidence_dir, manifest, scan_number=18, indirect_call_count=3)
    _validate_empty_screen(evidence_dir, manifest, scan_number=19, indirect_call_count=4)
    _validate_empty_screen(evidence_dir, manifest, scan_number=20, indirect_call_count=5)
    _validate_empty_screen(evidence_dir, manifest, scan_number=21, indirect_call_count=6)

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

        replayed_screening_roots = 0
        for scan_number in (16, 17, 18):
            label = f"scan{scan_number}"
            scan = evidence_dir / f"screening-{label}"
            screening_scratch = temporary_dir / label
            screening_scratch.mkdir()
            pairs = screening_scratch / "field-access-pairs.jsonl"
            _run(
                binaries[names[0]],
                [
                    str(scan / "parameter-stores.tsv"),
                    str(scan / "parameter-loads.tsv"),
                    "--program-id",
                    PROGRAM_ID,
                    "--output",
                    str(pairs),
                ],
            )
            if pairs.read_bytes() != (scan / "field-access-pairs.jsonl").read_bytes():
                raise ValueError(f"{label} field access pairs changed on replay")

            combined_effects = screening_scratch / "direct-call-memory-effects.jsonl"
            with combined_effects.open("wb") as combined:
                for caller in sorted((scan / "caller-pcode-flow").glob("*.tsv")):
                    arguments = [str(caller), "--program-id", PROGRAM_ID]
                    with caller.open(newline="") as stream:
                        targets = sorted({
                            row["callee_entry"]
                            for row in csv.DictReader(stream, delimiter="\t")
                            if row["opcode"] == "CALL" and row["callee_entry"] not in {"", "-"}
                        })
                    for target in targets:
                        flow = caller if target == caller.stem else scan / "callee-pcode-flow" / f"{target}.tsv"
                        if flow.is_file():
                            arguments.extend(["--callee-flow", target, str(flow)])
                    output = screening_scratch / f"{caller.stem}-direct-call-memory-effects.jsonl"
                    arguments.extend(["--output", str(output)])
                    _run(binaries[names[1]], arguments)
                    combined.write(output.read_bytes())
            if combined_effects.read_bytes() != (scan / "direct-call-memory-effects.jsonl").read_bytes():
                raise ValueError(f"{label} direct-call effects changed on replay")

            for version in ("v2", "v3"):
                audit = screening_scratch / f"field-store-load-dominance-{version}.jsonl"
                command = [
                    str(pairs),
                    str(scan / "function-pcode-cfg-v3.jsonl"),
                    "--memory-store-access-jsonl",
                    str(scan / "memory-store-access-relevant.jsonl"),
                ]
                if version == "v3":
                    command.extend(["--direct-call-memory-effect-jsonl", str(combined_effects)])
                command.extend(["--output", str(audit)])
                _run(binaries[names[2]], command)
                if audit.read_bytes() != (scan / f"field-store-load-dominance-{version}.jsonl").read_bytes():
                    raise ValueError(f"{label} dominance /{version[-1]} audit changed on replay")

            replayed_screening_roots += manifest[f"expanded_{label}_screen"]["selection"]["candidate_count"]

        scan19 = evidence_dir / "screening-scan19"
        screening_scratch = temporary_dir / "scan19"
        screening_scratch.mkdir()
        pairs = screening_scratch / "field-access-pairs.jsonl"
        _run(
            binaries[names[0]],
            [
                str(scan19 / "parameter-stores.tsv"),
                str(scan19 / "parameter-loads.tsv"),
                "--program-id",
                PROGRAM_ID,
                "--output",
                str(pairs),
            ],
        )
        if pairs.read_bytes() != (scan19 / "field-access-pairs.jsonl").read_bytes():
            raise ValueError("scan19 field access pairs changed on replay")
        replayed_screening_roots += manifest["expanded_scan19_screen"]["selection"]["candidate_count"]

        scan20 = evidence_dir / "screening-scan20"
        screening_scratch = temporary_dir / "scan20"
        screening_scratch.mkdir()
        pairs = screening_scratch / "field-access-pairs.jsonl"
        _run(
            binaries[names[0]],
            [
                str(scan20 / "parameter-stores.tsv"),
                str(scan20 / "parameter-loads.tsv"),
                "--program-id",
                PROGRAM_ID,
                "--output",
                str(pairs),
            ],
        )
        if pairs.read_bytes() != (scan20 / "field-access-pairs.jsonl").read_bytes():
            raise ValueError("scan20 field access pairs changed on replay")
        replayed_screening_roots += manifest["expanded_scan20_screen"]["selection"]["candidate_count"]

        scan21 = evidence_dir / "screening-scan21"
        screening_scratch = temporary_dir / "scan21"
        screening_scratch.mkdir()
        pairs = screening_scratch / "field-access-pairs.jsonl"
        _run(
            binaries[names[0]],
            [
                str(scan21 / "parameter-stores.tsv"),
                str(scan21 / "parameter-loads.tsv"),
                "--program-id",
                PROGRAM_ID,
                "--output",
                str(pairs),
            ],
        )
        if pairs.read_bytes() != (scan21 / "field-access-pairs.jsonl").read_bytes():
            raise ValueError("scan21 field access pairs changed on replay")
        replayed_screening_roots += manifest["expanded_scan21_screen"]["selection"]["candidate_count"]

    return {
        **summary,
        "replayed_candidates": len(manifest["candidates"]),
        "replayed_screening_roots": replayed_screening_roots,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin-dir", type=Path, required=True, help="revenginstr virtualenv bin directory")
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    evidence_dir = arguments.repository_root / EVIDENCE_DIR
    summary = replay(evidence_dir, arguments.bin_dir)
    print(
        f"M2.3 frozen replay passed: {summary['replayed_candidates']} audit candidates, "
        f"{summary['replayed_screening_roots']} screening roots, {summary['artifacts']} artifacts, "
        f"{summary['bytes']} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
