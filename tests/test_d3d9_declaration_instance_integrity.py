import struct


def test_d3d9_declaration_end_sentinel_is_detected():
    from d3d9_declaration_instance import decode_d3d9_declaration_records

    payload = struct.pack("<HHBBBB", 0, 0, 2, 0, 6, 0) + struct.pack(
        "<HHBBBB", 0xFFFF, 0, 0x11, 0, 0, 0
    )
    result = decode_d3d9_declaration_records(payload)

    assert result["status"] == "match"
    assert result["validation"]["end_sentinel_index"] == 1
    assert result["validation"]["end_sentinel_status"] == "observed"
    assert result["validation"]["terminator_indices"] == [1]


def test_d3d9_declaration_end_sentinel_requires_the_full_shape():
    from d3d9_declaration_instance import decode_d3d9_declaration_records

    payload = struct.pack("<HHBBBB", 0xFFFF, 4, 0x11, 0, 0, 0)
    result = decode_d3d9_declaration_records(payload)

    assert result["status"] == "match"
    assert result["validation"]["end_sentinel_index"] is None
    assert result["validation"]["end_sentinel_status"] == "not-present"
