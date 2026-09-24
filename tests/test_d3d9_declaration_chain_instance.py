from d3d9_declaration_chain_evidence import analyze_d3d9_declaration_chain


def _inputs():
    return {
        "type_profile": {
            "validation": {"status": "match", "match_count": 17},
        },
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
                {"name": str(i), "status": "observed"}
                for i in range(6)
            ],
            "semantic_links": {
                "xml_type_to_record_type_code": {"status": "observed"},
                "xml_usage_to_record_usage_code": {"status": "observed"},
                "xml_channel_to_record_usage_index": {"status": "observed"},
            },
        },
        "canonicalizer": {
            "status": "observed",
            "canonicalization": {
                "full_record_identity": "observed",
                "record_stride": 8,
            },
        },
    }


def test_declaration_chain_accepts_supplied_runtime_instance():
    inputs = _inputs()
    result = analyze_d3d9_declaration_chain(
        **inputs,
        declaration_instance={
            "format": "SHIFT.D3D9DeclarationInstanceEvidence/1",
            "status": "match",
            "record_stride": 8,
            "semantic_links": {
                "d3dvertexelement9_shape": {"status": "observed"},
            },
        },
    )

    assert result["status"] == "observed"
    assert result["summary"]["required_checks"] == 10
    assert result["checks"]["declaration_instance"]["status"] == "observed"
    assert result["evidence_boundary"]["runtime_declaration_instance"] == "observed"


def test_declaration_chain_blocks_supplied_mismatched_runtime_instance():
    inputs = _inputs()
    result = analyze_d3d9_declaration_chain(
        **inputs,
        declaration_instance={
            "format": "SHIFT.D3D9DeclarationInstanceEvidence/1",
            "status": "mismatch",
            "record_stride": 8,
            "semantic_links": {
                "d3dvertexelement9_shape": {"status": "observed"},
            },
        },
    )

    assert result["status"] == "not-proven"
    assert result["checks"]["declaration_instance"]["status"] == "mismatch"
    assert "declaration_instance" in result["summary"]["blocking_checks"]
    assert result["evidence_boundary"]["runtime_declaration_instance"] == "mismatch"
