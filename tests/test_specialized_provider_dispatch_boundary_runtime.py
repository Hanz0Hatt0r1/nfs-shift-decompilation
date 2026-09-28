import specialized_provider_dispatch_boundary_runtime as runtime


def test_selection_boundary_has_both_provider_candidates():
    result = runtime.build_provider_selection_boundary()

    assert [item["slot"] for item in result["provider_candidates"]] == [0, 1]
    assert result["provider_candidates"][0]["scalar_count"] == 40
    assert result["provider_candidates"][1]["scalar_count"] == 34
    assert result["state_rebind"]["provider_pointer"] == "+0x48"
    assert result["vtable_offsets"]["acceptance"] == "0x14"


def test_execution_boundary_preserves_provider_order():
    result = runtime.build_provider_execution_boundary()

    assert [event["event"] for event in result["provider_path"]] == [
        "provider-cleanup",
        "common-preparation",
        "provider-solve",
    ]
    assert result["provider_path"][0]["vtable_offset"] == "0x20"
    assert result["provider_path"][2]["vtable_offset"] == "0x18"


def test_execution_boundary_preserves_builtin_fallback():
    result = runtime.build_provider_execution_boundary()

    assert result["builtin_path"]["condition"] == "provider pointer is null"
    assert result["builtin_path"]["solver"] == "FUN_007b0f20"
    assert result["builtin_path"]["solver_state"] == "+0x4c"


def test_validate_dispatch_boundary():
    result = runtime.validate_dispatch_boundary()

    assert result["ready"] is True
    assert result["errors"] == []


def test_contract_interpretation_separates_reset_from_solve():
    contract = runtime.build_dispatch_boundary_contract()

    assert contract["interpretation"]["reset_slot_+0x1c"].startswith(
        "separate selector-driven"
    )
    assert contract["source_order"][2].endswith(
        "provider-cleanup +0x20 when provider is active"
    )
