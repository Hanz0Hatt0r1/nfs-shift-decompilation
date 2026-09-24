import struct

from d3d9_declaration_chain_evidence import analyze_d3d9_declaration_chain
from d3d9_memory_declaration_evidence import capture_d3d9_memory_declaration


def _base_inputs():
    return {
        "type_profile": {
            "validation": {"status": "match", "match_count": 17},
        },
        "stream_topology": {
            "status": "observed",
            "grouping": {
                "group_stride": 0x14,
            },
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


def _memory_dump():
    return b"".join(
        (
            struct.pack("<HHBBBB", 0, 0, 2, 0, 6, 0),
            struct.pack("<HHBBBB", 0, 12, 4, 0, 6, 1),
            struct.pack("<HHBBBB", 0xFFFF, 0, 0x11, 0, 0, 0),
        )
    )


def test_declaration_chain_accepts_coherent_runtime_memory_evidence():
    evidence = capture_d3d9_memory_declaration(
        _memory_dump(),
        base_address=0x12340000,
        source_name="capture.bin",
    )
    result = analyze_d3d9_declaration_chain(
        **_base_inputs(),
        runtime_memory_evidence=evidence,
    )

    assert result["status"] == "observed"
    assert result["checks"]["declaration_instance"]["status"] == "observed"
    assert result["checks"]["runtime_memory_provenance"]["status"] == "observed"
    assert result["summary"]["runtime_memory_status"] == "match"
    assert result["evidence_boundary"]["runtime_memory_dump"] == "observed"
    assert result["evidence_boundary"]["runtime_declaration_instance"] == "observed"


def test_declaration_chain_rejects_tampered_runtime_memory_bytes():
    evidence = capture_d3d9_memory_declaration(
        _memory_dump(),
        base_address=0x12340000,
    )
    tampered = dict(evidence)
    tampered["bytes"] = dict(evidence["bytes"])
    tampered["bytes"]["hex"] = "01" + evidence["bytes"]["hex"][2:]

    result = analyze_d3d9_declaration_chain(
        **_base_inputs(),
        runtime_memory_evidence=tampered,
    )

    assert result["status"] == "not-proven"
    assert result["checks"]["runtime_memory_provenance"]["status"] == "not-proven"
    assert "runtime_memory_provenance" in result["summary"]["blocking_checks"]
