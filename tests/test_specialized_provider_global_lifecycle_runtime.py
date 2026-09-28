import specialized_provider_global_lifecycle_runtime as runtime


def test_provider0_global_lifecycle():
    result = runtime.build_provider_global_lifecycle(0)

    assert result["global_object"] == "DAT_00c23da8"
    assert result["init"]["function"] == "FUN_00a8ca80"
    assert result["runtime"]["solve_function"] == "0x7c7200"
    assert result["runtime"]["reset_function"] == "0x7d3150"
    assert result["runtime"]["cleanup_function"] == "0x7d43c0"
    assert result["runtime"]["shutdown_function"] == "0x7c6e10"
    assert result["teardown"]["function"] == "FUN_00aa3800"


def test_provider1_global_lifecycle():
    result = runtime.build_provider_global_lifecycle(1)

    assert result["global_object"] == "DAT_00c23dac"
    assert result["init"]["function"] == "FUN_00a8caa0"
    assert result["runtime"]["solve_function"] == "0x7cdfc0"
    assert result["runtime"]["reset_function"] == "0x7d48a0"
    assert result["runtime"]["cleanup_function"] == "0x7d5600"
    assert result["runtime"]["shutdown_function"] == "0x7cdb00"
    assert result["teardown"]["function"] == "FUN_00aa3810"


def test_validate_global_lifecycle_for_both_providers():
    assert runtime.validate_provider_global_lifecycle(0)["ready"] is True
    assert runtime.validate_provider_global_lifecycle(1)["ready"] is True


def test_global_contract_tracks_reset_frame_callsite():
    contract = runtime.build_global_lifecycle_contract()

    assert contract["reset_boundary"]["vtable_slot"] == "+0x1c"
    assert contract["reset_boundary"]["frame_loop_callsite"] == (
        "FUN_007b3f40 -> FUN_007b2210 -> provider vtable +0x1c"
    )
    assert [item["provider_id"] for item in contract["providers"]] == [0, 1]


def test_global_order_keeps_frame_reset_in_execution_layer():
    contract = runtime.build_global_lifecycle_contract()

    assert contract["reset_boundary"]["status"] == (
        "per-scalar frame reset delegated by FUN_007b2210"
    )
