import specialized_provider_vtable_lifecycle_runtime as runtime


def test_provider0_vtable_has_exact_core_lifecycle_slots():
    table = runtime.get_vtable_lifecycle(0)

    assert table.vtable_address == 0x00B0FC5C
    assert table.slots[0x18] == 0x007C7200
    assert table.slots[0x1C] == 0x007D3150
    assert table.slots[0x20] == 0x007D43C0
    assert table.slots[0x00] == 0x007D3120


def test_provider1_vtable_has_exact_core_lifecycle_slots():
    table = runtime.get_vtable_lifecycle(1)

    assert table.vtable_address == 0x00B0FC8C
    assert table.slots[0x18] == 0x007CDFC0
    assert table.slots[0x1C] == 0x007D48A0
    assert table.slots[0x20] == 0x007D5600
    assert table.slots[0x00] == 0x007D4870


def test_vtable_contract_contains_twelve_slots_per_provider():
    assert build0 := runtime.build_vtable_contract(0)
    assert build0["slot_count"] == 12
    assert runtime.build_vtable_contract(1)["slot_count"] == 12


def test_vtable_contract_labels_storage_and_solver_roles():
    result = runtime.build_vtable_contract(0)

    roles = {
        item["offset"]: item["role"]
        for item in result["slots"]
    }

    assert roles["0x18"] == "solve"
    assert roles["0x1c"] == "reset"
    assert roles["0x20"] == "cleanup"
    assert roles["0x04"] == "output-vector-accessor"
    assert roles["0x08"] == "factor-workspace-accessor"
    assert roles["0x0c"] == "row-pointer-accessor"


def test_validate_vtable_contract_for_both_providers():
    assert runtime.validate_vtable_contract(0)["ready"] is True
    assert runtime.validate_vtable_contract(1)["ready"] is True


def test_validate_vtable_contract_rejects_missing_solve_slot():
    original = runtime.PROVIDER0_VTABLE
    broken = runtime.VTableLifecycle(
        provider_id=0,
        vtable_address=original.vtable_address,
        slots={
            offset: address
            for offset, address in original.slots.items()
            if offset != 0x18
        },
        shutdown_function=original.shutdown_function,
        reset_function=original.reset_function,
        cleanup_function=original.cleanup_function,
    )
    runtime.PROVIDER0_VTABLE = broken
    try:
        result = runtime.validate_vtable_contract(0)
        assert result["ready"] is False
        assert "missing-slot:0x18" in result["errors"]
    finally:
        runtime.PROVIDER0_VTABLE = original


def test_build_lifecycle_contract_contains_both_providers():
    contract = runtime.build_vtable_lifecycle_contract()

    assert [item["provider_id"] for item in contract["providers"]] == [0, 1]
    assert all(
        item["validation"]["ready"]
        for item in contract["providers"]
    )
