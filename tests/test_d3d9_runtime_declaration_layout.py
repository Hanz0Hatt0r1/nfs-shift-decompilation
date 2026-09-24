import struct

from d3d9_memory_declaration_evidence import capture_d3d9_memory_declaration
from d3d9_runtime_declaration_layout import validate_d3d9_runtime_declaration_layout


def _dump():
    return b"".join(
        (
            struct.pack("<HHBBBB", 0, 0, 2, 0, 6, 0),
            struct.pack("<HHBBBB", 0, 12, 4, 0, 6, 1),
            struct.pack("<HHBBBB", 0xFFFF, 0, 0x11, 0, 0, 0),
        )
    )


def test_runtime_layout_matches_recovered_type_sizes():
    evidence = capture_d3d9_memory_declaration(
        _dump(),
        base_address=0x401000,
        source_name="capture.bin",
    )

    result = validate_d3d9_runtime_declaration_layout(evidence)

    assert result["status"] == "match"
    assert result["input_kind"] == "memory-wrapper"
    assert result["record_stride"] == 8
    assert result["declaration"]["end_sentinel_status"] == "observed"
    assert result["stream_summaries"] == [
        {
            "stream": 0,
            "element_count": 2,
            "byte_size": 16,
            "final_offset": 16,
            "type_codes": [2, 4],
            "contiguous_offsets": True,
        }
    ]
    assert result["semantic_links"]["offsets_follow_type_sizes"]["status"] == "observed"
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_runtime_layout_rejects_wrong_second_offset():
    report = capture_d3d9_memory_declaration(
        b"".join(
            (
                struct.pack("<HHBBBB", 0, 0, 2, 0, 6, 0),
                struct.pack("<HHBBBB", 0, 16, 4, 0, 6, 1),
                struct.pack("<HHBBBB", 0xFFFF, 0, 0x11, 0, 0, 0),
            )
        ),
        base_address=0x5000,
    )

    result = validate_d3d9_runtime_declaration_layout(report)

    assert result["status"] == "mismatch"
    assert result["issues"][0]["expected_offset"] == 12
    assert result["issues"][0]["observed_offset"] == 16
    assert result["semantic_links"]["offsets_follow_type_sizes"]["status"] == "mismatch"


def test_runtime_layout_is_partial_without_end_sentinel():
    report = capture_d3d9_memory_declaration(
        struct.pack("<HHBBBB", 0, 0, 2, 0, 6, 0),
        base_address=0x6000,
    )

    result = validate_d3d9_runtime_declaration_layout(report)

    assert result["status"] == "not-proven"
    assert result["declaration"]["end_sentinel_status"] == "not-present"
