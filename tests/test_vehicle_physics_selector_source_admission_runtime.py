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



def test_phase514_mask_hit_calls_wrapper_and_clears_bit():
    state = runtime.evaluate_selector_source_admission(
        owner_mask=0x20,
        source_token=0x1235,
        current_count=3,
        capacity=16,
    )

    assert state["selector_key"] == 5
    assert state["bit_mask"] == 0x20
    assert state["mask_hit"] is True
    assert state["wrapper_called"] is True
    assert state["population_succeeded"] is True
    assert state["owner_mask_after"] == 0
    assert state["count_after"] == 4


def test_phase514_capacity_gate_is_independent_from_mask_gate():
    state = runtime.evaluate_selector_source_admission(
        owner_mask=0x10,
        source_token=0x20,
        current_count=16,
        capacity=16,
    )

    assert state["selector_key"] == 0
    assert state["mask_hit"] is True
    assert state["wrapper_called"] is True
    assert state["capacity_available"] is False
    assert state["population_succeeded"] is False
    assert state["mask_cleared"] is True
    assert state["owner_mask_after"] == 0
    assert state["count_after"] == 16


def test_phase514_mask_miss_does_not_mutate_state():
    state = runtime.evaluate_selector_source_admission(
        owner_mask=0x04,
        source_token=0x25,
        current_count=2,
        capacity=16,
    )

    assert state["selector_key"] == 5
    assert state["mask_hit"] is False
    assert state["wrapper_called"] is False
    assert state["population_succeeded"] is False
    assert state["mask_cleared"] is False
    assert state["owner_mask_after"] == 0x04
    assert state["count_after"] == 2
