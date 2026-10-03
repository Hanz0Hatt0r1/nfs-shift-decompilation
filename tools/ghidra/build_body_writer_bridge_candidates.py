#!/usr/bin/env python3
"""Classify fail-closed BODY state-writer bridge candidates from p-code access evidence.

Input is SHIFT.GhidraRegisterRelativeAccesses/1. The classifier deliberately
requires all participating offsets to occur in the same function and use the
same syntactic x86 base register. This is only a target-selection layer: it does
not prove that the register points to BODY, that two functions share an object,
or that any candidate is part of frame-to-frame integration.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.BodyWriterBridgeCandidates/1"
ACCESS_FORMAT = "SHIFT.GhidraRegisterRelativeAccesses/1"

LANES: dict[str, tuple[int, ...]] = {
    "origin": (0x00, 0x08, 0x10),
    "cross_vector": (0x18, 0x20, 0x28),
    "accumulator_a": (0x48, 0x50, 0x58),
    "accumulator_b": (0x60, 0x68, 0x70),
    "motion_triplet": (0x78, 0x80, 0x88),
    "basis": (0xD4, 0xD8, 0xDC, 0xE0, 0xE4, 0xE8, 0xEC, 0xF0, 0xF4),
}

ACCUMULATOR_OFFSETS = frozenset(LANES["accumulator_a"] + LANES["accumulator_b"])
MOTION_SIDE_OFFSETS = frozenset(LANES["cross_vector"] + LANES["motion_triplet"])
POSE_OFFSETS = frozenset(LANES["origin"] + LANES["basis"])


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != ACCESS_FORMAT:
        raise ValueError(f"{path}: expected {ACCESS_FORMAT}")
    accesses = value.get("accesses")
    if not isinstance(accesses, list):
        raise ValueError(f"{path}: accesses must be a list")
    return value


def _offset(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return None
    return None


def _is_read(access: str) -> bool:
    return access in {"read", "read-write"}


def _is_write(access: str) -> bool:
    return access in {"write", "read-write"}


def _lane_names(offset: int) -> list[str]:
    return [name for name, offsets in LANES.items() if offset in offsets]


def _evidence_rows(
    rows: Iterable[dict[str, Any]],
    offsets: frozenset[int],
    *,
    mode: str,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        displacement = _offset(row.get("displacement"))
        access = str(row.get("access") or "")
        if displacement not in offsets:
            continue
        if mode == "read" and not _is_read(access):
            continue
        if mode == "write" and not _is_write(access):
            continue
        result.append(
            {
                "instruction": row.get("instruction"),
                "instruction_text": row.get("instruction_text"),
                "access": access,
                "displacement": displacement,
                "displacement_hex": f"0x{displacement:x}" if displacement is not None else None,
                "lanes": _lane_names(displacement) if displacement is not None else [],
                "pcode_memory_ops": list(row.get("pcode_memory_ops") or []),
            }
        )
    result.sort(
        key=lambda row: (
            int(str(row.get("instruction") or "0x0"), 16),
            int(row.get("displacement") or 0),
        )
    )
    return result


def _candidate(
    *,
    kind: str,
    function: str,
    function_name: str | None,
    base_register: str,
    reads: list[dict[str, Any]],
    writes: list[dict[str, Any]],
) -> dict[str, Any]:
    read_offsets = sorted({int(row["displacement"]) for row in reads})
    write_offsets = sorted({int(row["displacement"]) for row in writes})
    return {
        "kind": kind,
        "function": function,
        "function_name": function_name,
        "base_register": base_register,
        "read_offsets": read_offsets,
        "read_offsets_hex": [f"0x{value:x}" for value in read_offsets],
        "write_offsets": write_offsets,
        "write_offsets_hex": [f"0x{value:x}" for value in write_offsets],
        "read_evidence": reads,
        "write_evidence": writes,
        "same_function": True,
        "same_base_register": True,
        "body_pointer_proven": False,
        "persistent_writer_proven": False,
        "promoted": False,
    }


def build_body_writer_bridge_candidates(access_report: dict[str, Any]) -> dict[str, Any]:
    if access_report.get("format") != ACCESS_FORMAT:
        raise ValueError(f"expected {ACCESS_FORMAT}")
    raw_accesses = access_report.get("accesses")
    if not isinstance(raw_accesses, list):
        raise ValueError("accesses must be a list")

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    malformed: list[dict[str, Any]] = []
    for index, row in enumerate(raw_accesses):
        if not isinstance(row, dict):
            malformed.append({"index": index, "reason": "access row is not an object"})
            continue
        function = row.get("function")
        base = row.get("base_register")
        displacement = _offset(row.get("displacement"))
        access = row.get("access")
        if (
            not isinstance(function, str)
            or not function
            or not isinstance(base, str)
            or not base
            or displacement is None
            or access not in {"read", "write", "read-write"}
        ):
            malformed.append(
                {
                    "index": index,
                    "function": function,
                    "base_register": base,
                    "displacement": row.get("displacement"),
                    "access": access,
                    "reason": "missing function/base/displacement or unsupported access kind",
                }
            )
            continue
        normalized = dict(row)
        normalized["displacement"] = displacement
        grouped[(function, base.upper())].append(normalized)

    candidates: list[dict[str, Any]] = []
    inspected_groups: list[dict[str, Any]] = []
    for (function, base), rows in sorted(grouped.items()):
        function_name = next(
            (str(row.get("function_name")) for row in rows if row.get("function_name")),
            None,
        )
        accumulator_reads = _evidence_rows(rows, ACCUMULATOR_OFFSETS, mode="read")
        motion_reads = _evidence_rows(rows, MOTION_SIDE_OFFSETS, mode="read")
        motion_writes = _evidence_rows(rows, MOTION_SIDE_OFFSETS, mode="write")
        pose_writes = _evidence_rows(rows, POSE_OFFSETS, mode="write")

        accumulator_to_motion = bool(accumulator_reads and motion_writes)
        motion_to_pose = bool(motion_reads and pose_writes)
        if accumulator_to_motion:
            candidates.append(
                _candidate(
                    kind="accumulator-to-motion",
                    function=function,
                    function_name=function_name,
                    base_register=base,
                    reads=accumulator_reads,
                    writes=motion_writes,
                )
            )
        if motion_to_pose:
            candidates.append(
                _candidate(
                    kind="motion-to-pose",
                    function=function,
                    function_name=function_name,
                    base_register=base,
                    reads=motion_reads,
                    writes=pose_writes,
                )
            )

        inspected_groups.append(
            {
                "function": function,
                "function_name": function_name,
                "base_register": base,
                "accumulator_read_count": len(accumulator_reads),
                "motion_read_count": len(motion_reads),
                "motion_write_count": len(motion_writes),
                "pose_write_count": len(pose_writes),
                "accumulator_to_motion_candidate": accumulator_to_motion,
                "motion_to_pose_candidate": motion_to_pose,
            }
        )

    by_group: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in candidates:
        by_group[(str(row["function"]), str(row["base_register"]))].add(str(row["kind"]))
    combined_groups = [
        {"function": function, "base_register": base_register}
        for (function, base_register), kinds in sorted(by_group.items())
        if {"accumulator-to-motion", "motion-to-pose"}.issubset(kinds)
    ]
    combined_functions = sorted({row["function"] for row in combined_groups})

    return {
        "format": FORMAT,
        "source_format": ACCESS_FORMAT,
        "lane_offsets": {
            name: [f"0x{value:x}" for value in offsets]
            for name, offsets in LANES.items()
        },
        "input_access_count": len(raw_accesses),
        "valid_access_count": sum(len(rows) for rows in grouped.values()),
        "malformed_access_count": len(malformed),
        "inspected_function_base_group_count": len(inspected_groups),
        "candidate_count": len(candidates),
        "accumulator_to_motion_candidate_count": sum(
            row["kind"] == "accumulator-to-motion" for row in candidates
        ),
        "motion_to_pose_candidate_count": sum(
            row["kind"] == "motion-to-pose" for row in candidates
        ),
        "combined_bridge_group_count": len(combined_groups),
        "combined_bridge_groups": combined_groups,
        "combined_bridge_function_count": len(combined_functions),
        "combined_bridge_functions": combined_functions,
        "candidates": candidates,
        "inspected_groups": inspected_groups,
        "malformed_accesses": malformed,
        "scope": {
            "requires_pcode_classified_access_input": True,
            "same_function_required": True,
            "same_syntactic_base_register_required": True,
            "combined_bridge_requires_same_base_register": True,
            "read_write_access_counts_as_read_and_write": True,
            "base_register_is_body_pointer": False,
            "pointer_aliases_across_functions_resolved": False,
            "body_or_vehicle_identity_proven": False,
            "field_semantics_promoted_beyond_existing_lane_contract": False,
            "persistent_state_writer_proven": False,
            "integration_order_proven": False,
            "note": (
                "Candidates are only functions where p-code-backed accesses show the required "
                "read/write lane pattern on the same syntactic base register. Independent pointer "
                "provenance and update-order evidence are still required before promoting any "
                "candidate to a BODY writer or integrator."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("register_accesses", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--fail-on-empty",
        action="store_true",
        help="return non-zero if no bridge candidates are found",
    )
    parser.add_argument(
        "--fail-on-malformed",
        action="store_true",
        help="return non-zero if malformed access rows are present",
    )
    args = parser.parse_args()

    access_report = _load(args.register_accesses)
    report = build_body_writer_bridge_candidates(access_report)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")

    print(f"format: {report['format']}")
    print(f"function/base groups: {report['inspected_function_base_group_count']}")
    print(f"bridge candidates: {report['candidate_count']}")
    print(f"accumulator -> motion: {report['accumulator_to_motion_candidate_count']}")
    print(f"motion -> pose: {report['motion_to_pose_candidate_count']}")
    print(f"combined bridge groups: {report['combined_bridge_group_count']}")
    print(f"combined bridge functions: {report['combined_bridge_function_count']}")
    print(f"malformed accesses: {report['malformed_access_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")

    if args.fail_on_malformed and report["malformed_access_count"]:
        return 2
    if args.fail_on_empty and not report["candidate_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
