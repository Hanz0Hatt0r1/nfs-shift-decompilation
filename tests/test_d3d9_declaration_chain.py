from d3d9_declaration_chain_evidence import analyze_d3d9_declaration_chain


def _type_profile_match():
    from d3d9_type_profile import validate_type_tables

    return validate_type_tables(
        [4, 8, 12, 16, 4, 4, 4, 8, 4, 4, 8, 4, 8, 4, 4, 4, 8],
        [1, 2, 3, 4, 4, 4, 2, 4, 4, 2, 4, 2, 4, 3, 3, 2, 4],
    )


def _stream_topology():
    return {
        "format": "SHIFT.D3D9StreamTopologyEvidence/1",
        "status": "observed",
        "source": {"kind": "shift-exe-c", "bytes": 100, "line_count": 10},
        "grouping": {
            "group_stride": 0x14,
            "record_pointer_array": "observed",
            "byte_size_accumulation": "observed",
        },
        "semantic_links": {
            "stream_group_to_record_pointer": {"status": "observed"},
            "type_to_group_byte_size": {"status": "observed"},
        },
    }


def _stream_record():
    return {
        "format": "SHIFT.D3D9StreamRecordEvidence/1",
        "status": "observed",
        "source": {"kind": "shift-exe-c", "bytes": 100, "line_count": 10},
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
        "meb_property_mapping": {"status": "not-proven"},
    }


def _canonicalizer():
    return {
        "format": "SHIFT.D3D9DeclarationCanonicalizerEvidence/1",
        "status": "observed",
        "source": {"kind": "shift-exe-c", "bytes": 100, "line_count": 10},
        "canonicalization": {
            "record_stride": 8,
            "full_record_identity": "observed",
        },
        "semantic_links": {
            "d3dvertexelement9_shape": {"status": "observed"},
        },
        "meb_property_mapping": {"status": "not-proven"},
    }


def test_d3d9_declaration_chain_is_observed_when_all_evidence_links_match():
    result = analyze_d3d9_declaration_chain(
        type_profile=_type_profile_match(),
        stream_topology=_stream_topology(),
        stream_record=_stream_record(),
        canonicalizer=_canonicalizer(),
        pe_evidence={
            "type_profile_validation": {
                "validation": {"status": "match", "match_count": 17}
            }
        },
    )

    assert result["format"] == "SHIFT.D3D9DeclarationChainEvidence/1"
    assert result["status"] == "observed"
    assert result["summary"]["observed_checks"] == 9
    assert result["summary"]["blocking_checks"] == []
    assert result["summary"]["type_match_count"] == 17
    assert result["summary"]["record_stride"] == 8
    assert result["summary"]["group_stride"] == 0x14
    assert result["evidence_boundary"]["source_backed"] is True
    assert result["evidence_boundary"]["pe_file_backed_validation"] == "match"
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_d3d9_declaration_chain_fails_closed_when_a_link_is_missing():
    record = _stream_record()
    record["semantic_links"]["xml_usage_to_record_usage_code"]["status"] = "not-proven"

    result = analyze_d3d9_declaration_chain(
        type_profile=_type_profile_match(),
        stream_topology=_stream_topology(),
        stream_record=record,
        canonicalizer=_canonicalizer(),
    )

    assert result["status"] == "not-proven"
    assert "xml_usage_to_record_usage" in result["summary"]["blocking_checks"]
    assert result["summary"]["observed_checks"] == 8
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_d3d9_declaration_chain_does_not_treat_mismatched_type_profile_as_ready():
    profile = _type_profile_match()
    profile["validation"]["status"] = "mismatch"
    profile["validation"]["match_count"] = 16

    result = analyze_d3d9_declaration_chain(
        type_profile=profile,
        stream_topology=_stream_topology(),
        stream_record=_stream_record(),
        canonicalizer=_canonicalizer(),
    )

    assert result["status"] == "not-proven"
    assert result["checks"]["type_table_semantics"]["status"] == "mismatch"
    assert "type_table_semantics" in result["summary"]["blocking_checks"]


def _meb_color_bridge():
    return {
        "format": "SHIFT.MEBD3D9ColorBridgeEvidence/1",
        "selection": "not-selected",
        "verified_abi": False,
        "d3d9_candidates": {
            "status": "ambiguous",
            "types": [
                {"code": 4, "name": "D3DCOLOR"},
                {"code": 8, "name": "UBYTE4N"},
            ],
        },
        "properties": {
            "460": {"meb_storage": {"status": "observed"}},
            "461": {"meb_storage": {"status": "observed"}},
        },
        "meb_property_mapping": {"status": "not-proven"},
    }


def test_meb_color_bridge_is_nonselecting_evidence_when_supplied():
    result = analyze_d3d9_declaration_chain(
        type_profile=_type_profile_match(),
        stream_topology=_stream_topology(),
        stream_record=_stream_record(),
        canonicalizer=_canonicalizer(),
        pe_evidence={
            "type_profile_validation": {
                "validation": {"status": "match", "match_count": 17}
            }
        },
        meb_color_bridge_evidence=_meb_color_bridge(),
    )

    assert result["status"] == "observed"
    assert result["checks"]["meb_color_bridge"]["status"] == "observed"
    assert result["summary"]["meb_color_bridge_status"] == "observed"
    assert result["meb_property_mapping"]["status"] == "not-proven"
    assert result["meb_color_bridge_evidence"]["selection"] == "not-selected"


def test_meb_color_bridge_mismatch_blocks_the_chain_when_supplied():
    bridge = _meb_color_bridge()
    bridge["meb_property_mapping"]["status"] = "mismatch"

    result = analyze_d3d9_declaration_chain(
        type_profile=_type_profile_match(),
        stream_topology=_stream_topology(),
        stream_record=_stream_record(),
        canonicalizer=_canonicalizer(),
        meb_color_bridge_evidence=bridge,
    )

    assert result["status"] == "not-proven"
    assert result["checks"]["meb_color_bridge"]["status"] == "mismatch"
    assert "meb_color_bridge" in result["summary"]["blocking_checks"]


def test_meb_color_bridge_missing_one_property_is_not_observed():
    bridge = _meb_color_bridge()
    del bridge["properties"]["461"]

    result = analyze_d3d9_declaration_chain(
        type_profile=_type_profile_match(),
        stream_topology=_stream_topology(),
        stream_record=_stream_record(),
        canonicalizer=_canonicalizer(),
        meb_color_bridge_evidence=bridge,
    )

    assert result["status"] == "not-proven"
    assert result["checks"]["meb_color_bridge"]["status"] == "not-proven"
    assert "meb_color_bridge" in result["summary"]["blocking_checks"]
