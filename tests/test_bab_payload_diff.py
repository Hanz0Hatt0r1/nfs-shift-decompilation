from bab_payload_diff import compare_bab_payload_bytes


def test_bab_payload_compare_identical_data():
    data = b"\x01\x02\x03\x04" * 8
    result = compare_bab_payload_bytes(data, data)
    assert result["size_delta"] == 0
    assert result["equal_overlap_bytes"] == len(data)
    assert result["differing_overlap_bytes"] == 0
    assert result["overlap_equal_ratio"] == 1.0
    assert result["equal_prefix_bytes"] == len(data)
    assert result["equal_suffix_bytes"] == len(data)
    assert result["block_match_ratio"]["16"] == 1.0


def test_bab_payload_compare_measures_shared_prefix_only():
    a = b"HEADER" + b"AAAA" * 8
    b = b"HEADER" + b"BBBB" * 8
    result = compare_bab_payload_bytes(a, b)
    assert result["equal_prefix_bytes"] == 6
    assert result["equal_suffix_bytes"] == 0
    assert result["differing_overlap_bytes"] == len(a) - 6
    assert 0.0 < result["overlap_equal_ratio"] < 1.0


def test_bab_payload_compare_handles_different_lengths():
    a = bytes(range(32))
    b = bytes(range(16)) + b"Z" * 32
    result = compare_bab_payload_bytes(a, b)
    assert result["size_delta"] == -16
    assert result["overlap_size"] == 32
    assert result["equal_overlap_bytes"] == 16
    assert result["equal_suffix_bytes"] == 0
