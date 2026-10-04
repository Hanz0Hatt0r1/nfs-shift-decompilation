#!/usr/bin/env python3
"""Fail closed on the retracted BMW offset33b additional-mass zero proof.

PR #1247 confused the PhysicsParticipant manager record with the separately
allocated PhysicsParticipant object stored in record[0].  The manager-record
constructor/reset path can prove zeros inside the 0x1fa0 manager record, but the
source-backed HighDetailVehicle init reads ``*(record[0] + 0xba0)``.  Therefore
that proof cannot establish the additional-mass value consumed by
``FUN_0076b280``.

Keep this historical entry point so any downstream invocation fails closed and
receives the corrected object frontier instead of silently reusing the invalid
``SHIFT.BMWOffset33bAdditionalMassBootstrapZero/1`` claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.BMWOffset33bAdditionalMassActualObjectFrontier/1"
RETRACTED_FORMAT = "SHIFT.BMWOffset33bAdditionalMassBootstrapZero/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

MANAGER_RECORD_STRIDE = 0x1FA0
ACTUAL_PARTICIPANT_ALLOCATION_SIZE = 0x2B90
VEHICLE_EMBEDDED_OFFSET = 0x340
PARTICIPANT_ADDITIONAL_MASS_OFFSET = 0xBA0
VEHICLE_ADDITIONAL_MASS_OFFSET = 0x860


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def _validate_binary(root: Path) -> dict[str, Any]:
    binary = _read_json(root / "binary.json")
    if binary.get("program_name") != PROGRAM:
        raise ValueError("unexpected retail program name")
    if binary.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable identity")
    return binary


def analyze_bmw_offset33b_additional_mass_bootstrap_zero(root: Path) -> dict[str, Any]:
    _validate_binary(root)

    if PARTICIPANT_ADDITIONAL_MASS_OFFSET - VEHICLE_EMBEDDED_OFFSET != VEHICLE_ADDITIONAL_MASS_OFFSET:
        raise AssertionError("participant/Vehicle target alias relation drift")

    return {
        "format": FORMAT,
        "ready": False,
        "status": "additional-mass-actual-object-producer-unresolved",
        "retail": {
            "program": PROGRAM,
            "pe_md5": PE_MD5,
        },
        "correction": {
            "retracted_contract": RETRACTED_FORMAT,
            "retracted_ready_claim": True,
            "reason": (
                "the previous proof applied FUN_00714360/FUN_00552dd0 to the 0x1fa0 "
                "PhysicsParticipant manager record, while HighDetailVehicle::Init reads "
                "offset +0xba0 from the separately allocated object stored in record[0]"
            ),
            "manager_record_and_actual_participant_are_distinct_objects": True,
            "manager_record_stride": MANAGER_RECORD_STRIDE,
            "actual_participant_allocation_size": ACTUAL_PARTICIPANT_ALLOCATION_SIZE,
            "manager_record_allocator_path": {
                "function": "FUN_007125e0",
                "allocation_size": ACTUAL_PARTICIPANT_ALLOCATION_SIZE,
                "actual_object_constructor": "FUN_0072ed20",
                "stored_as": "record[0]",
            },
            "actual_object_vehicle_construction": {
                "actual_object_constructor": "FUN_0072ed20",
                "vehicle_constructor": "FUN_0079c1c0",
                "vehicle_argument": "actual_participant + 0x340",
            },
            "source_backed_consumer": {
                "high_detail_vehicle_init_storage": "HDVehicle+0x3428",
                "source_expression": "*(float *)(*record + 0xba0)",
                "actual_participant_storage": "actual_participant+0xba0",
                "vehicle_alias_storage": "Vehicle+0x860",
                "offset33b_producer": "FUN_0076b280",
            },
            "manager_record_zero_helper_proves_target_value": False,
            "additional_mass_zero_value_proven": False,
        },
        "next_proof": {
            "target": "actual PhysicsParticipant+0xba0 / embedded Vehicle+0x860 producer",
            "constructor_chain": [
                "FUN_007125e0 allocates 0x2b90 bytes",
                "FUN_0072ed20 constructs the actual PhysicsParticipant",
                "FUN_0079c1c0 constructs embedded Vehicle at actual_participant+0x340",
            ],
            "required_result": (
                "prove the last writer/value reaching Vehicle+0x860 before "
                "HighDetailVehicle::Init copies it into HDVehicle+0x3428"
            ),
        },
        "scope": {
            "original_game_executed": False,
            "runtime_witness_required_yet": False,
            "historical_invalid_zero_contract_must_not_be_consumed": True,
        },
        "gates": {
            "offset33b_additional_mass_bootstrap_zero_ready": False,
            "offset33b_additional_mass_term_can_be_elided_for_first_bootstrap": False,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": [
            "actual-participant+0xba0 / Vehicle+0x860 producer remains unresolved",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Retract the invalid manager-record BMW offset33b zero proof and emit the "
            "actual PhysicsParticipant producer frontier"
        )
    )
    parser.add_argument("ghidra_export", type=Path, help="retail Ghidra export root")
    parser.add_argument("--json-out", type=Path, default=None, help="write corrected frontier JSON")
    args = parser.parse_args()

    try:
        report = analyze_bmw_offset33b_additional_mass_bootstrap_zero(args.ghidra_export)
    except (OSError, ValueError, AssertionError) as exc:
        parser.error(str(exc))

    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
