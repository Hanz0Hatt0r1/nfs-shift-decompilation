import vehicle_physics_participant_process_runtime as runtime


def test_phase509_process_contract_is_source_backed():
    report = runtime.build_vehicle_physics_participant_process()

    assert report["format"] == "SHIFT.VehiclePhysicsParticipantProcessReselect/1"
    assert report["ready"] is True
    assert report["owner"]["pointer_slot"] == "IGPhaseVehicle+0x450"
    assert report["owner"]["ordinal_slot"] == "IGPhaseVehicle+0x454"
    assert report["owner"]["state_slot"] == "IGPhaseVehicle+0x45c"


def test_phase509_consumes_previous_selection_before_reselect():
    report = runtime.build_vehicle_physics_participant_process()

    preload = report["preload_step"]
    assert preload["function"] == "FUN_00468ed0"
    assert preload["pointer_argument"] == "IGPhaseVehicle+0x450"
    assert preload["first_argument"] == "selected_pointer[0x23] (selected_pointer + 0x8c)"
    assert preload["ordering"].startswith("runs before")


def test_phase509_reselects_from_same_selector_global_and_loads_bff():
    report = runtime.build_vehicle_physics_participant_process()

    assert report["selection_step"]["selector_global"] == "DAT_00bbc600"
    assert report["selection_step"]["selector_function"] == "FUN_00410ef0"
    assert report["load_step"]["path_template"] == "Pakfiles/Vehicles/%s.bff"
    assert report["load_step"]["success_condition"] == "(char)uVar3 != 0"


def test_phase509_writeback_happens_only_after_load_success():
    report = runtime.build_vehicle_physics_participant_process()

    load = report["load_step"]
    assert load["writeback_order"] == [
        "IGPhaseVehicle+0x454 = selected ordinal",
        "IGPhaseVehicle+0x450 = selected pointer",
    ]
    assert report["loop"]["termination"][1] == "next vehicle BFF load fails"


def test_phase509_closes_phase508_and_phase505_joins_without_overclaiming():
    report = runtime.build_vehicle_physics_participant_process()

    assert report["relationship_to_phase508"]["same_selector_global"] is True
    assert report["relationship_to_phase505"]["same_slots"] is True
    assert "does not assign" in " ".join(report["limitations"])
