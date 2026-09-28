import physics_participant_manager_event_runtime as runtime


def test_phase506_event_contract_is_source_backed():
    report = runtime.build_physics_participant_manager_event()

    assert report["format"] == "SHIFT.PhysicsParticipantManagerEvent/1"
    assert report["ready"] is True
    assert report["event"]["opcode"] == "0x20"
    assert report["event"]["channel"] == 3
    assert report["event"]["producer"] == "FUN_0070e1c0"
    assert report["event"]["dispatch_target"] == "FUN_00714560(&DAT_00c109e0, event)"


def test_phase506_manager_ingestion_records_ready_field():
    report = runtime.build_physics_participant_manager_event()

    assert report["manager"]["global_instance"] == "DAT_00c109e0"
    assert report["manager"]["consumer"] == "FUN_00714560"
    assert report["manager"]["ready_field"] == "+0x39c"
    assert report["manager"]["ready_value"] == 1
    assert report["manager"]["configuration"]["count_source"] == "event+0xb0"


def test_phase506_does_not_overclaim_selector_join():
    report = runtime.build_physics_participant_manager_event()

    assert report["relationship_to_phase505"]["causal_link_proven"] is False
    assert "unproven" in " ".join(report["limitations"]).lower()
