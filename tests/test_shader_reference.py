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


def test_material_constant_payload_rejects_bad_byte_range():
    from shader_reference import material_constants_from_payload

    result = material_constants_from_payload({
        "format": "SHIFT.MaterialConstantPayload/1",
        "ready": True,
        "registers": [{
            "register_index": 3,
            "values": [0.25, 0.5, 0.75, 1.0],
            "byte_offset": 16,
            "byte_size": 16,
        }],
    })
    assert result["status"] == "unsupported"
    assert "uniform-payload:byte-range-invalid:3" in result["blocking_reasons"]


def _vertex_program(instructions, *, temps=(0,)):
    return ShaderProgram(
        offset=0,
        end=0,
        stage="vertex",
        major=3,
        minor=0,
        instructions=list(instructions),
        inputs=[{"usage": "POSITION", "index": 0, "register": "v0"}],
        outputs=[],
        samplers=[],
        constants=[],
        temps=list(temps),
        unsupported_opcodes=[],
    )

def _relative_const(index, address_token):
    return Operand(
        token=0x80000000 | (2 << 28) | (index & 0x7FF) | (0xE4 << 16) | (1 << 13),
        kind="source",
        reg_type=2,
        index=index,
        swizzle="xyzw",
        source_modifier=0,
        relative=True,
        relative_token=address_token,
    )

def test_reference_shader_executes_a0_relative_constant_read():
    address_token = 0x80000000 | (3 << 28)
    mova = Instruction(0, 46, "MOVA", 0, 3, 0, False, [_dst(3, 0, mask="x"), _src(1, 0)])
    mov = Instruction(4, 1, "MOV", 0, 3, 0, False, [_dst(0, 0), _relative_const(2, address_token)])
    out = Instruction(8, 1, "MOV", 0, 3, 0, False, [_dst(6, 0), _src(0, 0)])
    result = execute_shader(
        _vertex_program([mova, mov, out]),
        inputs={0: (2.0, 0.0, 0.0, 0.0)},
        constants={"c": {4: (4.0, 3.0, 2.0, 1.0)}},
    )
    assert result["status"] == "executed"
    assert result["color"] == [4.0, 3.0, 2.0, 1.0]

def test_reference_shader_returns_zero_for_out_of_range_relative_constant():
    address_token = 0x80000000 | (3 << 28)
    mova = Instruction(0, 46, "MOVA", 0, 3, 0, False, [_dst(3, 0, mask="x"), _src(1, 0)])
    mov = Instruction(4, 1, "MOV", 0, 3, 0, False, [_dst(0, 0), _relative_const(2, address_token)])
    out = Instruction(8, 1, "MOV", 0, 3, 0, False, [_dst(6, 0), _src(0, 0)])
    result = execute_shader(
        _vertex_program([mova, mov, out]),
        inputs={0: (10.0, 0.0, 0.0, 0.0)},
        constants={"c": {4: (4.0, 3.0, 2.0, 1.0)}},
    )
    assert result["status"] == "executed"
    assert result["color"] == [0.0, 0.0, 0.0, 0.0]

def test_reference_shader_blocks_relative_constant_on_pixel_stage():
    address_token = 0x80000000 | (3 << 28)
    mov = Instruction(0, 1, "MOV", 0, 3, 0, False, [_dst(8, 0), _relative_const(0, address_token)])
    result = execute_shader(_program([mov], temps=()), constants={"c": {0: (1.0, 0.0, 0.0, 1.0)}})
    assert result["status"] == "error"
    assert "relative constant addressing requires vertex shader stage" in result["blocking_reasons"][0]

def test_reference_shader_does_not_guess_address_rounding_ties():
    mova = Instruction(0, 46, "MOVA", 0, 3, 0, False, [_dst(3, 0, mask="x"), _src(1, 0)])
    result = execute_shader(_vertex_program([mova]), inputs={0: (1.5, 0.0, 0.0, 0.0)})
    assert result["status"] == "error"
    assert "address register rounding tie is not proven" in result["blocking_reasons"][0]


def test_reference_shader_only_rounds_written_address_components():
    mova = Instruction(0, 46, "MOVA", 0, 3, 0, False, [
        _dst(3, 0, mask="x"),
        _src(1, 0),
    ])
    result = execute_shader(
        _vertex_program([mova]),
        inputs={0: (1.0, 1.5, 0.0, 0.0)},
    )
    assert result["status"] == "executed"


def _vertex_passthrough_program():
    return ShaderProgram(
        offset=0,
        end=0,
        stage="vertex",
        major=3,
        minor=0,
        instructions=[
            Instruction(
                0, 1, "MOV", 0, 3, 0, False,
                [
                    _dst(4, 0),
                    _src(1, 0),
                ],
            ),
            Instruction(
                12, 1, "MOV", 0, 3, 0, False,
                [
                    _dst(6, 1),
                    _src(1, 1),
                ],
            ),
        ],
        inputs=[
            {"usage": "POSITION", "index": 0, "register": "v0"},
            {"usage": "TEXCOORD", "index": 0, "register": "v1"},
        ],
        outputs=[
            {"usage": "POSITION", "index": 0, "register": "oR0"},
            {"usage": "TEXCOORD", "index": 0, "register": "oT1"},
        ],
        samplers=[],
        constants=[],
        temps=[],
        unsupported_opcodes=[],
    )


def test_reference_shader_returns_all_outputs_for_vertex_stage():
    program = _vertex_passthrough_program()
    result = execute_shader(
        program,
        inputs={
            0: (1.0, 0.5, -0.25, 1.0),
            1: (0.25, 0.75, 0.0, 1.0),
        },
    )
    assert result["status"] == "executed"
    assert result["outputs"]["0"] == [1.0, 0.5, -0.25, 1.0]
    assert result["outputs"]["1"] == [0.25, 0.75, 0.0, 1.0]


def test_validate_vertex_program_input_contract_rejects_unknown_semantic():
    from shader_reference import validate_vertex_program_inputs

    program = _vertex_passthrough_program()
    program.inputs = [{"usage": "COLOR", "index": 0, "register": "v1"}]
    result = validate_vertex_program_inputs(program)
    assert result["valid"] is False
    assert "vertex-input:unsupported:COLOR:0" in result["blocking_reasons"]


def test_validate_vertex_program_accepts_proven_skin_inputs():
    from shader_reference import validate_vertex_program_inputs

    program = _vertex_passthrough_program()
    program.inputs.extend([
        {"usage": "BLENDWEIGHT", "index": 0, "register": "v2"},
        {"usage": "BLENDINDICES", "index": 0, "register": "v3"},
    ])
    result = validate_vertex_program_inputs(program)
    assert result["valid"] is True


def _sampler2d_pixel_program(sampler_type="sampler2D"):
    return ShaderProgram(
        offset=0,
        end=0,
        stage="pixel",
        major=3,
        minor=0,
        instructions=[
            Instruction(
                0, 66, "TEX", 0, 4, 0, False,
                [
                    _dst(8, 0),
                    _src(1, 0),
                    Operand(
                        token=0x80000000,
                        kind="source",
                        reg_type=10,
                        index=0,
                        swizzle="xyzw",
                        source_modifier=0,
                    ),
                ],
            ),
        ],
        inputs=[{"usage": "TEXCOORD", "index": 0, "register": "v0"}],
        outputs=[{"usage": "COLOR", "index": 0, "register": "oC0"}],
        samplers=[0],
        constants=[],
        temps=[],
        unsupported_opcodes=[],
        sampler_types={0: sampler_type},
    )


def test_reference_shader_executes_external_sampler2d_image():
    program = _sampler2d_pixel_program("sampler2D")
    result = execute_shader(
        program,
        inputs={0: (0.0, 0.0, 0.0, 1.0)},
        textures={0: {
            "format": "SHIFT.ReferenceTexture/1",
            "source_format": "RGBA32",
            "width": 1,
            "height": 1,
            "pixels": bytes((70, 80, 90, 255)),
        }},
    )
    assert result["status"] == "executed"
    assert result["color"] == [70 / 255.0, 80 / 255.0, 90 / 255.0, 1.0]


def test_reference_shader_rejects_cube_sampler_resource_without_cube_implementation():
    program = _sampler2d_pixel_program("samplerCube")
    result = execute_shader(
        program,
        inputs={0: (0.0, 0.0, 0.0, 1.0)},
        textures={0: {
            "format": "SHIFT.ReferenceTexture/1",
            "source_format": "RGBA32",
            "width": 1,
            "height": 1,
            "pixels": bytes((70, 80, 90, 255)),
        }},
    )
    assert result["status"] == "error"
    assert "reference resource type samplerCube for s0 is not implemented" in result["blocking_reasons"][0]


def test_reference_shader_reports_missing_external_sampler_image():
    program = _sampler2d_pixel_program("sampler2D")
    result = execute_shader(
        program,
        inputs={0: (0.0, 0.0, 0.0, 1.0)},
    )
    assert result["status"] == "error"
    assert "texture sampler s0 (sampler2D) has no reference image" in result["blocking_reasons"][0]


def test_reference_shader_executes_sampler_cube_resource():
    from texture_reference import sample_texture_cube

    program = _sampler2d_pixel_program("samplerCube")
    program.sampler_types = {0: "samplerCube"}
    cube = {
        "format": "SHIFT.ReferenceCubeTexture/1",
        "faces": {
            face: {
                "format": "SHIFT.ReferenceTexture/1",
                "width": 1,
                "height": 1,
                "pixels": bytes(rgba),
            }
            for face, rgba in {
                "px": (255, 0, 0, 255),
                "nx": (0, 255, 0, 255),
                "py": (0, 0, 255, 255),
                "ny": (255, 255, 0, 255),
                "pz": (255, 0, 255, 255),
                "nz": (0, 255, 255, 255),
            }.items()
        },
    }
    assert sample_texture_cube(cube, 0.0, 0.0, 1.0) == pytest.approx((1.0, 0.0, 1.0, 1.0))
    result = execute_shader(
        program,
        inputs={0: (0.0, 0.0, 1.0, 1.0)},
        textures={0: cube},
    )
    assert result["status"] == "executed"
    assert result["color"] == [1.0, 0.0, 1.0, 1.0]
