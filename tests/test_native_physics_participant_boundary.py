import native_physics_participant_boundary as runtime


def test_phase600_native_participant_boundary_is_source_backed():
    report = runtime.build_native_physics_participant_boundary()

    assert report["format"] == "SHIFT.NativePhysicsParticipantBoundary/1"
    assert report["ready"] is True
    assert report["blocking_reasons"] == []
    assert report["registry_contract_ready"] is True
    assert report["participant_gate_ready"] is True
    assert report["participant_process_ready"] is True
    assert report["selector_context_ready"] is True

    assert report["registry_manager_global"] == "DAT_00c109e0"
    assert report["selector_global"] == "DAT_00bbc600"
    assert report["selector_context_separate"] is True
    assert report["registry_slot_array_offset"] == 0x140
    assert report["registry_slot_count_offset"] == 0x148
    assert report["registry_slot_stride"] == 0x1FA0
    assert report["participant_descriptor_type"] == 3

    assert report["participant_pointer_slot"] == "IGPhaseVehicle+0x450"
    assert report["participant_ordinal_slot"] == "IGPhaseVehicle+0x454"
    assert report["participant_state_slot"] == "IGPhaseVehicle+0x45c"

    assert report["participant_instance_ready"] is False
    assert report["participant_index"] == -1
    assert report["participant_mode"] == -1
    assert (
        report["boundary"]["selected_runtime_instance_proven"]
        is False
    )
    assert report["boundary"]["selected_provider_proven"] is False
    assert (
        report["boundary"]["numeric_physics_equivalence_proven"]
        is False
    )


def test_phase600_fails_closed_on_selector_manager_conflation(monkeypatch):
    original = runtime.build_vehicle_physics_selector_context

    def selector():
        report = original()
        report["separation"]["same_object_proven"] = True
        return report

    monkeypatch.setattr(
        runtime,
        "build_vehicle_physics_selector_context",
        selector,
    )
    report = runtime.build_native_physics_participant_boundary()

    assert report["ready"] is False
    assert (
        "selector:manager-separation-not-preserved"
        in report["blocking_reasons"]
    )


def test_phase600_fails_closed_on_registry_stride_drift(monkeypatch):
    original = runtime.build_physics_participant_registry_update

    def registry():
        report = original()
        report["manager"]["allocated_entry_stride"] = "0x2000"
        return report

    monkeypatch.setattr(
        runtime,
        "build_physics_participant_registry_update",
        registry,
    )
    report = runtime.build_native_physics_participant_boundary()

    assert report["ready"] is False
    assert "registry:slot-stride-mismatch" in report["blocking_reasons"]
