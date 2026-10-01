import relation_state_mutation_evidence_runtime as runtime


def _event(
    *,
    call_index=1,
    sequence=3,
    frame=1,
    frame_entry_sequence=1,
    slot=1,
    spindle_present=False,
    frame_physics_system=0x5000,
):
    vehicle = 0x10000000
    component_offset = slot * 0xA80
    spindle = 0x21000000 if spindle_present else 0
    return {
        "format": "SHIFT.ConstraintRelationStateMutationCaptureRuntime/1",
        "version": 1,
        "status": "captured",
        "ready": True,
        "capture_errors": [],
        "body_pointer_capture_skipped": False,
        "source_function": "FUN_00757d2c",
        "source_address": 0x00757D2C,
        "vehicle_pointer": vehicle,
        "component_offset": component_offset,
        "component_slot": slot,
        "component_slot_name": ("FL", "FR", "RL", "RR")[slot],
        "component_block_pointer": vehicle + 0x400 + component_offset,
        "wheel_body_pointer": 0x20000000 + slot * 0x100,
        "spindle_body_pointer": spindle,
        "rear_axle_body_pointer": 0x30000000,
        "spindle_body_present": spindle_present,
        "source_branch": (
            "spindle-bar-endpoint"
            if spindle_present
            else "wheel-rear-axle-pair"
        ),
        "caller_return_address": 0x0076EE00,
        "call_index": call_index,
        "runtime_event_sequence": sequence,
        "frame_index": frame,
        "frame_entry_runtime_event_sequence": frame_entry_sequence,
        "frame_physics_system": frame_physics_system,
        "registers": {
            "eax": component_offset,
            "ecx": vehicle,
            "esp": 0x12000000,
            "eip": 0x00757D2C,
        },
    }


def _frame_entry(sequence=1, frame=1, physics_system=0x5000):
    return {
        "capture_kind": "frame_entry_backend",
        "runtime_event_sequence": sequence,
        "frame_index": frame,
        "physics_system": physics_system,
    }


def _builtin_solve(sequence=4, frame=1):
    return {
        "capture_kind": "pre_solve_builtin_solver",
        "runtime_event_sequence": sequence,
        "frame_index": frame,
        "physics_system": 0x5000,
    }


def _post_solve(sequence=5, frame=1):
    return {
        "capture_kind": "post_solve",
        "runtime_event_sequence": sequence,
        "frame_index": frame,
        "physics_system": 0x5000,
    }


def _reset(sequence=2, frame=1):
    return {
        "source_function": "FUN_007b2210",
        "runtime_event_sequence": sequence,
        "frame_index": frame,
        "physics_system": 0x5000,
    }


def test_validate_mutation_event_accepts_phase635_contract():
    result = runtime.validate_relation_state_mutation_event(_event())

    assert result["ready"] is True
    assert result["errors"] == []


def test_validate_mutation_event_rejects_branch_mismatch():
    event = _event(spindle_present=True)
    event["source_branch"] = "wheel-rear-axle-pair"

    result = runtime.validate_relation_state_mutation_event(event)

    assert result["ready"] is False
    assert "source-branch" in result["errors"]


def test_build_evidence_correlates_pre_solve_window():
    event = _event(sequence=3)
    anchors = [
        _frame_entry(sequence=1),
        _reset(sequence=2),
        _builtin_solve(sequence=4),
        _post_solve(sequence=5),
    ]

    result = runtime.build_relation_state_mutation_evidence(
        [event],
        anchors=anchors,
    )

    assert result["ready"] is True
    assert result["correlated_event_count"] == 1
    placement = result["placements"][0]
    assert placement["component_slot_name"] == "FR"
    assert placement["timing_class"] == "pre-solve"
    assert placement["timeline_window"] == "scalar-reset->builtin-solve-entry"
    assert result["summary"]["slot_counts"] == {"FR": 1}
    assert result["summary"]["timing_class_counts"] == {"pre-solve": 1}
    assert result["scheduler_admission"] == {
        "ready": True,
        "scope": "retail-event-evidence-only",
        "native_scheduler_integrated": False,
        "requires_explicit_native_mapping": True,
    }


def test_build_evidence_classifies_post_solve_before_next_frame():
    event = _event(sequence=4)
    anchors = [
        _frame_entry(sequence=1),
        _builtin_solve(sequence=2),
        _post_solve(sequence=3),
        _frame_entry(sequence=5, frame=2, physics_system=0x6000),
    ]

    result = runtime.build_relation_state_mutation_evidence(
        [event],
        anchors=anchors,
    )

    assert result["ready"] is True
    placement = result["placements"][0]
    assert placement["timing_class"] == "post-solve"
    assert placement["timeline_window"] == "post-solve->frame-entry"


def test_build_evidence_requires_exact_referenced_frame_entry():
    event = _event(frame_entry_sequence=7)
    anchors = [
        _frame_entry(sequence=1),
        _builtin_solve(sequence=4),
        _post_solve(sequence=5),
    ]

    result = runtime.build_relation_state_mutation_evidence(
        [event],
        anchors=anchors,
    )

    assert result["ready"] is False
    assert "event-0:missing-frame-entry-anchor" in result["errors"]


def test_build_evidence_requires_complete_next_timeline_anchor():
    event = _event(sequence=6)
    anchors = [
        _frame_entry(sequence=1),
        _builtin_solve(sequence=4),
        _post_solve(sequence=5),
    ]

    result = runtime.build_relation_state_mutation_evidence(
        [event],
        anchors=anchors,
    )

    assert result["ready"] is False
    assert "event-0:missing-next-timeline-anchor" in result["errors"]


def test_build_evidence_rejects_duplicate_anchor_sequence():
    event = _event(sequence=3)
    anchors = [
        _frame_entry(sequence=1),
        _reset(sequence=2),
        _builtin_solve(sequence=4),
        {
            "capture_kind": "post_solve",
            "runtime_event_sequence": 4,
            "frame_index": 1,
            "physics_system": 0x5000,
        },
    ]

    result = runtime.build_relation_state_mutation_evidence(
        [event],
        anchors=anchors,
    )

    assert result["ready"] is False
    assert "duplicate-anchor-runtime-event-sequence" in result["errors"]


def test_build_evidence_requires_contiguous_mutation_call_indices():
    events = [
        _event(call_index=1, sequence=3),
        _event(call_index=3, sequence=6, slot=2),
    ]
    anchors = [
        _frame_entry(sequence=1),
        _reset(sequence=2),
        _builtin_solve(sequence=4),
        _post_solve(sequence=5),
        _frame_entry(sequence=7, frame=2, physics_system=0x6000),
    ]

    result = runtime.build_relation_state_mutation_evidence(
        events,
        anchors=anchors,
    )

    assert result["ready"] is False
    assert "mutation-call-index-not-contiguous" in result["errors"]
