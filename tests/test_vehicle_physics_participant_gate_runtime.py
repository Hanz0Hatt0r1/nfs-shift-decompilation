import vehicle_physics_participant_gate_runtime as runtime


def test_phase505_source_gate_is_ready():
    report = runtime.build_vehicle_physics_participant_gate()

    assert report["format"] == "SHIFT.VehiclePhysicsParticipantGate/1"
    assert report["ready"] is True
    assert report["selection"]["callee"] == "FUN_00410ef0"
    assert report["selection"]["argument_output_pointer"] == "IGPhaseVehicle+0x450"
    assert report["selection"]["returned_ordinal_slot"] == "IGPhaseVehicle+0x454"
    assert report["selection"]["failure_value"] == -1


def test_phase505_links_success_to_vehicle_bff_load():
    report = runtime.build_vehicle_physics_participant_gate()

    assert report["post_success"]["base_load_path"] == "Pakfiles/Vehicles/%s.bff"
    assert report["post_success"]["base_load_begins_after_success"] is True
    assert report["post_success"]["phase_state_field"] == "IGPhaseVehicle+0x45c"


def test_phase505_preserves_only_observed_candidate_condition():
    report = runtime.build_vehicle_physics_participant_gate()

    assert report["source_algorithm"]["candidate_eligibility_test"] == "candidate+0x74 == 0"
    assert "semantic class name" in " ".join(report["limitations"])
    assert "runtime participant instance" in " ".join(report["limitations"])
