import physics_participant_registry_update_runtime as runtime


def test_phase507_registry_contract_is_source_backed():
    report = runtime.build_physics_participant_registry_update()

    assert report["format"] == "SHIFT.PhysicsParticipantRegistryUpdate/1"
    assert report["ready"] is True
    assert report["manager"]["global_instance"] == "DAT_00c109e0"
    assert report["manager"]["slot_array_field"] == "+0x140"
    assert report["manager"]["allocated_entry_stride"] == "0x1fa0"


def test_phase507_registration_and_update_calls_are_explicit():
    report = runtime.build_physics_participant_registry_update()

    assert report["registration"]["function"] == "FUN_00713f40"
    assert report["registration"]["descriptor_enabled_field"] == "param_2+0x10"
    assert report["registration"]["descriptor_index_field"] == "param_2+0x14"
    assert report["update"]["function"] == "FUN_00713ec0"
    assert report["update"]["writes"]["+0x2298"] == "descriptor+0x1c"


def test_phase507_captures_physics_participant_type_gate():
    report = runtime.build_physics_participant_registry_update()

    callsite = report["participant_callsite"]
    assert callsite["type_gate"] == "participant descriptor +0x1c == 3"
    assert callsite["registration_call"].startswith("FUN_00713f40(&DAT_00c109e0")
    assert callsite["update_call"].startswith("FUN_00713ec0(&DAT_00c109e0")


def test_phase507_does_not_claim_phase505_context_identity():
    report = runtime.build_physics_participant_registry_update()

    relationship = report["relationship_to_phase505"]
    assert relationship["same_object_proven"] is False
    assert "remains open" in " ".join(report["limitations"])
