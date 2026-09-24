import struct

from d3d9_declaration_chain_evidence import analyze_d3d9_declaration_chain
from d3d9_memory_declaration_evidence import capture_d3d9_memory_declaration
from d3d9_runtime_declaration_layout import validate_d3d9_runtime_declaration_layout


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
            "fields": [
                {"name": name, "offset": offset, "width": width, "status": "observed"}
                for name, offset, width in (
                    ("stream", 0, 2),
                    ("offset", 2, 2),
                    ("type", 4, 1),
                    ("method", 5, 1),
                    ("usage", 6, 1),
                    ("usage_index", 7, 1),
                )
            ],
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


def _memory():
    return b"".join(
        (
            struct.pack("<HHBBBB", 0, 0, 2, 0, 6, 0),
            struct.pack("<HHBBBB", 0, 12, 4, 0, 6, 1),
            struct.pack("<HHBBBB", 0xFFFF, 0, 0x11, 0, 0, 0),
        )
    )


def test_chain_accepts_runtime_layout_evidence():
    memory = capture_d3d9_memory_declaration(
        _memory(),
        base_address=0x401000,
        source_name="capture.bin",
    )
    layout = validate_d3d9_runtime_declaration_layout(memory)

    result = analyze_d3d9_declaration_chain(
        **_base_inputs(),
        runtime_memory_evidence=memory,
        runtime_layout_evidence=layout,
    )

    assert result["status"] == "observed"
    assert result["checks"]["runtime_memory_provenance"]["status"] == "observed"
    assert result["checks"]["runtime_declaration_layout"]["status"] == "observed"
    assert result["summary"]["runtime_layout_status"] == "match"


def test_chain_blocks_runtime_layout_mismatch():
    memory = capture_d3d9_memory_declaration(
        _memory(),
        base_address=0x401000,
    )
    layout = validate_d3d9_runtime_declaration_layout(memory)
    tampered = dict(layout)
    tampered["status"] = "mismatch"
    tampered["issues"] = [
        {
            "index": 1,
            "reason": "offset does not follow recovered Type byte size",
        }
    ]

    result = analyze_d3d9_declaration_chain(
        **_base_inputs(),
        runtime_memory_evidence=memory,
        runtime_layout_evidence=tampered,
    )

    assert result["status"] == "not-proven"
    assert result["checks"]["runtime_declaration_layout"]["status"] == "mismatch"
    assert "runtime_declaration_layout" in result["summary"]["blocking_checks"]
