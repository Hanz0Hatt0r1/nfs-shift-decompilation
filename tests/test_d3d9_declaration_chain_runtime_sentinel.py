import struct

from d3d9_declaration_chain_evidence import analyze_d3d9_declaration_chain
from d3d9_declaration_sentinel_evidence import analyze_d3d9_declaration_sentinel
from d3d9_memory_declaration_evidence import capture_d3d9_memory_declaration


SOURCE = """
uint FUN_008587e0(int param_1,int param_2)
{
  *(undefined2 *)(*(int *)(param_1 + 0x1c) + (int)pAVar22 * 8) = 0xff;
  *(undefined2 *)(*(int *)(param_1 + 0x1c) + 2 + (int)pAVar22 * 8) = 0;
  *(undefined1 *)(*(int *)(param_1 + 0x1c) + 4 + (int)pAVar22 * 8) = 0x11;
  *(undefined1 *)(*(int *)(param_1 + 0x1c) + 5 + (int)pAVar22 * 8) = 0;
  *(undefined1 *)(*(int *)(param_1 + 0x1c) + 6 + (int)pAVar22 * 8) = 0;
  *(undefined1 *)(*(int *)(param_1 + 0x1c) + 7 + (int)pAVar22 * 8) = 0;
}
"""


def _base_inputs():
    return {
        "type_profile": {"validation": {"status": "match", "match_count": 17}},
        "stream_topology": {
            "status": "observed",
            "grouping": {"group_stride": 0x14},
            "semantic_links": {
                "stream_group_to_record_pointer": {"status": "observed"},
                "type_to_group_byte_size": {"status": "observed"},
            },
        },
        "stream_record": {
            "status": "observed",
            "record": {"stride": 8},
            "fields": [{"status": "observed"} for _ in range(6)],
            "semantic_links": {
                "xml_type_to_record_type_code": {"status": "observed"},
                "xml_usage_to_record_usage_code": {"status": "observed"},
                "xml_channel_to_record_usage_index": {"status": "observed"},
            },
        },
        "canonicalizer": {
            "status": "observed",
            "canonicalization": {"full_record_identity": "observed"},
        },
    }


def test_runtime_sentinel_matches_source_producer():
    memory = capture_d3d9_memory_declaration(
        struct.pack("<HHBBBB", 0, 0, 2, 0, 6, 0)
        + struct.pack("<HHBBBB", 0xFFFF, 0, 0x11, 0, 0, 0),
        base_address=0x7000,
    )
    source = analyze_d3d9_declaration_sentinel(SOURCE)

    result = analyze_d3d9_declaration_chain(
        **_base_inputs(),
        runtime_memory_evidence=memory,
        declaration_sentinel_evidence=source,
    )

    assert result["status"] == "observed"
    assert result["checks"]["runtime_source_sentinel_coherence"]["status"] == "observed"
    assert result["summary"]["runtime_sentinel_coherence_status"] == "observed"
    assert result["runtime_sentinel_coherence"]["expected_sentinel"] == {
        "stream": 0xFFFF,
        "offset": 0,
        "type": 0x11,
        "method": 0,
        "usage": 0,
        "usage_index": 0,
    }


def test_runtime_sentinel_tamper_blocks_source_coherence():
    memory = capture_d3d9_memory_declaration(
        struct.pack("<HHBBBB", 0, 0, 2, 0, 6, 0)
        + struct.pack("<HHBBBB", 0xFFFF, 0, 0x11, 0, 0, 0),
        base_address=0x8000,
    )
    memory["declaration_instance"]["records"][1]["usage"] = 1
    source = analyze_d3d9_declaration_sentinel(SOURCE)

    result = analyze_d3d9_declaration_chain(
        **_base_inputs(),
        runtime_memory_evidence=memory,
        declaration_sentinel_evidence=source,
    )

    assert result["status"] == "not-proven"
    assert result["checks"]["runtime_source_sentinel_coherence"]["status"] == "mismatch"
    assert result["runtime_sentinel_coherence"]["conflicts"][0]["field"] == "usage"


def test_source_sentinel_tamper_is_rejected_even_with_valid_runtime():
    memory = capture_d3d9_memory_declaration(
        struct.pack("<HHBBBB", 0, 0, 2, 0, 6, 0)
        + struct.pack("<HHBBBB", 0xFFFF, 0, 0x11, 0, 0, 0),
        base_address=0x9000,
    )
    source = analyze_d3d9_declaration_sentinel(
        SOURCE.replace(
            "+ 7 + (int)pAVar22 * 8) = 0;",
            "+ 7 + (int)pAVar22 * 8) = 1;",
        )
    )

    result = analyze_d3d9_declaration_chain(
        **_base_inputs(),
        runtime_memory_evidence=memory,
        declaration_sentinel_evidence=source,
    )

    assert result["status"] == "not-proven"
    assert result["checks"]["d3d9_declaration_sentinel"]["status"] == "not-proven"
    assert result["checks"]["runtime_source_sentinel_coherence"]["status"] == "not-proven"
