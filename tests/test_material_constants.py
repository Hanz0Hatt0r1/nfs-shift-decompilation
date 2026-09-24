from material_constants import pack_material_constant_payload


def _binding(**overrides):
    value = overrides.pop("value", [1.0, 2.0, 3.0, 4.0])
    binding = {
        "name": "primerBasis",
        "binding": "material-constant",
        "register_set": 2,
        "register_index": 5,
        "register_count": 1,
        "ctab_type": "float4",
        "value": value,
    }
    binding.update(overrides)
    return binding


def test_material_constant_payload_packs_vec4_into_one_register():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [_binding()],
    })
    assert result["format"] == "SHIFT.MaterialConstantPayload/1"
    assert result["ready"] is True
    assert result["register_count"] == 1
    assert result["registers"] == [{
        "register_index": 5,
        "values": [1.0, 2.0, 3.0, 4.0],
        "byte_offset": 80,
        "byte_size": 16,
    }]
    assert result["ubo_binding"] == 14


def test_material_constant_payload_pads_vector_slot():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [_binding(ctab_type="float2", value=[0.25, 0.5])],
    })
    assert result["ready"] is True
    assert result["registers"][0]["values"] == [0.25, 0.5, 0.0, 0.0]
    assert result["bindings"][0]["component_width"] == 2


def test_material_constant_payload_packs_multiple_registers_deterministically():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [_binding(register_index=2, register_count=2, value=list(range(8)))],
    })
    assert result["ready"] is True
    assert [row["register_index"] for row in result["registers"]] == [2, 3]
    assert result["registers"][1]["byte_offset"] == 48


def test_material_constant_payload_blocks_matrix_orientation():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [_binding(
            name="world",
            register_index=4,
            register_count=4,
            ctab_type="float4x4",
            value=list(range(16)),
        )],
    })
    assert result["ready"] is False
    assert "uniform-payload:unsupported-ctab-type:world:float4x4" in result["blocking_reasons"]
    assert result["matrix_packing"] == "blocked-until-orientation-proven"


def test_material_constant_payload_blocks_non_material_register_set():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [_binding(register_set=3)],
    })
    assert result["ready"] is False
    assert "uniform-payload:unexpected-register-set:primerBasis" in result["blocking_reasons"]


def test_material_constant_payload_blocks_overflow():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [_binding(register_count=2, value=list(range(9)))],
    })
    assert result["ready"] is False
    assert "uniform-payload:value-exceeds-register-range:primerBasis" in result["blocking_reasons"]


def test_material_constant_payload_reports_conflicting_register_data():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [
            _binding(name="a", register_index=0, value=[1.0, 2.0, 3.0, 4.0]),
            _binding(name="b", register_index=0, value=[4.0, 3.0, 2.0, 1.0]),
        ],
    })
    assert result["ready"] is False
    assert "uniform-payload:register-conflict:0" in result["blocking_reasons"]


def test_material_constant_payload_rejects_invalid_format():
    result = pack_material_constant_payload({
        "format": "SHIFT.NotMaterialUniform/1",
        "bindings": [],
    })
    assert result["ready"] is False
    assert result["blocking_reasons"] == ["uniform-binding:invalid-format"]
