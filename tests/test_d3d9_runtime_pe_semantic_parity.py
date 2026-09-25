from d3d9_runtime_pe_semantic_parity import validate_runtime_against_pe
from tests.test_d3d9_pe_semantic_map import _report


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
