import specialized_provider_scalar_reset_runtime as runtime


def test_scalar_reset_signature():
    assert runtime.FUNCTION["name"] == "FUN_007b2210"
    assert runtime.FUNCTION["signature"] == (
        "void __thiscall FUN_007b2210(void *this,int param_1)"
    )


def test_builtin_scalar_reset_operations():
    contract = runtime.build_scalar_reset_contract()

    assert contract["builtin"]["row_zero"]["address"] == (
        "row_pointer[param_1][index]"
    )
    assert contract["builtin"]["column_zero"]["address"] == (
        "row_pointer[index][param_1]"
    )
    assert contract["builtin"]["diagonal"] == {
        "address": "row_pointer[param_1][param_1]",
        "value": "1.0",
    }
    assert contract["builtin"]["rhs"]["value"] == "0.0"


def test_provider_scalar_reset_delegates_to_vtable_plus_1c():
    contract = runtime.build_scalar_reset_contract()

    assert contract["provider"]["vtable_offset"] == 0x1C
    assert contract["provider"]["selector"] == "param_1"
    assert contract["provider_execution"]["selector_propagation"] is True


def test_scalar_reset_has_three_source_callsite_groups():
    contract = runtime.build_scalar_reset_contract()

    assert contract["source_call_count"] == 6
    assert [entry["width"] for entry in contract["source_call_sites"]] == [
        3, 2, 1
    ]
    assert [entry["source_line"] for entry in contract["source_call_sites"]] == [
        814124, 814138, 814150
    ]


def test_validate_scalar_reset_contract():
    result = runtime.validate_scalar_reset_contract()

    assert result["ready"] is True
    assert result["errors"] == []
