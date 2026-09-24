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
            "source": {
                "name": "SHIFT.exe.c",
                "sha256": "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9",
                "bytes": 38993813,
                "line_count": 1471366,
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
            "source": {
                "name": "SHIFT.exe.c",
                "sha256": "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9",
                "bytes": 38993813,
                "line_count": 1471366,
            },
        },
        "canonicalizer": {
            "status": "observed",
            "canonicalization": {"full_record_identity": "observed"},
            "source": {
                "name": "SHIFT.exe.c",
                "sha256": "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9",
                "bytes": 38993813,
                "line_count": 1471366,
            },
        },
    }


def _api():
    return {
        "format": "SHIFT.D3D9ApiBindEvidence/1",
        "status": "observed",
        "source": {
            "name": "SHIFT.exe.c",
            "sha256": "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9",
            "bytes": 38993813,
            "line_count": 1471366,
        },
        "api_identity": {"method": "IDirect3DDevice9::SetVertexDeclaration", "vtable_slot": 87},
        "semantic_links": {
            "declaration_object_to_d3d9_bind": {"status": "observed"},
        },
    }


def test_api_bind_is_a_required_gate_when_supplied():
    result = analyze_d3d9_declaration_chain(**_inputs(), api_bind_evidence=_api())

    assert result["status"] == "observed"
    assert result["checks"]["d3d9_api_bind"]["status"] == "observed"
    assert result["summary"]["api_bind_status"] == "observed"
    assert result["source_provenance"]["status"] == "observed"


def test_api_bind_snapshot_conflict_blocks_the_chain():
    api = _api()
    api["source"]["sha256"] = "other"
    result = analyze_d3d9_declaration_chain(**_inputs(), api_bind_evidence=api)

    assert result["status"] == "not-proven"
    assert result["checks"]["d3d9_api_bind"]["status"] == "observed"
    assert result["checks"]["source_provenance_coherence"]["status"] == "mismatch"
    assert "source_provenance_coherence" in result["summary"]["blocking_checks"]
