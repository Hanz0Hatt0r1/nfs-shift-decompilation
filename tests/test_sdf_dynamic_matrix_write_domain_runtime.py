import sdf_dynamic_matrix_write_domain_runtime as runtime


def _domain():
    return {
        "solver_scalar_count": 6,
        "records": [
            {
                "runtime_record_index": 0,
                "section": "JOINT",
                "solver_width": 3,
                "scalar_base": 0,
                "scalar_indices": [0, 1, 2],
                "posbody": "A",
                "negbody": "B",
            },
            {
                "runtime_record_index": 1,
                "section": "HINGE",
                "solver_width": 2,
                "scalar_base": 3,
                "scalar_indices": [3, 4],
                "posbody": "B",
                "negbody": "C",
            },
            {
                "runtime_record_index": 2,
                "section": "BAR",
                "solver_width": 1,
                "scalar_base": 5,
                "scalar_indices": [5],
                "posbody": "C",
                "negbody": "A",
            },
        ],
    }


def test_dynamic_domain_builds_self_and_pair_writes():
    result = runtime.build_dynamic_write_domain(_domain())

    assert result["ready"] is True
    assert result["runtime_constraint_records"] == 3
    assert result["shared_constraint_pairs"] == 3
    assert result["self_cell_count"] == 10
    assert result["pair_cell_count"] == 11
    assert result["union_cell_count"] == 21


def test_dynamic_domain_uses_expected_kernel_ownership():
    result = runtime.build_dynamic_write_domain(_domain())

    kernels = {
        entry["kernel"]
        for entry in result["writes"]
    }

    assert kernels == {
        "FUN_007bbb80",
        "FUN_007bb250",
        "FUN_007bb6c0",
    }


def test_dynamic_domain_provenance_uses_lower_triangle_cells_only():
    result = runtime.build_dynamic_write_domain(_domain())

    for key in result["cell_provenance"]:
        row_text, column_text = key.split(",", 1)
        row = int(row_text)
        column = int(column_text)
        assert row >= column


def test_dynamic_domain_can_lookup_pair_provenance():
    result = runtime.build_dynamic_write_domain(_domain())

    entries = runtime.provenance_for_dynamic_cell(
        result,
        3,
        0,
    )

    assert entries
    assert entries[0]["kind"] == "pair"
    assert entries[0]["kernel"] in {
        "FUN_007bbb80",
        "FUN_007bb250",
        "FUN_007bb6c0",
    }


def test_validate_dynamic_domain_accepts_valid_fixture():
    result = runtime.build_dynamic_write_domain_contract(_domain())

    assert result["validation"]["ready"] is True
    assert result["validation"]["errors"] == []


def test_validate_dynamic_domain_rejects_upper_cell_provenance():
    result = runtime.build_dynamic_write_domain(_domain())
    result["cell_provenance"]["0,3"] = [
        {
            "kernel": "FUN_007bbb80",
        }
    ]

    validation = runtime.validate_dynamic_write_domain(result)

    assert validation["ready"] is False
    assert "dynamic-cell-out-of-lower-domain:0,3" in validation["errors"]


def test_validate_dynamic_domain_rejects_unknown_kernel():
    result = runtime.build_dynamic_write_domain(_domain())
    result["cell_provenance"]["0,0"][0]["kernel"] = "FUN_unknown"

    validation = runtime.validate_dynamic_write_domain(result)

    assert validation["ready"] is False
    assert any(
        error.startswith("unknown-dynamic-kernel:0,0")
        for error in validation["errors"]
    )


def test_validate_dynamic_domain_checks_provenance_count():
    result = runtime.build_dynamic_write_domain(_domain())
    result["union_cell_count"] += 1

    validation = runtime.validate_dynamic_write_domain(result)

    assert validation["ready"] is False
    assert "dynamic-cell-count-provenance-mismatch" in validation["errors"]


def test_summarize_dynamic_write_domain():
    result = runtime.summarize_dynamic_write_domain(
        {
            "scalar_count": 40,
            "runtime_constraint_records": 28,
            "shared_constraint_pairs": 30,
            "self_cell_count": 100,
            "pair_cell_count": 200,
            "union_cell_count": 280,
            "lower_triangle_off_diagonal_cell_count": 140,
            "kernel_write_counts": {
                "FUN_007bbb80": 20,
                "FUN_007bb250": 20,
                "FUN_007bb6c0": 10,
            },
            "ready": True,
        }
    )

    assert result["scalar_count"] == 40
    assert result["lower_triangle_off_diagonal_cell_count"] == 140
    assert result["kernel_write_counts"]["FUN_007bbb80"] == 20
    assert result["ready"] is True


def test_pair_lower_cells_are_orientation_independent():
    assert runtime._pair_lower_cells(0, 3, 3, 2) == {
        (3, 0),
        (3, 1),
        (3, 2),
        (4, 0),
        (4, 1),
        (4, 2),
    }
    assert runtime._pair_lower_cells(3, 2, 0, 3) == {
        (3, 0),
        (3, 1),
        (3, 2),
        (4, 0),
        (4, 1),
        (4, 2),
    }
