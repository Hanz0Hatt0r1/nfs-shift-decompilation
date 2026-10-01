"""Correlate retail FUN_00757d2c mutation events with solver timeline anchors.

Phase 636 consumes the Phase 635 mutation JSONL stream plus full-probe frame,
solve, reset and post-solve captures. It validates the recovered slot/body
contract again and produces a fail-closed timing evidence manifest without
changing the native scheduler.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from sdf_runtime_probe_runtime import (
    FUNCTIONS,
    RELATION_STATE_MUTATION_LAYOUT,
    RELATION_STATE_MUTATION_SLOT_NAMES,
)

FORMAT = "SHIFT.ConstraintRelationStateMutationEvidenceRuntime/1"

_SOLVE_ENTRY_KINDS = {
    "builtin-solve-entry",
    "provider-solve-entry",
}


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _positive_int(value: Any) -> int | None:
    if not _is_int(value):
        return None
    value = int(value)
    return value if value > 0 else None


def _nonnegative_int(value: Any) -> int | None:
    if not _is_int(value):
        return None
    value = int(value)
    return value if value >= 0 else None


def validate_relation_state_mutation_event(
    event: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    if event.get("format") != "SHIFT.ConstraintRelationStateMutationCaptureRuntime/1":
        errors.append("format")
    if event.get("version") != 1:
        errors.append("version")
    if event.get("status") != "captured":
        errors.append("status")
    if event.get("source_function") != "FUN_00757d2c":
        errors.append("source-function")
    if event.get("source_address") != FUNCTIONS["relation_state_mutation"]:
        errors.append("source-address")
    if event.get("ready") is not True:
        errors.append("capture-not-ready")
    if event.get("body_pointer_capture_skipped") is not False:
        errors.append("body-pointer-capture-skipped")
    if event.get("capture_errors"):
        errors.append("capture-errors-present")

    slot = _nonnegative_int(event.get("component_slot"))
    if slot is None or slot >= RELATION_STATE_MUTATION_LAYOUT["component_count"]:
        errors.append("component-slot")
        slot = None

    component_offset = _nonnegative_int(event.get("component_offset"))
    if slot is not None:
        expected_offset = (
            slot * RELATION_STATE_MUTATION_LAYOUT["component_stride"]
        )
        if component_offset != expected_offset:
            errors.append("component-offset")

        if event.get("component_slot_name") != RELATION_STATE_MUTATION_SLOT_NAMES[slot]:
            errors.append("component-slot-name")

    vehicle_pointer = _nonnegative_int(event.get("vehicle_pointer"))
    component_block_pointer = _nonnegative_int(
        event.get("component_block_pointer")
    )
    if vehicle_pointer is None:
        errors.append("vehicle-pointer")
    if component_offset is None:
        errors.append("component-offset")
    if (
        vehicle_pointer is not None
        and component_offset is not None
        and component_block_pointer
        != vehicle_pointer
        + RELATION_STATE_MUTATION_LAYOUT["component_base_offset"]
        + component_offset
    ):
        errors.append("component-block-pointer")

    spindle_pointer = _nonnegative_int(
        event.get("spindle_body_pointer")
    )
    spindle_present = event.get("spindle_body_present")
    if not isinstance(spindle_present, bool):
        errors.append("spindle-presence")
    else:
        expected_branch = (
            "spindle-bar-endpoint"
            if spindle_present
            else "wheel-rear-axle-pair"
        )
        if event.get("source_branch") != expected_branch:
            errors.append("source-branch")
        if spindle_pointer is not None:
            if spindle_present != (spindle_pointer != 0):
                errors.append("spindle-pointer-presence")

    for name in (
        "wheel_body_pointer",
        "spindle_body_pointer",
        "rear_axle_body_pointer",
        "caller_return_address",
    ):
        if _nonnegative_int(event.get(name)) is None:
            errors.append(name.replace("_", "-"))

    event_sequence = _positive_int(event.get("runtime_event_sequence"))
    if event_sequence is None:
        errors.append("runtime-event-sequence")

    frame_index = _positive_int(event.get("frame_index"))
    if frame_index is None:
        errors.append("frame-index")

    frame_entry_sequence = _positive_int(
        event.get("frame_entry_runtime_event_sequence")
    )
    if frame_entry_sequence is None:
        errors.append("frame-entry-runtime-event-sequence")
    elif event_sequence is not None and frame_entry_sequence >= event_sequence:
        errors.append("frame-entry-not-before-mutation")

    if _positive_int(event.get("frame_physics_system")) is None:
        errors.append("frame-physics-system")

    call_index = _positive_int(event.get("call_index"))
    if call_index is None:
        errors.append("call-index")

    registers = event.get("registers")
    if not isinstance(registers, Mapping):
        errors.append("registers")
    else:
        if component_offset is not None and registers.get("eax") != component_offset:
            errors.append("register-eax")
        if vehicle_pointer is not None and registers.get("ecx") != vehicle_pointer:
            errors.append("register-ecx")

    return {
        "format": "SHIFT.ConstraintRelationStateMutationEventValidation/1",
        "version": 1,
        "ready": not errors,
        "status": "valid" if not errors else "blocked",
        "errors": list(dict.fromkeys(errors)),
    }


def normalize_timeline_anchor(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, Mapping):
        metadata = {}

    capture_kind = payload.get("capture_kind")
    stage = payload.get("stage")
    if stage is None:
        stage = metadata.get("capture_kind")

    if capture_kind == "frame_entry_backend":
        kind = "frame-entry"
    elif capture_kind == "pre_solve_builtin_solver":
        kind = "builtin-solve-entry"
    elif capture_kind == "post_solve":
        kind = "post-solve"
    elif stage == "pre-solve-provider":
        kind = "provider-solve-entry"
    elif stage == "post-solve-provider":
        kind = "provider-solve-return"
    elif payload.get("source_function") == "FUN_007b2210":
        kind = "scalar-reset"
    else:
        kind = "unknown"

    sequence = payload.get("runtime_event_sequence")
    if sequence is None:
        sequence = metadata.get("runtime_event_sequence")

    frame_index = payload.get("frame_index")
    physics_system = payload.get("physics_system")

    errors: list[str] = []
    normalized_sequence = _positive_int(sequence)
    if normalized_sequence is None:
        errors.append("runtime-event-sequence")

    normalized_frame = _positive_int(frame_index)
    if normalized_frame is None:
        errors.append("frame-index")

    if kind == "unknown":
        errors.append("anchor-kind")

    return {
        "kind": kind,
        "runtime_event_sequence": normalized_sequence,
        "frame_index": normalized_frame,
        "physics_system": physics_system,
        "ready": not errors,
        "errors": errors,
    }


def _event_error(
    event_index: int,
    error: str,
) -> str:
    return f"event-{event_index}:{error}"


def _anchor_error(
    anchor_index: int,
    error: str,
) -> str:
    return f"anchor-{anchor_index}:{error}"


def build_relation_state_mutation_evidence(
    events: Sequence[Mapping[str, Any]],
    *,
    anchors: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []

    if not events:
        errors.append("no-mutation-events")
    if not anchors:
        errors.append("no-timeline-anchors")

    event_validations = [
        validate_relation_state_mutation_event(event)
        for event in events
    ]
    for index, validation in enumerate(event_validations):
        errors.extend(
            _event_error(index, error)
            for error in validation.get("errors") or []
        )

    normalized_anchors = [
        normalize_timeline_anchor(anchor)
        for anchor in anchors
    ]
    for index, anchor in enumerate(normalized_anchors):
        errors.extend(
            _anchor_error(index, error)
            for error in anchor.get("errors") or []
        )

    ready_anchors = [
        anchor
        for anchor in normalized_anchors
        if anchor["ready"]
    ]
    ready_anchors.sort(
        key=lambda anchor: int(anchor["runtime_event_sequence"])
    )

    anchor_sequences = [
        int(anchor["runtime_event_sequence"])
        for anchor in ready_anchors
    ]
    if len(anchor_sequences) != len(set(anchor_sequences)):
        errors.append("duplicate-anchor-runtime-event-sequence")

    event_sequences: list[int] = []
    call_indices: list[int] = []
    for event in events:
        sequence = _positive_int(event.get("runtime_event_sequence"))
        call_index = _positive_int(event.get("call_index"))
        if sequence is not None:
            event_sequences.append(sequence)
        if call_index is not None:
            call_indices.append(call_index)

    if len(event_sequences) != len(set(event_sequences)):
        errors.append("duplicate-mutation-runtime-event-sequence")
    if set(event_sequences) & set(anchor_sequences):
        errors.append("mutation-anchor-runtime-event-sequence-collision")
    if call_indices and sorted(call_indices) != list(
        range(1, len(events) + 1)
    ):
        errors.append("mutation-call-index-not-contiguous")

    anchors_by_sequence = {
        int(anchor["runtime_event_sequence"]): anchor
        for anchor in ready_anchors
    }
    anchors_by_frame: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for anchor in ready_anchors:
        anchors_by_frame[int(anchor["frame_index"])].append(anchor)

    placements: list[dict[str, Any]] = []
    slot_counts = Counter()
    branch_counts = Counter()
    timing_counts = Counter()
    window_counts = Counter()

    for index, event in enumerate(events):
        if not event_validations[index]["ready"]:
            continue

        sequence = int(event["runtime_event_sequence"])
        frame_index = int(event["frame_index"])
        frame_entry_sequence = int(
            event["frame_entry_runtime_event_sequence"]
        )

        frame_entry = anchors_by_sequence.get(frame_entry_sequence)
        if frame_entry is None:
            errors.append(_event_error(index, "missing-frame-entry-anchor"))
            continue
        if frame_entry["kind"] != "frame-entry":
            errors.append(_event_error(index, "referenced-anchor-not-frame-entry"))
            continue
        if frame_entry["frame_index"] != frame_index:
            errors.append(_event_error(index, "frame-entry-index-mismatch"))
            continue
        if (
            _positive_int(event.get("frame_physics_system"))
            != _positive_int(frame_entry.get("physics_system"))
        ):
            errors.append(_event_error(index, "frame-physics-system-mismatch"))
            continue

        frame_anchors = sorted(
            anchors_by_frame.get(frame_index, []),
            key=lambda anchor: int(anchor["runtime_event_sequence"]),
        )
        solve_entries = [
            anchor
            for anchor in frame_anchors
            if anchor["kind"] in _SOLVE_ENTRY_KINDS
        ]
        post_solves = [
            anchor
            for anchor in frame_anchors
            if anchor["kind"] == "post-solve"
        ]
        if not solve_entries:
            errors.append(_event_error(index, "missing-solve-entry-anchor"))
            continue
        if not post_solves:
            errors.append(_event_error(index, "missing-post-solve-anchor"))
            continue

        solve_entry_sequence = min(
            int(anchor["runtime_event_sequence"])
            for anchor in solve_entries
        )
        post_solve_sequence = min(
            int(anchor["runtime_event_sequence"])
            for anchor in post_solves
        )
        if solve_entry_sequence <= frame_entry_sequence:
            errors.append(_event_error(index, "solve-entry-not-after-frame-entry"))
            continue
        if post_solve_sequence <= solve_entry_sequence:
            errors.append(_event_error(index, "post-solve-not-after-solve-entry"))
            continue

        previous_anchor = None
        next_anchor = None
        for anchor in ready_anchors:
            anchor_sequence = int(anchor["runtime_event_sequence"])
            if anchor_sequence < sequence:
                previous_anchor = anchor
                continue
            if anchor_sequence > sequence:
                next_anchor = anchor
                break

        if previous_anchor is None:
            errors.append(_event_error(index, "missing-previous-timeline-anchor"))
            continue
        if next_anchor is None:
            errors.append(_event_error(index, "missing-next-timeline-anchor"))
            continue

        if sequence < solve_entry_sequence:
            timing_class = "pre-solve"
        elif sequence < post_solve_sequence:
            timing_class = "solver-window"
        else:
            timing_class = "post-solve"

        window = (
            f"{previous_anchor['kind']}->{next_anchor['kind']}"
        )
        slot = int(event["component_slot"])
        branch = str(event["source_branch"])

        slot_counts[RELATION_STATE_MUTATION_SLOT_NAMES[slot]] += 1
        branch_counts[branch] += 1
        timing_counts[timing_class] += 1
        window_counts[window] += 1

        placements.append({
            "call_index": int(event["call_index"]),
            "runtime_event_sequence": sequence,
            "frame_index": frame_index,
            "component_slot": slot,
            "component_slot_name": RELATION_STATE_MUTATION_SLOT_NAMES[slot],
            "spindle_body_present": bool(event["spindle_body_present"]),
            "source_branch": branch,
            "caller_return_address": int(event["caller_return_address"]),
            "frame_entry_runtime_event_sequence": frame_entry_sequence,
            "solve_entry_runtime_event_sequence": solve_entry_sequence,
            "post_solve_runtime_event_sequence": post_solve_sequence,
            "previous_anchor": {
                "kind": previous_anchor["kind"],
                "runtime_event_sequence": int(
                    previous_anchor["runtime_event_sequence"]
                ),
                "frame_index": int(previous_anchor["frame_index"]),
            },
            "next_anchor": {
                "kind": next_anchor["kind"],
                "runtime_event_sequence": int(
                    next_anchor["runtime_event_sequence"]
                ),
                "frame_index": int(next_anchor["frame_index"]),
            },
            "timeline_window": window,
            "timing_class": timing_class,
        })

    errors = list(dict.fromkeys(errors))
    ready = (
        not errors
        and len(placements) == len(events)
        and bool(events)
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "event_count": len(events),
        "anchor_count": len(anchors),
        "correlated_event_count": len(placements),
        "placements": placements,
        "summary": {
            "slot_counts": dict(sorted(slot_counts.items())),
            "branch_counts": dict(sorted(branch_counts.items())),
            "timing_class_counts": dict(sorted(timing_counts.items())),
            "timeline_window_counts": dict(sorted(window_counts.items())),
        },
        "scheduler_admission": {
            "ready": ready,
            "scope": "retail-event-evidence-only",
            "native_scheduler_integrated": False,
            "requires_explicit_native_mapping": True,
        },
        "event_validations": event_validations,
        "timeline_anchors": ready_anchors,
        "errors": errors,
        "limitations": [
            "This validator correlates supplied capture artifacts; it does not independently prove that they came from an unmodified live retail process.",
            "A ready evidence manifest does not modify or enable the native scheduler.",
            "Native scheduling still requires an explicit mapping from observed timing classes/callsites to the fixed-step runtime.",
        ],
    }


__all__ = [
    "FORMAT",
    "validate_relation_state_mutation_event",
    "normalize_timeline_anchor",
    "build_relation_state_mutation_evidence",
]
