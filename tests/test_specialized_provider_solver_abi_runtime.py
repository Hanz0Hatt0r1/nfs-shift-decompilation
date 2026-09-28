import specialized_provider_solver_abi_runtime as runtime


def test_provider_solver_abis_are_void_noarg():
    assert runtime.get_provider_solver_abi(0)["signature"] == (
        "void FUN_007c7200(void)"
    )
    assert runtime.get_provider_solver_abi(1)["signature"] == (
        "void FUN_007cdfc0(void)"
    )


def test_builtin_solver_abi_contract_matches_known_stack_shape():
    assert runtime.BUILTIN_SOLVER_ABI["function"] == "FUN_007b0f20"
    assert runtime.BUILTIN_SOLVER_ABI["abi"] == "__thiscall"
    assert runtime.BUILTIN_SOLVER_ABI["stack_offsets"] == {
        "solver_state": "+0x04",
        "row_pointer_table": "+0x08",
        "rhs": "+0x0c",
        "scalar_count": "+0x10",
    }


def test_validate_provider_solver_abi():
    assert runtime.validate_provider_solver_abi(0)["ready"] is True
    assert runtime.validate_provider_solver_abi(1)["ready"] is True


def test_global_state_contract_uses_exact_provider_storage():
    result = runtime.build_global_state_contract(0)

    assert result["function"] == "FUN_007c7200"
    assert result["abi"] == "void(void)"
    assert result["global_state"] is True
    assert result["state_regions"]["row_pointer_table"]["entries"] == 40
    assert result["state_regions"]["factor_workspace"]["doubles"] == 1190
    assert result["state_regions"]["output_vector"]["doubles"] == 40
    assert result["solve_function_address"] == "0x7c7200"


def test_solver_abi_contract_contains_both_provider_domains():
    contract = runtime.build_solver_abi_contract()

    assert [item["provider_id"] for item in contract["providers"]] == [0, 1]
    assert all(
        item["validation"]["ready"]
        for item in contract["providers"]
    )
    assert contract["contrast"]["provider"] == (
        "void(void), fixed global storage"
    )
