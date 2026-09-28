import igphasevehicle_finalization_runtime as runtime


def test_phase511_finalizer_owns_the_three_observed_containers():
    report = runtime.build_igphasevehicle_finalization()

    assert report["format"] == "SHIFT.IGPhaseVehicleCompletionFinalization/1"
    assert report["ready"] is True
    fields = [item["field"] for item in report["completion_finalizer"]["containers"]]
    assert fields == [
        "IGPhaseVehicle+0x3ec",
        "IGPhaseVehicle+0x3cc",
        "IGPhaseVehicle+0x40c",
    ]


def test_phase511_records_callback_and_cleanup_order():
    report = runtime.build_igphasevehicle_finalization()
    finalizer = report["completion_finalizer"]

    assert finalizer["containers"][0]["entry_callback"] == "DAT_00c26058 vtable +0x204"
    assert finalizer["containers"][1]["entry_callback"] == "DAT_00c26058 vtable +0x220"
    assert "FUN_00634eb0(thunk_FUN_0045b39c()+0x1758)" in finalizer["resource_cleanup"]
    assert "thunk_FUN_0050caa0(IGPhaseVehicle)" in finalizer["resource_cleanup"]
    assert finalizer["pre_callback"] is True


def test_phase511_normal_and_cockpit_paths_both_finalize_before_callback():
    report = runtime.build_igphasevehicle_finalization()
    process = report["process_link"]

    assert process["function"] == "FUN_004d5f30"
    assert "FUN_004d5930(param_1)" in process["normal_state"]
    assert "FUN_004d5930(param_1)" in process["cockpit_state"]
    assert process["normal_state"][-1] == "object vtable +0xc callback"
    assert process["cockpit_state"][-1] == "object vtable +0xc callback"


def test_phase511_keeps_destructor_teardown_separate_from_completion():
    report = runtime.build_igphasevehicle_finalization()
    destructor = report["destructor_boundary"]

    assert destructor["function"] == "FUN_004d54a0"
    assert "clear +0x42c container" in destructor["actions"]
    assert "call thunk_FUN_0050caa0(param_1)" in destructor["actions"]
    assert report["completion_finalizer"]["function"] != destructor["function"]


def test_phase511_does_not_invent_container_types_or_provider_semantics():
    report = runtime.build_igphasevehicle_finalization()
    limitations = " ".join(report["limitations"])

    assert "generic engine types are not inferred" in limitations
    assert "does not add runtime provider/PhysX numeric claims" in limitations
