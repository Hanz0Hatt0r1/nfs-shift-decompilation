import vehicle_physics_selector_context_runtime as runtime


def test_phase508_selector_context_identity_is_explicit():
    report = runtime.build_vehicle_physics_selector_context()

    assert report["format"] == "SHIFT.VehiclePhysicsSelectorContext/1"
    assert report["ready"] is True
    assert report["context"]["global_instance"] == "DAT_00bbc600"
    assert report["context"]["accessor_thunk"] == "thunk_FUN_00453990"
    assert report["separation"]["participant_manager_global"] == "DAT_00c109e0"
    assert report["separation"]["same_object_proven"] is False


def test_phase508_selector_layout_and_lifecycle_are_source_backed():
    report = runtime.build_vehicle_physics_selector_context()

    context = report["context"]
    lifecycle = report["lifecycle"]
    assert context["member_selector_field"] == "+0x9fc"
    assert context["descriptor_count_field"] == "+0x1c"
    assert context["descriptor_base"] == "+0xb8"
    assert context["descriptor_stride"] == "0x90"
    assert lifecycle["constructor"] == "FUN_00410490"
    assert lifecycle["selector_init"] == "FUN_004102d0 -> FUN_004f0050(context+0x9fc, param_2)"
    assert lifecycle["shutdown"] == "FUN_00411430(context)"


def test_phase508_matching_rules_remain_observational():
    report = runtime.build_vehicle_physics_selector_context()
    matching = report["matching"]

    assert matching["function"] == "FUN_00410ef0"
    assert matching["linking"]["comparison"] == "__stricmp"
    assert matching["insert"]["function"] == "FUN_00800dd0"
    assert matching["termination"]["fallback_scan"].startswith("FUN_0052cce0")
    assert matching["termination"]["candidate_ready_test"] == "candidate+0x74 == 0"


def test_phase508_does_not_conflate_selector_and_manager():
    report = runtime.build_vehicle_physics_selector_context()
    assert report["separation"]["same_object_proven"] is False
    assert "does not assign a C++ class name" in " ".join(report["limitations"])
