from material_alpha_test import build_alpha_test_contract


def _enum(raw, index):
    return {
        "raw": raw,
        "engine_enum_index": index,
        "status": "known",
    }


def test_alpha_test_contract_reconstructs_exact_d3d9_states():
    result = build_alpha_test_contract({
        "format": "SHIFT.BMTAlphaTestState/1",
        "enabled": True,
        "function": _enum("ETF_GREATER_THAN_OR_EQUAL", 6),
        "value_raw": 64.0,
        "value_normalized": 64.0 / 255.0,
    })

    assert result["ready"] is True, result["blocking_reasons"]
    assert result["enabled"] is True
    assert result["compare"]["engine_enum_index"] == 6
    assert result["compare"]["d3d9_value"] == 7
    assert result["compare"]["d3d9_name"] == "D3DCMP_GREATEREQUAL"
    assert result["reference"]["d3d9_u8"] == 64
    assert result["reference"]["normalized"] == 64.0 / 255.0
    assert result["d3d9_render_states"]["D3DRS_ALPHATESTENABLE"] == {
        "id": 15,
        "value": 1,
    }
    assert result["d3d9_render_states"]["D3DRS_ALPHAFUNC"]["id"] == 25
    assert result["d3d9_render_states"]["D3DRS_ALPHAREF"] == {
        "id": 24,
        "value": 64,
    }
    assert result["native_execution"]["ready"] is False
    assert (
        "alpha-test:fragment-alpha-quantization-unproven"
        in result["native_execution"]["blocking_reasons"]
    )


def test_disabled_alpha_test_needs_no_shader_patch():
    result = build_alpha_test_contract(None)
    assert result["ready"] is True
    assert result["enabled"] is False
    assert result["native_execution"]["ready"] is True
    assert result["d3d9_render_states"]["D3DRS_ALPHATESTENABLE"]["value"] == 0


def test_fractional_bmt_alpha_reference_fails_closed():
    result = build_alpha_test_contract({
        "enabled": True,
        "function": _enum("ETF_GREATER_THAN_OR_EQUAL", 6),
        "value_raw": 64.5,
    })
    assert result["ready"] is False
    assert any(
        reason.startswith("alpha-test:fractional-reference-unproven:")
        for reason in result["blocking_reasons"]
    )


def test_unknown_alpha_function_fails_closed():
    result = build_alpha_test_contract({
        "enabled": True,
        "function": {
            "raw": "ETF_MAGIC",
            "engine_enum_index": None,
            "status": "unknown",
        },
        "value_raw": 64.0,
    })
    assert result["ready"] is False
    assert "alpha-test:function-unknown:ETF_MAGIC" in result["blocking_reasons"]
