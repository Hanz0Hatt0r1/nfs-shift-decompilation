import pytest

from material_constants import pack_material_constant_payload


def _binding(**overrides):
    result = {
        "name": "primerBasis",
        "type": "EPT_VEC4",
        "value": [1.0, 2.0, 3.0, 4.0],
        "register_set": 2,
        "register_index": 5,
        "register_count": 1,
        "ctab_type": "float4",
        "binding": "material-constant",
    }
    result.update(overrides)
    return result


def test_material_constant_payload_packs_float4_register():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [_binding()],
    })
    assert result["format"] == "SHIFT.MaterialConstantPayload/1"
    assert result["ready"] is True
    assert result["ubo_binding"] == 14
    assert result["registers"] == [{
        "register_index": 5,
        "values": [1.0, 2.0, 3.0, 4.0],
        "byte_offset": 80,
        "byte_size": 16,
    }]


def test_material_constant_payload_pads_short_vectors():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [_binding(
            name="roughness",
            type="EPT_F32",
            value=[0.25],
            ctab_type="float",
        )],
    })
    assert result["ready"] is True
    assert result["registers"][0]["values"] == [0.25, 0.0, 0.0, 0.0]


def test_material_constant_payload_rejects_register_conflict():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [
            _binding(name="A", value=[1, 2, 3, 4], register_index=5),
            _binding(name="B", value=[4, 3, 2, 1], register_index=5),
        ],
    })
    assert result["ready"] is False
    assert "uniform-payload:register-conflict:5" in result["blocking_reasons"]


def test_material_constant_payload_rejects_matrix_orientation_until_proven():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [_binding(
            name="world",
            type="EPT_MATRIX",
            value=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
            ctab_type="float4x4",
            register_count=4,
        )],
    })
    assert result["ready"] is False
    assert any("unsupported-ctab-type:float4x4" in x for x in result["blocking_reasons"])


def test_material_constant_payload_rejects_non_float_register_set():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [_binding(register_set=3)],
    })
    assert result["ready"] is False
    assert "uniform-payload:unexpected-register-set:primerBasis" in result["blocking_reasons"]


def test_material_constant_payload_rejects_value_overflow():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [_binding(value=list(range(9)), register_count=2)],
    })
    assert result["ready"] is False
    assert "uniform-payload:value-exceeds-register-range:primerBasis" in result["blocking_reasons"]
