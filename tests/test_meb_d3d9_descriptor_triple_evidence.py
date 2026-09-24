from meb_d3d9_descriptor_triple_evidence import analyze_meb_d3d9_descriptor_triple


SOURCE_REPORT = {
    "format": "SHIFT.D3D9SourceVertexEvidence/1",
    "observations": [
        {"id": "binary-descriptor-triple-semantics", "status": "observed", "function": "FUN_00859800"},
        {"id": "binary-mesh-loader-identity", "status": "observed", "function": "FUN_00859800"},
        {"id": "meb-extension-registration", "status": "observed"},
    ],
}


def _meb(descriptors):
    return {
        "format": "SHIFT.MEB",
        "property_descriptors": descriptors,
    }


def _descriptor(pid, words, offset=64):
    return {
        "id": pid,
        "offset": offset,
        "words": words,
        "raw_hex": b"".join(int(x).to_bytes(4, "little") for x in words).hex(),
    }


def test_exact_460_461_descriptor_triples_prove_type4_mapping():
    result = analyze_meb_d3d9_descriptor_triple(
        _meb([
            _descriptor("460", [4, 6, 0], 64),
            _descriptor("461", [4, 6, 1], 80),
        ]),
        SOURCE_REPORT,
    )

    assert result["format"] == "SHIFT.MEBD3D9DescriptorTripleEvidence/1"
    assert result["d3d9_type_mapping"]["status"] == "match"
    assert result["d3d9_type_mapping"]["type_codes"] == [4, 4]
    assert result["d3d9_type_mapping"]["usage_ordinals"] == [6, 6]
    assert result["d3d9_type_mapping"]["channels"] == [0, 1]
    assert result["meb_property_mapping"]["status"] == "match"
    assert result["properties"]["460"]["d3d9_type_mapping"]["d3d9_type_code"] == 4
    assert result["properties"]["461"]["d3d9_type_mapping"]["d3d9_type_code"] == 4
    assert result["selection"] == "resolved"
    assert result["verified_abi"] is True


def test_wrong_type_triple_fails_closed():
    result = analyze_meb_d3d9_descriptor_triple(
        _meb([
            _descriptor("460", [8, 6, 0]),
            _descriptor("461", [4, 6, 1], 80),
        ]),
        SOURCE_REPORT,
    )

    assert result["properties"]["460"]["descriptor_check"]["status"] == "mismatch"
    assert result["properties"]["460"]["d3d9_type_mapping"]["status"] == "mismatch"
    assert result["d3d9_type_mapping"]["status"] == "mismatch"
    assert result["meb_property_mapping"]["status"] == "mismatch"
    assert result["verified_abi"] is False


def test_missing_descriptor_is_partial():
    result = analyze_meb_d3d9_descriptor_triple(
        _meb([_descriptor("460", [4, 6, 0])]),
        SOURCE_REPORT,
    )

    assert result["properties"]["461"]["descriptor_check"]["status"] == "partial"
    assert result["properties"]["461"]["d3d9_type_mapping"]["status"] == "partial"
    assert result["d3d9_type_mapping"]["status"] == "partial"
    assert result["meb_property_mapping"]["status"] == "partial"
    assert result["verified_abi"] is False


def test_source_without_binary_loader_identity_does_not_promote_mapping():
    source = {
        "format": "SHIFT.D3D9SourceVertexEvidence/1",
        "observations": [
            {"id": "binary-descriptor-triple-semantics", "status": "observed"},
            {"id": "binary-mesh-loader-identity", "status": "not-found"},
            {"id": "meb-extension-registration", "status": "observed"},
        ],
    }
    result = analyze_meb_d3d9_descriptor_triple(
        _meb([
            _descriptor("460", [4, 6, 0]),
            _descriptor("461", [4, 6, 1], 80),
        ]),
        source,
    )
    assert result["d3d9_type_mapping"]["status"] == "partial"
    assert result["meb_property_mapping"]["status"] == "partial"


def test_malformed_source_report_is_rejected():
    result = analyze_meb_d3d9_descriptor_triple(
        _meb([
            _descriptor("460", [4, 6, 0]),
            _descriptor("461", [4, 6, 1], 80),
        ]),
        {"format": "SHIFT.Wrong/1", "observations": []},
    )
    assert result["d3d9_type_mapping"]["status"] == "partial"
    assert result["meb_property_mapping"]["status"] == "partial"
