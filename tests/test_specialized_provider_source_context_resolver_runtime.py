import specialized_provider_source_context_resolver_runtime as runtime


def test_row_for_pointer_resolves_registered_provider_row():
    assert runtime.row_for_pointer(0, 0x00C21800) == 1
    assert runtime.row_for_pointer(1, 0x00C1FEE8) == 1


def test_resolve_loop_cell_is_unique_with_explicit_context():
    result = runtime.resolve_loop_cell(
        0,
        row_pointer=0x00C21800,
        local_index=31,
    )

    assert result["domain"] == "workspace"
    assert result["row"] == 1
    assert result["column"] == 31
    assert result["local_index"] == 31
    assert result["unique"] is True


def test_resolve_direct_address_preserves_alias_candidates():
    result = runtime.resolve_direct_address(
        0,
        address=0x00C21800,
    )

    assert result["domain"] == "workspace"
    assert result["candidate_count"] == 2
    assert result["unique"] is False
    assert result["candidates"] == [
        {"row": 0, "column": 25},
        {"row": 1, "column": 0},
    ]


def test_resolve_direct_output_vector_address():
    result = runtime.resolve_direct_address(
        0,
        address=0x00C23C68,
    )

    assert result["domain"] == "output_vector"
    assert result["index"] == 0
    assert result["unique"] is True


def test_resolve_direct_unknown_address_stays_global():
    result = runtime.resolve_direct_address(
        0,
        address=0x00DEAD00,
    )

    assert result["domain"] == "global"
    assert result["unique"] is True
    assert result["candidates"] == []


def test_context_contract_covers_all_provider_diagonals():
    contract = runtime.build_source_context_contract()

    assert contract["providers"][0]["scalar_count"] == 40
    assert contract["providers"][1]["scalar_count"] == 34
    assert all(
        provider["diagonal_resolution_unique"]
        for provider in contract["providers"]
    )
