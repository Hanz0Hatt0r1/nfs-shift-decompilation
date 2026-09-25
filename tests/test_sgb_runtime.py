import struct

import pytest

from sgb_runtime import SGBRuntimeDecodeError, parse_sgb_runtime


def _chunk(tag: str, payload: bytes) -> bytes:
    return tag[::-1].encode("ascii") + struct.pack("<I", 8 + len(payload)) + payload


def _header(flags: int = 0) -> bytes:
    return b" \x42\x47\x53" + struct.pack("<III", 0x10, flags, 0)


def test_header_and_end_chunk():
    report = parse_sgb_runtime(_header() + _chunk("END ", b""))
    assert report["ready"] is True
    assert report["header"]["word_1"] == 0x10
    assert report["chunks"][0]["tag"] == "END "


def test_part_record_uses_partition_id_and_variable_child_table():
    record = struct.pack("<II", 7, 0)
    record += struct.pack("<ffffff", -1, -2, -3, 1, 2, 3)
    record += struct.pack("<IIII", 10, 11, 12, 13)
    record += struct.pack("<I", 2)
    record += struct.pack("<II", 99, 100)
    payload = struct.pack("<I", 1) + record
    data = _header() + _chunk("PART", payload) + _chunk("END ", b"")
    row = parse_sgb_runtime(data)["chunks"][0]["records"][0]
    assert row["partition_id"] == 7
    assert row["aabbox_min"] == [ -1.0, -2.0, -3.0]
    assert row["aabbox_max"] == [1.0, 2.0, 3.0]
    assert row["fixed_quad"] == [10, 11, 12, 13]
    assert row["child_object_indices"] == [99, 100]


def test_node_header_and_flags():
    record = struct.pack("<IIIIIIII", 32, 0, 32, 0, 0, 2, 0, 0)
    data = _header() + _chunk("NODE", struct.pack("<I", 1) + record) + _chunk("END ", b"")
    row = parse_sgb_runtime(data)["chunks"][0]["records"][0]
    assert row["stride"] == 32
    assert row["instances"] == 2
    assert row["flags"]["present"] is False
    assert row["variation_index"] == 0


def test_summ_and_occl_fixed_record_shape():
    # Two zero relative offsets plus four vec3 values.
    record = struct.pack("<14I", 0, 0, *([0] * 12))
    for tag in ("SUMM", "OCCL"):
        data = _header() + _chunk(tag, struct.pack("<I", 1) + record) + _chunk("END ", b"")
        row = parse_sgb_runtime(data)["chunks"][0]["records"][0]
        assert row["record_bytes"] == 56


def test_truncated_chunk_blocks_non_strict():
    data = _header() + b"EDNE" + struct.pack("<I", 64)
    result = parse_sgb_runtime(data, strict=False)
    assert result["ready"] is False
    assert any(x.startswith("chunk-truncated") for x in result["blockers"])


def test_invalid_magic_rejected():
    with pytest.raises(SGBRuntimeDecodeError):
        parse_sgb_runtime(b"not-sgb")
