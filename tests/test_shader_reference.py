import struct

from shader_asm import Instruction, Operand, ShaderProgram
from shader_reference import execute_shader, material_constants_from_uniform_binding


def _program(instructions, *, temps=(0, 1, 2)):
    return ShaderProgram(
        offset=0,
        end=0,
        stage="pixel",
        major=3,
        minor=0,
        instructions=list(instructions),
        inputs=[{"usage": "TEXCOORD", "index": 0, "register": "v0"}],
        outputs=[{"usage": "COLOR", "index": 0, "register": "oC0"}],
        samplers=[0],
        constants=[0],
        temps=list(temps),
        unsupported_opcodes=[],
    )


def _src(reg_type, index, *, swizzle="xyzw", source_modifier=0):
    return Operand(
        token=0x80000000,
        kind="source",
        reg_type=reg_type,
        index=index,
        swizzle=swizzle,
        source_modifier=source_modifier,
    )


def _dst(reg_type, index, *, mask="xyzw"):
    return Operand(
        token=0x80000000,
        kind="dest",
        reg_type=reg_type,
        index=index,
        write_mask=mask,
    )


def test_reference_shader_executes_arithmetic_and_constants():
    mov = Instruction(
        0, 1, "MOV", 0, 3, 0, False,
        [_dst(0, 0), _src(2, 0)],
    )
    mul = Instruction(
        4, 5, "MUL", 0, 4, 0, False,
        [_dst(8, 0), _src(0, 0), _src(2, 0)],
    )
    result = execute_shader(
        _program([mov, mul], temps=(0,)),
        constants={"c": {0: (0.25, 0.5, 0.75, 1.0)}},
    )
    assert result["status"] == "executed"
    assert result["color"] == [0.0625, 0.25, 0.5625, 1.0]


def test_reference_shader_applies_source_modifier_and_write_mask():
    mov = Instruction(
        0, 1, "MOV", 0, 3, 0, False,
        [_dst(0, 0, mask="xy"), _src(1, 0, swizzle="yx", source_modifier=1)],
    )
    out = Instruction(
        4, 1, "MOV", 0, 3, 0, False,
        [_dst(8, 0), _src(0, 0)],
    )
    result = execute_shader(
        _program([mov, out], temps=(0,)),
        inputs={0: (0.2, 0.7, 0.0, 1.0)},
    )
    assert result["status"] == "executed"
    assert result["color"] == [-0.7, -0.2, 0.0, 0.0]


def test_reference_shader_executes_tex_against_reference_image():
    tex = {
        "width": 1,
        "height": 1,
        "pixels": bytes((64, 128, 255, 255)),
    }
    instr = Instruction(
        0, 66, "TEX", 0, 4, 0, False,
        [_dst(8, 0), _src(1, 0), _src(10, 0)],
    )
    result = execute_shader(
        _program([instr], temps=()),
        inputs={0: (0.25, 0.75, 0.0, 1.0)},
        textures={0: tex},
        samplers={0: {
            "min_filter": "POINT",
            "mag_filter": "POINT",
            "address_u": "CLAMP_TO_EDGE",
            "address_v": "CLAMP_TO_EDGE",
        }},
    )
    assert result["status"] == "executed"
    assert result["color"] == [64 / 255, 128 / 255, 1.0, 1.0]


def test_reference_shader_reports_unsupported_control_flow():
    instr = Instruction(
        0, 40, "IF", 0, 2, 0, False,
        [_src(0, 0)],
    )
    result = execute_shader(_program([instr], temps=(0,)))
    assert result["status"] == "unsupported"
    assert "shader-opcode:unsupported:IF:40" in result["blocking_reasons"]


def test_reference_shader_error_is_explicit_for_missing_texture():
    instr = Instruction(
        0, 66, "TEX", 0, 4, 0, False,
        [_dst(8, 0), _src(1, 0), _src(10, 0)],
    )
    result = execute_shader(
        _program([instr], temps=()),
        inputs={0: (0.0, 0.0, 0.0, 1.0)},
    )
    assert result["status"] == "error"
    assert "texture sampler s0 has no reference image" in result["blocking_reasons"][0]


def test_material_uniform_binding_builds_reference_constant_bank():
    result = material_constants_from_uniform_binding({
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
    assert result["status"] == "ready"
    assert result["banks"]["c"][3] == [0.25, 0.5, 0.75, 1.0]


def test_material_uniform_binding_builds_matrix_rows():
    result = material_constants_from_uniform_binding({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [{
            "name": "viewProj",
            "binding": "material-constant",
            "register_set": 2,
            "register_index": 4,
            "register_count": 4,
            "ctab_type": "float4x4",
            "value": list(range(16)),
        }],
    })
    assert result["status"] == "ready"
    assert result["banks"]["c"][4] == [0.0, 1.0, 2.0, 3.0]
    assert result["banks"]["c"][7] == [12.0, 13.0, 14.0, 15.0]


def test_material_uniform_binding_rejects_unsupported_type():
    result = material_constants_from_uniform_binding({
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [{
            "name": "flag",
            "binding": "material-constant",
            "register_set": 2,
            "register_index": 1,
            "register_count": 1,
            "ctab_type": "int",
            "value": 1,
        }],
    })
    assert result["status"] == "unsupported"
    assert "uniform-binding:unsupported-ctab-type:int" in result["blocking_reasons"]


def test_material_constant_payload_builds_reference_bank():
    from shader_reference import material_constants_from_payload

    result = material_constants_from_payload({
        "format": "SHIFT.MaterialConstantPayload/1",
        "ready": True,
        "blocking_reasons": [],
        "register_count": 1,
        "registers": [{
            "register_index": 3,
            "values": [0.25, 0.5, 0.75, 1.0],
            "byte_offset": 48,
            "byte_size": 16,
        }],
    })
    assert result["status"] == "ready"
    assert result["banks"]["c"][3] == [0.25, 0.5, 0.75, 1.0]


def test_material_constant_payload_rejects_malformed_register():
    from shader_reference import material_constants_from_payload

    result = material_constants_from_payload({
        "format": "SHIFT.MaterialConstantPayload/1",
        "ready": True,
        "registers": [{
            "register_index": 3,
            "values": [1.0, 2.0],
            "byte_offset": 48,
            "byte_size": 16,
        }],
    })
    assert result["status"] == "unsupported"
    assert "uniform-payload:register-width-invalid:3" in result["blocking_reasons"]
