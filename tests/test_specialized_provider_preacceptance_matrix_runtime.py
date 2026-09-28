import specialized_provider_preacceptance_matrix_runtime as runtime


def test_matrix_build_contract_has_exact_allocations():
    result = runtime.build_matrix_construction_contract()
    contract = result["contract"]

    assert contract["scalar_count_source"] == "FUN_007b1b60(param_1)"
    assert contract["matrix_pool_allocation"] == {
        "allocator": "FUN_00638340",
        "size": "scalar_count * scalar_count * 8",
        "flags": 7,
        "destination": "physics_system+0x38",
    }
    assert contract["row_pointer_allocation"] == {
        "allocator": "FUN_008868d0",
        "size": "scalar_count * 4",
        "destination": "physics_system+0x3c",
    }


def test_row_pointer_formula_is_contiguous_row_major():
    result = runtime.build_matrix_construction_contract()

    assert result["contract"]["row_pointer_formula"] == (
        "row_pointer[row] = matrix_base + scalar_count * row * 8"
    )


def test_fun_007b2010_zeros_matrix_before_acceptance():
    result = runtime.build_matrix_construction_contract()

    initialization = result["contract"]["initialization"]
    assert initialization["function"] == "FUN_007b2010"
    assert initialization["matrix_action"] == "zero every matrix double"
    assert initialization["body_action"] == (
        "FUN_007ba2b0(body, row_pointer_table)"
    )
    assert result["order"][-1].endswith(
        "acceptance receives current row-pointer table"
    )


def test_preacceptance_domains_are_separate():
    result = runtime.build_matrix_construction_contract()

    assert result["domain"]["matrix"] == (
        "pre-selection logical matrix storage"
    )
    assert result["domain"]["provider_workspace"] == (
        "not yet rebound"
    )
    assert result["domain"]["provider_output"] == (
        "not yet rebound"
    )


def test_validate_matrix_construction_contract():
    result = runtime.validate_matrix_construction_contract()

    assert result["ready"] is True
    assert result["errors"] == []
