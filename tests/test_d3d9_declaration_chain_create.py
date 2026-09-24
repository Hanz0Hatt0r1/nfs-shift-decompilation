from d3d9_declaration_chain_evidence import analyze_d3d9_declaration_chain


def _inputs():
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


def test_declaration_create_is_a_required_gate_when_supplied():
    result = analyze_d3d9_declaration_chain(
        **_inputs(),
        declaration_create_evidence={
            "format": "SHIFT.D3D9DeclarationCreateEvidence/1",
            "status": "observed",
            "semantic_links": {
                "canonical_record_bytes_to_create_call": {"status": "observed"},
            },
        },
    )

    assert result["status"] == "observed"
    assert result["checks"]["d3d9_declaration_create"]["status"] == "observed"
    assert result["summary"]["declaration_create_status"] == "observed"


def test_declaration_create_mismatch_blocks_chain():
    result = analyze_d3d9_declaration_chain(
        **_inputs(),
        declaration_create_evidence={
            "format": "SHIFT.D3D9DeclarationCreateEvidence/1",
            "status": "mismatch",
            "semantic_links": {
                "canonical_record_bytes_to_create_call": {"status": "not-proven"},
            },
        },
    )

    assert result["status"] == "not-proven"
    assert result["checks"]["d3d9_declaration_create"]["status"] == "mismatch"
