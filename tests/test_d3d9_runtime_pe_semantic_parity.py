from d3d9_runtime_pe_semantic_parity import validate_runtime_against_pe


def _report():
    return {
        "format": "SHIFT.PEImageEvidence/1",
        "image": {"image_base": "0x00400000", "machine": "0x014c"},
        "decoded_tables": {
            "type_code": [{"ordinal": i, "value": i} for i in range(20)],
            "type_size": [
                {"ordinal": i, "value": value}
                for i, value in enumerate([4,8,12,16,4,4,4,8,4,4,8,4,8,4,4,4,8,0])
            ],
            "type_components": [
                {"ordinal": i, "value": value}
                for i, value in enumerate([1,2,3,4,4,4,2,4,4,2,4,2,4,3,3,2,4,0])
            ],
            "usage": [
                {"ordinal": i, "value": value}
                for i, value in enumerate([0,1,3,5,6,7,10,12,2])
            ],
        },
        "type_name_pointers": [{"ordinal": 4, "string": "RGBA32"}],
    }


def _runtime(records):
    return {
        "format": "SHIFT.D3D9DeclarationInstanceEvidence/1",
        "records": records,
    }


def test_runtime_declaration_matches_pe_numeric_abi():
    result = validate_runtime_against_pe(
        _runtime([
            {"type": 4, "usage": 10, "stream": 0, "offset": 0},
            {"type": 2, "usage": 3, "stream": 0, "offset": 12},
        ]),
        _report(),
    )
    assert result["ready"] is True
    assert result["records"][0]["d3d9_type"] == "D3DDECLTYPE_D3DCOLOR"
    assert result["records"][0]["usage_ordinal_candidates"] == [6]


def test_runtime_declaration_rejects_unknown_usage_value():
    result = validate_runtime_against_pe(
        _runtime([{"type": 4, "usage": 999}]),
        _report(),
    )
    assert result["ready"] is False
    assert "runtime-pe-parity:usage-value-not-in-pe-map:0:999" in result["blocking_reasons"]


def test_runtime_declaration_does_not_claim_m3_property_identity():
    result = validate_runtime_against_pe(
        _runtime([{"type": 4, "usage": 10}]),
        _report(),
    )
    assert result["policy"]["property_identity"] == "not-established-by-numeric-parity"
