from d3d9_unified_declaration_gate import build_unified_declaration_gate


def _chain(ready=True):
    return {
        "format": "SHIFT.D3D9DeclarationChainEvidence/1",
        "status": "observed" if ready else "not-proven",
    }


def _pe():
    return {
        "format": "SHIFT.D3D9PESemanticMap/1",
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "types": [],
        "usages": [],
    }


def _runtime():
    return {
        "format": "SHIFT.D3D9DeclarationInstanceEvidence/1",
        "records": [{"type": 4, "usage": 10}],
    }


def _pe_raw():
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


def test_unified_gate_accepts_ready_static_chain():
    result = build_unified_declaration_gate(_chain(), _pe())
    assert result["ready"] is True
    assert result["checks"]["declaration_chain"]["status"] == "observed"
    assert result["checks"]["pe_semantic_map"]["status"] == "observed"


def test_unified_gate_blocks_incomplete_chain():
    result = build_unified_declaration_gate(_chain(False), _pe())
    assert result["ready"] is False
    assert "unified-declaration:chain-not-ready" in result["blocking_reasons"]


def test_unified_gate_accepts_runtime_numeric_parity():
    result = build_unified_declaration_gate(
        _chain(),
        _pe(),
        runtime_declaration=_runtime(),
        pe_evidence=_pe_raw(),
    )
    assert result["ready"] is True
    assert result["checks"]["runtime_pe_numeric_parity"]["status"] == "observed"


def test_unified_gate_requires_pe_evidence_for_runtime_parity():
    result = build_unified_declaration_gate(
        _chain(),
        _pe(),
        runtime_declaration=_runtime(),
    )
    assert result["ready"] is False
    assert "unified-declaration:runtime-pe-evidence-missing" in result["blocking_reasons"]
