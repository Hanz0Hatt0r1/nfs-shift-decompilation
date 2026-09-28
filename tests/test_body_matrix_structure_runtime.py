import body_matrix_structure_runtime as runtime


def test_group_descriptors_match_recovered_body_offsets():
    assert runtime.group_descriptor(3) == {
        "count_offset": 0x98,
        "storage_offset": 0x160,
        "record_stride": 0x40,
        "scalar_index_offset": 0x30,
        "allocated_record_bytes": 0x40,
    }
    assert runtime.group_descriptor(2) == {
        "count_offset": 0x9C,
        "storage_offset": 0x164,
        "record_stride": 0xA0,
        "scalar_index_offset": 0x94,
        "allocated_record_bytes": 0xA0,
    }
    assert runtime.group_descriptor(1) == {
        "count_offset": 0xA0,
        "storage_offset": 0x168,
        "record_stride": 0x60,
        "scalar_index_offset": 0x30,
        "allocated_record_bytes": 0x60,
    }


def test_build_body_group_enforces_width():
    group = runtime.build_body_group(3, (10, 11, 12))
    assert group.width == 3
    assert group.scalar_indices == (10, 11, 12)

    try:
        runtime.build_body_group(2, (10,))
    except ValueError as exc:
        assert "requires 2 scalar indices" in str(exc)
    else:
        raise AssertionError("incorrect group width was accepted")


def test_body_structure_writes_symmetric_cartesian_products():
    groups = (
        runtime.build_body_group(2, (1, 2)),
        runtime.build_body_group(1, (3,)),
    )

    cells = runtime.matrix_cells_for_body_groups(groups)
    assert (1, 3) in cells
    assert (3, 1) in cells
    assert (2, 3) in cells
    assert (3, 2) in cells
    assert (1, 2) in cells
    assert (2, 1) in cells


def test_strict_upper_structure_drops_lower_triangle_and_keeps_diagonal_out():
    groups = (
        runtime.build_body_group(2, (1, 2)),
        runtime.build_body_group(1, (3,)),
    )

    upper = runtime.strict_upper_structure(groups)

    assert (1, 2) in upper
    assert (1, 3) in upper
    assert (2, 3) in upper
    assert (2, 1) not in upper
    assert (1, 1) not in upper


def test_validate_body_structure():
    result = runtime.validate_body_structure()

    assert result["ready"] is True
    assert result["errors"] == []


def test_source_contract_keeps_matrix_semantics_structural():
    result = runtime.build_source_contract()

    assert result["operation"]["cell_value"] == (
        "exact binary64 1.0"
    )
    assert result["operation"]["symmetry"] == (
        "both [row][column] and [column][row] are written"
    )
    assert result["interpretation"]["matrix_role"] == (
        "structural support seed"
    )
