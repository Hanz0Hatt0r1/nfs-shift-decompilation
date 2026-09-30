"""Bridge one runtime-observed IGPhaseVehicle participant selection into native_runtime.

Phase 505/508/509 prove the selector path, writeback slots and waiting/success
control flow. They do not prove the runtime identity of a concrete participant
instance and do not join DAT_00bbc600 to the separate DAT_00c109e0
PhysicsParticipantManager registry.

This module therefore requires an explicit runtime observation of the selector
result. Pointer identity is reduced to a presence bit and is never transported
into the native ABI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from vehicle_physics_participant_gate_runtime import (
    build_vehicle_physics_participant_gate,
)
from vehicle_physics_participant_process_runtime import (
    build_vehicle_physics_participant_process,
)
from vehicle_physics_selector_context_runtime import (
    build_vehicle_physics_selector_context,
)

OBSERVATION_FORMAT = "SHIFT.VehiclePhysicsParticipantSelectionObservation/1"
FORMAT = "SHIFT.NativePhysicsParticipantBridge/1"


def _i32(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer") from exc
    if result < -(1 << 31) or result > (1 << 31) - 1:
        raise ValueError(f"{field} exceeds int32")
    return result


def _source_contract() -> dict[str, Any]:
    gate = build_vehicle_physics_participant_gate()
    selector = build_vehicle_physics_selector_context()
    process = build_vehicle_physics_participant_process()

    if (
        gate.get("ready") is not True
        or selector.get("ready") is not True
        or process.get("ready") is not True
    ):
        raise ValueError("source participant contracts are not ready")

    gate_selection = gate.get("selection") or {}
    selector_context = selector.get("context") or {}
    separation = selector.get("separation") or {}
    process_owner = process.get("owner") or {}
    process_selection = process.get("selection_step") or {}

    expected = {
        "selector_global": "DAT_00bbc600",
        "selector_function": "FUN_00410ef0",
        "pointer_slot": "IGPhaseVehicle+0x450",
        "ordinal_slot": "IGPhaseVehicle+0x454",
        "phase_state_slot": "IGPhaseVehicle+0x45c",
        "waiting_ordinal": -1,
        "participant_manager_global": "DAT_00c109e0",
    }

    checks = {
        "selector_global": selector_context.get("global_instance"),
        "selector_function_gate": gate_selection.get("callee"),
        "selector_function_process": process_selection.get(
            "selector_function"
        ),
        "pointer_slot_gate": gate_selection.get(
            "returned_pointer_slot"
        ),
        "pointer_slot_process": process_owner.get("pointer_slot"),
        "ordinal_slot_gate": gate_selection.get(
            "returned_ordinal_slot"
        ),
        "ordinal_slot_process": process_owner.get("ordinal_slot"),
        "phase_state_slot_gate": (
            (gate.get("post_success") or {}).get("phase_state_field")
        ),
        "phase_state_slot_process": process_owner.get("state_slot"),
        "waiting_ordinal": gate_selection.get("failure_value"),
        "manager_global": separation.get("participant_manager_global"),
        "selector_manager_same_object": separation.get(
            "same_object_proven"
        ),
    }

    mismatches: list[str] = []
    if checks["selector_global"] != expected["selector_global"]:
        mismatches.append("selector-global")
    if checks["selector_function_gate"] != expected["selector_function"]:
        mismatches.append("selector-function-gate")
    if checks["selector_function_process"] != expected["selector_function"]:
        mismatches.append("selector-function-process")
    if checks["pointer_slot_gate"] != expected["pointer_slot"]:
        mismatches.append("pointer-slot-gate")
    if checks["pointer_slot_process"] != expected["pointer_slot"]:
        mismatches.append("pointer-slot-process")
    if checks["ordinal_slot_gate"] != expected["ordinal_slot"]:
        mismatches.append("ordinal-slot-gate")
    if checks["ordinal_slot_process"] != expected["ordinal_slot"]:
        mismatches.append("ordinal-slot-process")
    if checks["phase_state_slot_gate"] != expected["phase_state_slot"]:
        mismatches.append("phase-state-slot-gate")
    if checks["phase_state_slot_process"] != expected["phase_state_slot"]:
        mismatches.append("phase-state-slot-process")
    if checks["waiting_ordinal"] != expected["waiting_ordinal"]:
        mismatches.append("waiting-ordinal")
    if checks["manager_global"] != expected["participant_manager_global"]:
        mismatches.append("manager-global")
    if checks["selector_manager_same_object"] is not False:
        mismatches.append("selector-manager-separation")

    if mismatches:
        raise ValueError(
            "source participant contract mismatch: "
            + ",".join(mismatches)
        )

    return {
        **expected,
        "source_formats": [
            gate.get("format"),
            selector.get("format"),
            process.get("format"),
        ],
        "selector_manager_same_object_proven": False,
    }


def build_participant_selection_observation(
    *,
    ordinal: int,
    pointer_present: bool,
    phase_state: int,
    capture_source: str,
    capture_frame: int,
) -> dict[str, Any]:
    """Normalize one observed +0x450/+0x454/+0x45c state."""
    source = _source_contract()
    ordinal_value = _i32(ordinal, "ordinal")
    phase_state_value = _i32(phase_state, "phase_state")
    frame = _i32(capture_frame, "capture_frame")
    if frame < 0:
        raise ValueError("capture_frame must be non-negative")

    capture_source = str(capture_source or "").strip()
    if not capture_source:
        raise ValueError("capture_source is required")

    if ordinal_value == source["waiting_ordinal"]:
        if pointer_present:
            raise ValueError(
                "waiting ordinal -1 cannot carry a selected pointer"
            )
        status = "waiting"
    elif ordinal_value < 0:
        raise ValueError(
            "participant ordinal must be -1 or non-negative"
        )
    else:
        if not pointer_present:
            raise ValueError(
                "successful participant ordinal requires pointer presence"
            )
        status = "selected"

    return {
        "format": OBSERVATION_FORMAT,
        "version": 1,
        "status": status,
        "ready": status == "selected",
        "blocking_reasons": (
            []
            if status == "selected"
            else ["physics-participant:selector-returned-waiting"]
        ),
        "source_identity": {
            "selector_global": source["selector_global"],
            "selector_function": source["selector_function"],
            "pointer_slot": source["pointer_slot"],
            "ordinal_slot": source["ordinal_slot"],
            "phase_state_slot": source["phase_state_slot"],
        },
        "observation": {
            "ordinal": ordinal_value,
            "pointer_present": bool(pointer_present),
            "phase_state": phase_state_value,
        },
        "provenance": {
            "capture_source": capture_source,
            "capture_frame": frame,
            "runtime_observed": True,
        },
        "boundary": {
            "pointer_value_serialized": False,
            "pointer_identity_inferred": False,
            "provider_identity_inferred": False,
            "selector_manager_registry_joined": False,
        },
    }


def build_native_physics_participant_bridge(
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    if observation.get("format") != OBSERVATION_FORMAT:
        raise ValueError(
            "input must be "
            "SHIFT.VehiclePhysicsParticipantSelectionObservation/1"
        )

    source = _source_contract()
    identity = observation.get("source_identity")
    identity = identity if isinstance(identity, Mapping) else {}
    for field in (
        "selector_global",
        "selector_function",
        "pointer_slot",
        "ordinal_slot",
        "phase_state_slot",
    ):
        if identity.get(field) != source[field]:
            raise ValueError(
                f"participant observation source mismatch: {field}"
            )

    provenance = observation.get("provenance")
    provenance = provenance if isinstance(provenance, Mapping) else {}
    if provenance.get("runtime_observed") is not True:
        raise ValueError(
            "participant observation is not runtime-observed"
        )
    capture_source = str(
        provenance.get("capture_source") or ""
    ).strip()
    if not capture_source:
        raise ValueError(
            "participant observation capture_source is missing"
        )
    frame = _i32(
        provenance.get("capture_frame"),
        "capture_frame",
    )
    if frame < 0:
        raise ValueError("capture_frame must be non-negative")

    payload = observation.get("observation")
    payload = payload if isinstance(payload, Mapping) else {}
    ordinal = _i32(payload.get("ordinal"), "ordinal")
    phase_state = _i32(
        payload.get("phase_state"),
        "phase_state",
    )
    pointer_present = payload.get("pointer_present")
    if not isinstance(pointer_present, bool):
        raise ValueError("pointer_present must be boolean")

    if ordinal == source["waiting_ordinal"]:
        if pointer_present:
            raise ValueError(
                "waiting observation cannot carry pointer presence"
            )
        return {
            "format": FORMAT,
            "version": 1,
            "status": "waiting",
            "ready": False,
            "blocking_reasons": [
                "native-physics-participant:waiting-for-selection"
            ],
            "native_participant_ready": False,
            "native_participant_index": -1,
            "native_participant_phase_state": phase_state,
            "native_participant_mode": -1,
            "source_observation_status": observation.get("status"),
            "source": {
                **source,
                "capture_source": capture_source,
                "capture_frame": frame,
            },
            "boundary": {
                "participant_pointer_transport": "not-performed",
                "participant_mode_semantics_proven": False,
                "provider_identity_inferred": False,
                "provider_numerics_executed": False,
                "selector_manager_registry_joined": False,
            },
        }

    if ordinal < 0 or not pointer_present:
        raise ValueError(
            "selected participant requires non-negative ordinal "
            "and pointer presence"
        )
    if observation.get("ready") is not True:
        raise ValueError(
            "selected participant observation is not ready"
        )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "native_participant_ready": True,
        "native_participant_index": ordinal,
        "native_participant_phase_state": phase_state,
        # The existing native field is intentionally left unresolved. The
        # source contracts prove +0x45c as phase state, not participant mode.
        "native_participant_mode": -1,
        "participant_pointer_observed": True,
        "source": {
            **source,
            "capture_source": capture_source,
            "capture_frame": frame,
        },
        "boundary": {
            "participant_pointer_transport": "not-performed",
            "participant_pointer_presence_only": True,
            "participant_mode_semantics_proven": False,
            "provider_identity_inferred": False,
            "provider_numerics_executed": False,
            "selector_manager_registry_joined": False,
            "native_tick_integration_semantics_inferred": False,
        },
    }


def validate_observation_file(
    observation_path: str | Path,
) -> dict[str, Any]:
    value = json.loads(
        Path(observation_path).read_text(encoding="utf-8")
    )
    if not isinstance(value, Mapping):
        raise ValueError("participant observation JSON must be an object")
    return build_native_physics_participant_bridge(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    observed = sub.add_parser(
        "observation",
        help="build a normalized runtime selector observation",
    )
    observed.add_argument("--ordinal", required=True, type=int)
    observed.add_argument(
        "--pointer-present",
        action="store_true",
    )
    observed.add_argument("--phase-state", required=True, type=int)
    observed.add_argument("--capture-source", required=True)
    observed.add_argument("--capture-frame", required=True, type=int)
    observed.add_argument("-o", "--output", required=True)

    bridge = sub.add_parser(
        "bridge",
        help="build a native participant bridge from an observation",
    )
    bridge.add_argument("observation")
    bridge.add_argument("output")

    args = parser.parse_args(argv)
    if args.command == "observation":
        report = build_participant_selection_observation(
            ordinal=args.ordinal,
            pointer_present=args.pointer_present,
            phase_state=args.phase_state,
            capture_source=args.capture_source,
            capture_frame=args.capture_frame,
        )
    else:
        report = validate_observation_file(args.observation)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
