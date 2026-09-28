import specialized_provider_solver_runtime as runtime


def test_provider0_has_one_unique_reciprocal_per_scalar():
    spec = runtime.get_solver_spec(0)
    pivots = runtime.build_pivot_geometry(0)
    assert spec["unique_reciprocal_count"] == 40
    assert len(pivots) == 40
    assert pivots[0].diagonal_address == 0x00C21738
    assert pivots[1].diagonal_address == 0x00C21808
    assert pivots[2].diagonal_address == 0x00C218D8


def test_provider1_has_one_unique_reciprocal_per_scalar():
    spec = runtime.get_solver_spec(1)
    pivots = runtime.build_pivot_geometry(1)
    assert spec["unique_reciprocal_count"] == 34
    assert len(pivots) == 34
    assert pivots[0].diagonal_address == 0x00C1FE38
    assert pivots[1].diagonal_address == 0x00C1FEF0
    assert pivots[2].diagonal_address == 0x00C1FFA8


def test_pivot_formula_holds_for_every_provider0_scalar():
    pivots = runtime.build_pivot_geometry(0)
    for pivot in pivots:
        assert pivot.diagonal_address == pivot.row_pointer + 8 * pivot.index


def test_pivot_formula_holds_for_every_provider1_scalar():
    pivots = runtime.build_pivot_geometry(1)
    for pivot in pivots:
        assert pivot.diagonal_address == pivot.row_pointer + 8 * pivot.index


def test_source_reciprocal_counts_match_scalar_domains():
    c = runtime.build_solver_pivot_contract()
    assert c["providers"][0]["scalar_count"] == 40
    assert c["providers"][0]["unique_reciprocal_count"] == 40
    assert c["providers"][1]["scalar_count"] == 34
    assert c["providers"][1]["unique_reciprocal_count"] == 34


def test_geometry_validation_is_ready():
    assert runtime.validate_pivot_geometry(0)["ready"]
    assert runtime.validate_pivot_geometry(1)["ready"]


def test_solver_family_keeps_provider_unrolled_boundary_explicit():
    c = runtime.build_solver_pivot_contract()
    assert c["solver_family"]["classification"] == "fully-unrolled symmetric pivot/elimination routine"
    assert "unrolled coefficient expression" in " ".join(c["limitations"])
