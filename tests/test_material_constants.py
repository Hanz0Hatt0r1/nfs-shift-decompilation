from material_constants import pack_material_constant_payload


def test_material_constant_payload_packs_float4_register():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [{
            "name": "tint",
            "binding": "material-constant",
            "register_set": 2,
            "register_index": 3,
            "register_count": 1,
            "ctab_type": "float4",
            "value": [0.25, 0.5, 0.75, 1.0],
        }],
    })
    assert result["format"] == "SHIFT.MaterialConstantPayload/1"
    assert result["ready"] is True
    assert result["registers"] == [{
        "register_index": 3,
        "values": [0.25, 0.5, 0.75, 1.0],
        "byte_offset": 48,
        "byte_size": 16,
    }]
    assert result["ubo_binding"] == 14


def test_material_constant_payload_pads_float3():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [{
            "name": "rgb",
            "binding": "material-constant",
            "register_set": 2,
            "register_index": 1,
            "register_count": 1,
            "ctab_type": "float3",
            "value": [1.0, 0.5, 0.25],
        }],
    })
    assert result["ready"] is True
    assert result["registers"][0]["values"] == [1.0, 0.5, 0.25, 0.0]


def test_material_constant_payload_supports_multi_register_vector_payload():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [{
            "name": "curve",
            "binding": "material-constant",
            "register_set": 2,
            "register_index": 4,
            "register_count": 2,
            "ctab_type": "float4",
            "value": list(range(8)),
        }],
    })
    assert result["ready"] is True
    assert [x["register_index"] for x in result["registers"]] == [4, 5]
    assert result["registers"][1]["byte_offset"] == 80


def test_material_constant_payload_blocks_float4x4():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [{
            "name": "world",
            "binding": "material-constant",
            "register_set": 2,
            "register_index": 4,
            "register_count": 4,
            "ctab_type": "float4x4",
            "value": list(range(16)),
        }],
    })
    assert result["ready"] is False
    assert "uniform-payload:unsupported-ctab-type:world:float4x4" in result["blocking_reasons"]


def test_material_constant_payload_blocks_overflow():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [{
            "name": "tooLarge",
            "binding": "material-constant",
            "register_set": 2,
            "register_index": 0,
            "register_count": 1,
            "ctab_type": "float4",
            "value": list(range(5)),
        }],
    })
    assert result["ready"] is False
    assert "uniform-payload:value-exceeds-register-range:tooLarge" in result["blocking_reasons"]


def test_material_constant_payload_detects_register_conflict():
    result = pack_material_constant_payload({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [
            {
                "name": "a",
                "binding": "material-constant",
                "register_set": 2,
                "register_index": 0,
                "register_count": 1,
                "ctab_type": "float4",
                "value": [1.0, 2.0, 3.0, 4.0],
            },
            {
                "name": "b",
                "binding": "material-constant",
                "register_set": 2,
                "register_index": 0,
                "register_count": 1,
                "ctab_type": "float4",
                "value": [4.0, 3.0, 2.0, 1.0],
            },
        ],
    })
    assert result["ready"] is False
    assert "uniform-payload:register-conflict:0" in result["blocking_reasons"]
