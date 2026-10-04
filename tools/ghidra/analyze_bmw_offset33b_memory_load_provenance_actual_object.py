#!/usr/bin/env python3
"""Run the proven BMW offset33b memory-LOAD engine with the actual-object zero proof.

The original ``analyze_bmw_offset33b_memory_load_provenance.py`` was authored
before the manager-record object-base mistake was discovered.  Its p-code and
register-provenance engine remains useful, but its additional-mass validator
accepts the retracted contract.  This adapter preserves the tested engine while
admitting only ``SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1``.

No manager-record +0xba0 claim is accepted or reconstructed here.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_bmw_offset33b_memory_load_provenance as _legacy

FORMAT = _legacy.FORMAT
ACTUAL_ADDITIONAL_MASS_FORMAT = "SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def validate_actual_additional_mass_proof(path: Path) -> dict[str, Any]:
    report = _read_json(path)
    if report.get("format") != ACTUAL_ADDITIONAL_MASS_FORMAT:
        raise ValueError(f"{path}: expected {ACTUAL_ADDITIONAL_MASS_FORMAT}")
    if report.get("ready") is not True:
        raise ValueError("actual additional-mass bootstrap-zero proof is not ready")

    object_graph = report.get("object_graph")
    if not isinstance(object_graph, Mapping):
        raise ValueError("actual additional-mass object graph missing")
    if int(object_graph.get("actual_participant_allocation_size", -1)) != 0x2B90:
        raise ValueError("actual participant allocation size drift")
    if int(object_graph.get("embedded_vehicle_offset", -1)) != 0x340:
        raise ValueError("embedded Vehicle offset drift")
    if int(object_graph.get("participant_additional_mass_offset", -1)) != 0xBA0:
        raise ValueError("actual participant additional-mass offset drift")
    if int(object_graph.get("vehicle_additional_mass_offset", -1)) != 0x860:
        raise ValueError("Vehicle additional-mass offset drift")
    if object_graph.get("manager_record_plus_0xba0_is_not_the_proven_storage") is not True:
        raise ValueError("actual-object proof does not reject manager-record +0xba0")

    allocation = report.get("allocation_proof")
    if not isinstance(allocation, Mapping):
        raise ValueError("actual additional-mass allocation proof missing")
    if int(allocation.get("requested_flags", -1)) != 0x20:
        raise ValueError("actual participant zero-fill allocation flag drift")
    if allocation.get("zero_fill_operation") != "memset(allocation, 0, requested_size)":
        raise ValueError("actual participant allocator zero-fill semantics drift")

    value = report.get("proven_value")
    if not isinstance(value, Mapping):
        raise ValueError("actual additional-mass proven value missing")
    if value.get("type") != "float32":
        raise ValueError("actual additional-mass value type drift")
    if value.get("bits") != "0x00000000" or float(value.get("value", 1.0)) != 0.0:
        raise ValueError("actual additional-mass value is not exact +0.0f")

    handoff = report.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("actual additional-mass handoff missing")
    if handoff.get("offset33b_actual_additional_mass_bootstrap_zero_ready") is not True:
        raise ValueError("actual additional-mass zero gate is not ready")
    if handoff.get("offset33b_additional_mass_term_can_be_elided_for_first_bootstrap") is not True:
        raise ValueError("actual additional-mass term is not proven elidable")
    if handoff.get("BMW_numeric_offset33b_ready") is not False:
        raise ValueError("actual additional-mass proof unexpectedly preclaims numeric offset33b")
    if handoff.get("vehicle_world_transform_ready") is not False:
        raise ValueError("actual additional-mass proof unexpectedly preclaims world transform")

    scope = report.get("scope")
    if not isinstance(scope, Mapping):
        raise ValueError("actual additional-mass scope missing")
    if scope.get("retracted_manager_record_zero_claim_reused") is not False:
        raise ValueError("retracted manager-record zero claim was reused")
    return report


def _legacy_semantic_shape(actual: Mapping[str, Any]) -> dict[str, Any]:
    graph = actual["object_graph"]
    value = actual["proven_value"]
    return {
        "proof": {
            "offset33b_root": {
                "semantic_name": "actual PhysicsParticipant additional mass",
                "participant_storage": "actual_participant+0xba0",
                "vehicle_alias_storage": "embedded_vehicle+0x860",
                "value_type": value["type"],
                "value": value["value"],
                "numeric_value_proven": True,
            },
            "storage_alias": {
                "participant_additional_mass_offset": graph["participant_additional_mass_offset"],
                "vehicle_additional_mass_offset": graph["vehicle_additional_mass_offset"],
            },
        }
    }


def analyze(
    store_provenance_path: Path,
    instruction_export: Path,
    actual_additional_mass_proof_path: Path,
) -> dict[str, Any]:
    actual = validate_actual_additional_mass_proof(actual_additional_mass_proof_path)
    normalized = _legacy_semantic_shape(actual)

    original_validator = _legacy._validate_additional_mass_proof
    _legacy._validate_additional_mass_proof = lambda _path: normalized
    try:
        report = _legacy.analyze_bmw_offset33b_memory_load_provenance(
            store_provenance_path,
            instruction_export,
            actual_additional_mass_proof_path,
        )
    finally:
        _legacy._validate_additional_mass_proof = original_validator

    if report.get("format") != FORMAT:
        raise ValueError("legacy memory-LOAD engine format drift")

    reduction = report.get("known_semantic_reductions", {}).get("additional_mass_first_bootstrap")
    if not isinstance(reduction, dict):
        raise ValueError("memory-LOAD output lost additional-mass semantic reduction")
    reduction["proof_format"] = ACTUAL_ADDITIONAL_MASS_FORMAT
    reduction["proof_object_base"] = "actual PhysicsParticipant"
    reduction["manager_record_plus_0xba0_reused"] = False

    handoff = report.setdefault("handoff", {})
    handoff["offset33b_additional_mass_bootstrap_zero_proof_consumed"] = False
    handoff["offset33b_actual_additional_mass_bootstrap_zero_proof_consumed"] = True

    scope = report.setdefault("scope", {})
    scope["historical_manager_record_zero_proof_consumed"] = False
    scope["actual_object_allocator_zero_proof_consumed"] = True

    inputs = report.setdefault("inputs", {})
    inputs["actual_additional_mass_proof"] = str(actual_additional_mass_proof_path)
    inputs.pop("additional_mass_proof", None)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("store_provenance", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("actual_additional_mass_proof", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = analyze(
        args.store_provenance,
        args.instruction_export,
        args.actual_additional_mass_proof,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out is None:
        print(text, end="")
    else:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
