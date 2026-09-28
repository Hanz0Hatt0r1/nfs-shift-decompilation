import vehicle_physics_selector_source_admission_runtime as runtime


def test_phase513_admission_key_and_mask_gate_are_source_backed():
    report = runtime.build_vehicle_physics_selector_source_admission()

    assert report["format"] == "SHIFT.VehiclePhysicsSelectorSourceAdmission/1"
    assert report["ready"] is True
    gate = report["source_admission"]
    assert gate["function"] == "thunk_FUN_00d758d0"
    assert gate["selector_key"] == "(source_record+0x10) & 0xf"
    assert gate["bit_mask"] == "1 << selector_key"
    assert gate["gate"] == "owner+0x4f0 & bit_mask != 0"


def test_phase513_admission_calls_descriptor_wrapper_then_clears_the_bit():
    report = runtime.build_vehicle_physics_selector_source_admission()
    actions = report["source_admission"]["on_match"]

    assert actions[1] == "thunk_FUN_00409290(&DAT_00bbc600, source_record)"
    assert actions[2] == "owner+0x4f0 ^= bit_mask"


def test_phase513_reset_paths_clear_the_same_mask():
    report = runtime.build_vehicle_physics_selector_source_admission()
    resets = report["mask_lifecycle"]["clear_and_resync"]

    assert resets[0]["function"] == "FUN_004b6b30"
    assert resets[0]["mask_action"] == "owner+0x4f0 = 0"
    assert resets[1]["function"] == "thunk_FUN_00d75a20"
    assert resets[1]["mask_action"] == "owner+0x4f0 = 0"


def test_phase513_keeps_capacity_gate_and_mask_gate_separate():
    report = runtime.build_vehicle_physics_selector_source_admission()

    assert report["relation_to_population"]["capacity_gate"] == "selector context+0x1c < selector context+0x28"
    limitations = " ".join(report["limitations"])
    assert "capacity gate is exhausted" in limitations
