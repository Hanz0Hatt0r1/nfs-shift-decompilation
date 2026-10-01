"""Promote a structural native participant boundary using exact runtime observations.

This join proves one concrete participant instance across the manager-registry
identity and IGPhaseVehicle selected-pointer slot while preserving the selector
ordinal as a separate identity domain.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.NativePhysicsParticipantRuntimeEvidence/1"
OBSERVATION_FORMAT = "SHIFT.NativePhysicsParticipantObservation/1"
BOUNDARY_FORMAT = "SHIFT.NativePhysicsParticipantBoundary/1"


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _canonical_pointer(value: Any, *, label: str) -> str:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a 32-bit pointer token")
    if isinstance(value, int):
        number = value
    else:
        text = str(value or "").strip().lower()
        try:
            number = int(text, 0)
        except ValueError as exc:
            raise ValueError(
                f"{label} must be a 32-bit pointer token"
            ) from exc
    if number <= 0 or number > 0xFFFFFFFF:
        raise ValueError(f"{label} must be a non-zero 32-bit pointer token")
    return f"0x{number:08x}"


def _i32(value: Any, *, label: str, unresolved: int | None = None) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an integer") from exc
    if number < -0x80000000 or number > 0x7FFFFFFF:
        raise ValueError(f"{label} must fit signed 32-bit")
    if unresolved is not None and number == unresolved:
        raise ValueError(f"{label} remains unresolved")
    return number


def _require_boundary(boundary: Mapping[str, Any]) -> None:
    if boundary.get("format") != BOUNDARY_FORMAT:
        raise ValueError(f"boundary must be {BOUNDARY_FORMAT}")
    if boundary.get("ready") is not True:
        raise ValueError("structural participant boundary is not ready")
    if boundary.get("registry_contract_ready") is not True:
        raise ValueError("participant registry contract is not ready")
    if boundary.get("participant_gate_ready") is not True:
        raise ValueError("participant gate is not ready")
    if boundary.get("participant_process_ready") is not True:
        raise ValueError("participant process contract is not ready")
    if boundary.get("selector_context_ready") is not True:
        raise ValueError("selector context is not ready")
    if boundary.get("registry_manager_global") != "DAT_00c109e0":
        raise ValueError("participant manager global mismatch")
    if boundary.get("selector_global") != "DAT_00bbc600":
        raise ValueError("selector global mismatch")
    if boundary.get("selector_context_separate") is not True:
        raise ValueError("manager/selector separation is not preserved")
    if int(boundary.get("registry_slot_stride") or 0) != 0x1FA0:
        raise ValueError("registry slot stride mismatch")
    if int(boundary.get("participant_descriptor_type") or 0) != 3:
        raise ValueError("participant descriptor type mismatch")
    if int(boundary.get("registry_index_source_offset") or 0) != 0x3C:
        raise ValueError("registry index source offset mismatch")
    if int(boundary.get("selector_candidate_ready_offset") or 0) != 0x74:
        raise ValueError("selector candidate-ready offset mismatch")
    if boundary.get("registry_selector_identity_join_proven") is not False:
        raise ValueError("structural boundary already overclaims identity join")
    if boundary.get("participant_instance_ready") is not False:
        raise ValueError("structural boundary already overclaims participant instance")
    if int(boundary.get("participant_registry_index", -2)) != -1:
        raise ValueError("structural boundary registry index must be unresolved")
    if int(boundary.get("selector_ordinal", -2)) != -1:
        raise ValueError("structural boundary selector ordinal must be unresolved")
    if int(boundary.get("participant_process_state", -2)) != -1:
        raise ValueError("structural boundary process state must be unresolved")


def build_native_physics_participant_runtime_evidence(
    boundary: Mapping[str, Any],
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    _require_boundary(boundary)

    if observation.get("format") != OBSERVATION_FORMAT:
        raise ValueError(f"observation must be {OBSERVATION_FORMAT}")
    if observation.get("ready") is not True:
        raise ValueError("runtime participant observation is not ready")

    manager = observation.get("manager_registry")
    selected = observation.get("igphasevehicle_selection")
    selector = observation.get("selector")
    if not isinstance(manager, Mapping):
        raise ValueError("manager_registry observation is missing")
    if not isinstance(selected, Mapping):
        raise ValueError("igphasevehicle_selection observation is missing")
    if not isinstance(selector, Mapping):
        raise ValueError("selector observation is missing")

    if manager.get("global_instance") != "DAT_00c109e0":
        raise ValueError("observed participant manager global mismatch")
    if selector.get("global_instance") != "DAT_00bbc600":
        raise ValueError("observed selector global mismatch")
    if manager.get("registry_index_source") != "PhysicsParticipant+0x3c":
        raise ValueError("observed registry index source mismatch")
    if int(manager.get("registry_index_source_offset") or 0) != 0x3C:
        raise ValueError("observed registry index source offset mismatch")
    if int(manager.get("participant_descriptor_type") or 0) != 3:
        raise ValueError("observed participant descriptor type mismatch")
    if int(selector.get("candidate_ready_offset") or 0) != 0x74:
        raise ValueError("observed selector candidate-ready offset mismatch")
    if int(selector.get("candidate_ready_value", -1)) != 0:
        raise ValueError("observed selector candidate is not ready")

    if selected.get("pointer_slot") != "IGPhaseVehicle+0x450":
        raise ValueError("observed participant pointer slot mismatch")
    if selected.get("ordinal_slot") != "IGPhaseVehicle+0x454":
        raise ValueError("observed selector ordinal slot mismatch")
    if selected.get("state_slot") != "IGPhaseVehicle+0x45c":
        raise ValueError("observed participant process-state slot mismatch")

    manager_pointer = _canonical_pointer(
        manager.get("participant_pointer_token"),
        label="manager participant pointer",
    )
    selected_pointer = _canonical_pointer(
        selected.get("participant_pointer_token"),
        label="selected participant pointer",
    )
    if manager_pointer != selected_pointer:
        raise ValueError(
            "manager registry participant and IGPhaseVehicle selected participant differ"
        )

    registry_index = _i32(
        manager.get("registry_index"),
        label="participant registry index",
        unresolved=-1,
    )
    if registry_index < 0:
        raise ValueError("participant registry index must be non-negative")
    selector_ordinal = _i32(
        selected.get("selector_ordinal"),
        label="selector ordinal",
        unresolved=-1,
    )
    if selector_ordinal < 0:
        raise ValueError("selector ordinal must be non-negative")
    process_state = _i32(
        selected.get("process_state"),
        label="participant process state",
        unresolved=-1,
    )

    observation_join = observation.get("join")
    if not isinstance(observation_join, Mapping):
        raise ValueError("runtime participant join evidence is missing")
    if observation_join.get("same_participant_pointer_proven") is not True:
        raise ValueError("same participant pointer is not independently proven")
    if observation_join.get("manager_registry_identity_observed") is not True:
        raise ValueError("manager registry identity is not observed")
    if observation_join.get("igphasevehicle_selection_observed") is not True:
        raise ValueError("IGPhaseVehicle selection is not observed")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "verification_scope": observation.get("verification_scope"),
        "registry_contract_ready": True,
        "participant_gate_ready": True,
        "participant_process_ready": True,
        "selector_context_ready": True,
        "registry_manager_global": "DAT_00c109e0",
        "selector_global": "DAT_00bbc600",
        "selector_context_separate": True,
        "registry_slot_array_offset": int(
            boundary.get("registry_slot_array_offset") or 0
        ),
        "registry_slot_count_offset": int(
            boundary.get("registry_slot_count_offset") or 0
        ),
        "registry_slot_stride": int(boundary["registry_slot_stride"]),
        "participant_descriptor_type": int(
            boundary["participant_descriptor_type"]
        ),
        "registry_index_source": "PhysicsParticipant+0x3c",
        "registry_index_source_offset": 0x3C,
        "participant_pointer_slot": "IGPhaseVehicle+0x450",
        "participant_ordinal_slot": "IGPhaseVehicle+0x454",
        "participant_state_slot": "IGPhaseVehicle+0x45c",
        "selector_candidate_ready_offset": 0x74,
        "registry_selector_identity_join_proven": True,
        "participant_instance_ready": True,
        "participant_registry_index": registry_index,
        "selector_ordinal": selector_ordinal,
        "participant_process_state": process_state,
        # Legacy aliases remain inactive because the two integer identity
        # domains are still not equivalent.
        "participant_index": -1,
        "participant_mode": -1,
        "participant_pointer_token": manager_pointer,
        "join_evidence": {
            "same_participant_pointer_proven": True,
            "manager_registry_identity_observed": True,
            "igphasevehicle_selection_observed": True,
            "registry_index_equals_selector_ordinal": False,
        },
        "source_contracts": dict(boundary.get("source_contracts") or {}),
        "boundary": {
            "native_state_runtime_instance_admission": True,
            "selected_runtime_instance_proven": True,
            "selected_provider_proven": False,
            "numeric_physics_equivalence_proven": False,
            "manager_selector_same_object_claimed": False,
            "registry_index_equals_selector_ordinal": False,
            "registry_selector_identity_join_proven": True,
            "legacy_participant_index_alias_active": False,
            "participant_pointer_transport_policy": (
                "evidence token only; native runtime never dereferences it"
            ),
        },
        "limitations": [
            "Registry index and selector ordinal remain distinct numeric identity domains.",
            "The observed pointer token is provenance only and is never dereferenced by native_runtime.",
            "No PhysX/provider class identity is assigned.",
            "No provider selection or numerical solver parity is claimed.",
        ],
    }


def build_native_physics_participant_runtime_evidence_file(
    boundary_path: str | Path,
    observation_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    boundary = json.loads(Path(boundary_path).read_text(encoding="utf-8"))
    observation = json.loads(Path(observation_path).read_text(encoding="utf-8"))
    if not isinstance(boundary, Mapping):
        raise ValueError("boundary JSON must be an object")
    if not isinstance(observation, Mapping):
        raise ValueError("observation JSON must be an object")

    report = build_native_physics_participant_runtime_evidence(
        boundary,
        observation,
    )
    report["provenance"] = {
        "structural_boundary_sha256": _sha256_file(boundary_path),
        "runtime_observation_sha256": _sha256_file(observation_path),
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("boundary")
    parser.add_argument("observation")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = build_native_physics_participant_runtime_evidence_file(
        args.boundary,
        args.observation,
        args.output,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "participant_registry_index": report[
            "participant_registry_index"
        ],
        "selector_ordinal": report["selector_ordinal"],
        "participant_process_state": report[
            "participant_process_state"
        ],
        "verification_scope": report.get("verification_scope"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "FORMAT",
    "OBSERVATION_FORMAT",
    "build_native_physics_participant_runtime_evidence",
    "build_native_physics_participant_runtime_evidence_file",
]
