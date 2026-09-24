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
                {"status": "observed"}
                for _ in range(6)
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


def _add_source_provenance(inputs, sha):
    for report in (
        inputs["stream_topology"],
        inputs["stream_record"],
        inputs["canonicalizer"],
    ):
        report["source"] = {
            "name": "SHIFT.exe.c",
            "sha256": sha,
            "bytes": 38993813,
            "line_count": 1471366,
        }


def test_source_provenance_coherence_is_observed_for_one_source_snapshot():
    inputs = _inputs()
    _add_source_provenance(
        inputs,
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9",
    )

    result = analyze_d3d9_declaration_chain(**inputs)

    assert result["status"] == "observed"
    assert result["checks"]["source_provenance_coherence"]["status"] == "observed"
    assert result["summary"]["source_provenance_status"] == "observed"
    assert result["source_provenance"]["reference"]["name"] == "SHIFT.exe.c"
    assert result["source_provenance"]["conflicts"] == []


def test_source_provenance_conflict_blocks_the_chain():
    inputs = _inputs()
    _add_source_provenance(inputs, "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9")
    inputs["canonicalizer"]["source"]["sha256"] = "different-sha"

    result = analyze_d3d9_declaration_chain(**inputs)

    assert result["status"] == "not-proven"
    assert result["checks"]["source_provenance_coherence"]["status"] == "mismatch"
    assert "source_provenance_coherence" in result["summary"]["blocking_checks"]
    assert any(conflict["field"] == "sha256" for conflict in result["source_provenance"]["conflicts"])


def test_absent_source_hash_keeps_legacy_source_only_mode():
    result = analyze_d3d9_declaration_chain(**_inputs())

    assert result["status"] == "observed"
    assert result["summary"]["source_provenance_status"] == "not-supplied"
    assert "source_provenance_coherence" not in result["checks"]
