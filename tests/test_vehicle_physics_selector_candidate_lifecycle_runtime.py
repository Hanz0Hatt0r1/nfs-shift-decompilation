import vehicle_physics_selector_candidate_lifecycle_runtime as runtime


def test_phase510_descriptor_layout_and_defaults_are_source_backed():
    report = runtime.build_vehicle_physics_selector_candidate_lifecycle()

    assert report["format"] == "SHIFT.VehiclePhysicsSelectorCandidateLifecycle/1"
    assert report["ready"] is True
    descriptor = report["descriptor"]
    assert descriptor["base"] == "context+0xb8"
    assert descriptor["stride"] == "0x90"
    assert descriptor["state_offset"] == "+0x74"
    assert descriptor["ordinal_offset"] == "+0x8c"
    assert descriptor["constructor_defaults"]["+0x74"] == "not written by FUN_0040eec0"
    assert descriptor["constructor_defaults"]["+0x8c"] == 0


def test_phase510_selection_scans_use_the_same_observed_eligibility_field():
    report = runtime.build_vehicle_physics_selector_candidate_lifecycle()

    assert report["selection_scan"]["function"] == "FUN_0043af50"
    assert report["selection_scan"]["eligible_test"] == "descriptor+0x74 == 0"
    assert report["selector_match_path"]["function"] == "FUN_00410ef0"
    assert report["selector_match_path"]["eligible_test"] == "candidate+0x74 == 0"


def test_phase510_batch_path_proves_temporary_exclusion_then_reset():
    report = runtime.build_vehicle_physics_selector_candidate_lifecycle()
    batch = report["batch_reservation_path"]

    assert batch["function"] == "FUN_004d69d0"
    assert batch["bound"] == 16
    assert "set descriptor+0x74 = 1" in batch["steps"][1]
    assert "reset descriptor+0x74 = 0" in batch["steps"][3]


def test_phase510_keeps_post_load_flag_separate_from_selection_state():
    report = runtime.build_vehicle_physics_selector_candidate_lifecycle()
    consumer = report["vehicle_load_consumer_path"]

    assert consumer["function"] == "FUN_00465860"
    assert report["descriptor"]["post_load_flag_offset"] == "+0x1d"
    assert report["descriptor"]["state_offset"] != report["descriptor"]["post_load_flag_offset"]
    assert any("+0x1d = 1" in step for step in consumer["steps"])
    assert report["population"]["function"] == "thunk_FUN_00d36a00"
    assert "descriptor+0x1d = 0" in report["population"]["writes"]
    assert report["post_load_state_path"]["function"] == "FUN_0040f900"


def test_phase510_is_capture_gated_and_does_not_invent_class_identity():
    report = runtime.build_vehicle_physics_selector_candidate_lifecycle()
    limitations = " ".join(report["limitations"])

    assert "No C++ class identity" in limitations
    assert "capture-dependent" in limitations
