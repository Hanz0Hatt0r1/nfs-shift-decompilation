from d3d9_pe_semantic_map import build_d3d9_pe_semantic_map


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
        "type_name_pointers": [
            {"ordinal": 4, "string": "RGBA32"},
        ],
    }


def test_pe_semantic_map_is_ready_for_complete_tables():
    result = build_d3d9_pe_semantic_map(_report())
    assert result["format"] == "SHIFT.D3D9PESemanticMap/1"
    assert result["ready"] is True
    assert result["types"][4]["d3d9_type"] == "D3DDECLTYPE_D3DCOLOR"
    assert result["types"][4]["internal_name"] == "RGBA32"
    assert result["types"][4]["element_size_bytes"] == 4
    assert result["types"][4]["source_components"] == 4
    assert result["usages"][6]["source_name"] == "Colour"
    assert result["usages"][6]["numeric_d3d9_usage"] == 10
    assert result["color_abi"]["status"] == "observed"


def test_pe_semantic_map_fails_closed_on_type_table_mismatch():
    report = _report()
    report["decoded_tables"]["type_size"][4]["value"] = 16
    result = build_d3d9_pe_semantic_map(report)
    assert result["ready"] is False
    assert "pe-semantic-map:type-size-mismatch:4:16:4" in result["blocking_reasons"]


def test_pe_semantic_map_fails_closed_when_usage_is_missing():
    report = _report()
    report["decoded_tables"]["usage"] = report["decoded_tables"]["usage"][:6]
    result = build_d3d9_pe_semantic_map(report)
    assert result["ready"] is False
    assert "pe-semantic-map:usage-missing:6" in result["blocking_reasons"]
