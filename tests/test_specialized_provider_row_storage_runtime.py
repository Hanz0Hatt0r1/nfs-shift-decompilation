import specialized_provider_row_storage_runtime as runtime


def test_provider0_has_exact_40_row_pointers():
    pointers = runtime.get_row_pointers(0)
    assert len(pointers) == 40
    assert pointers[0] == 0x00C21738
    assert pointers[-1] == 0x00C23B28
    assert runtime.validate_row_pointer_table(0)["ready"]


def test_provider1_has_exact_34_row_pointers():
    pointers = runtime.get_row_pointers(1)
    assert len(pointers) == 34
    assert pointers[0] == 0x00C1FE38
    assert pointers[-1] == 0x00C21478
    assert runtime.validate_row_pointer_table(1)["ready"]


def test_provider0_segment_sizes_sum_to_1190_doubles():
    segments = runtime.build_row_segments(0)
    assert sum(segment.doubles for segment in segments) == 1190
    assert segments[0].doubles == 25
    assert segments[19].doubles == 40
    assert segments[-1].doubles == 40


def test_provider1_segment_sizes_sum_to_746_doubles():
    segments = runtime.build_row_segments(1)
    assert sum(segment.doubles for segment in segments) == 746
    assert segments[0].doubles == 22
    assert segments[9].doubles == 12
    assert segments[-1].doubles == 34


def test_last_segment_ends_at_output_vector():
    p0 = runtime.build_row_segments(0)[-1]
    p1 = runtime.build_row_segments(1)[-1]
    assert p0.end == 0x00C23C68
    assert p1.end == 0x00C21588


def test_storage_capacity_is_not_named_as_matrix_nonzero_count():
    contract = runtime.build_row_storage_contract()
    for provider in contract["providers"]:
        assert "storage capacity/extent" in " ".join(contract["limitations"])
