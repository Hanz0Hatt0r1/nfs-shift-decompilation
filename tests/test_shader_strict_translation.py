import pytest

from shader_asm import Instruction, Operand, ShaderProgram, parse_program, to_glsl


def _program(*, instruction: Instruction, stage: str = "pixel", unsupported=None):
    return ShaderProgram(
        offset=0,
        end=0,
        stage=stage,
        major=3,
        minor=0,
        instructions=[instruction],
        inputs=[],
        outputs=[],
        samplers=[],
        constants=[],
        temps=[0, 1],
        unsupported_opcodes=list(unsupported or []),
    )


def _dest(reg_type: int = 0, index: int = 0):
    return Operand(
        token=0x80000000,
        kind="dest",
        reg_type=reg_type,
        index=index,
        write_mask="xyzw",
    )


def _src(index: int = 1):
    return Operand(
        token=0x80000000,
        kind="source",
        reg_type=0,
        index=index,
        swizzle="xyzw",
    )


def test_strict_translation_rejects_unknown_parser_opcode():
    program = _program(
        instruction=Instruction(0, 123, "OP_123", 0, 0, 0, False, []),
        unsupported=[123],
    )
    with pytest.raises(ValueError, match="unsupported opcode values: 123"):
        to_glsl(program)


def test_strict_translation_rejects_known_but_unimplemented_opcode():
    program = _program(
        instruction=Instruction(
            0, 67, "TEXBEM", 0, 2, 0, False, [_dest(), _src()]
        )
    )
    with pytest.raises(NotImplementedError, match="unsupported TEXBEM opcode=67"):
        to_glsl(program)


def test_non_strict_translation_is_explicit_audit_mode():
    program = _program(
        instruction=Instruction(
            0, 67, "TEXBEM", 0, 2, 0, False, [_dest(), _src()]
        )
    )
    glsl = to_glsl(program, strict=False)
    assert "/* unsupported TEXBEM opcode=67 */" in glsl


def test_pixel_mrt_outputs_are_declared_from_written_color_registers():
    program = _program(
        instruction=Instruction(
            0, 1, "MOV", 0, 2, 0, False, [_dest(reg_type=8, index=2), _src()]
        )
    )
    glsl = to_glsl(program)
    assert "layout(location=2) out vec4 fragColor2;" in glsl
    assert "layout(location=0) out vec4 fragColor0;" not in glsl


def test_vertex_generic_output_without_dcl_fails_closed():
    program = _program(
        stage="vertex",
        instruction=Instruction(
            0, 1, "MOV", 0, 2, 0, False, [_dest(reg_type=6, index=0), _src()]
        ),
    )
    with pytest.raises(ValueError, match="undeclared generic outputs"):
        to_glsl(program)


def test_parser_uses_def_81_and_texkill_65():
    # ps_3_0; DEF c0, 1,2,3,4; TEXKILL r0; END
    import struct

    def _f(value: float) -> int:
        return struct.unpack("<I", struct.pack("<f", value))[0]

    dst_c0 = 0x80000000 | (2 << 28) | (0xF << 16)
    kill_r0 = 0x80000000 | (0xF << 16)
    words = [
        0xFFFF0300,
        (5 << 24) | 81,
        dst_c0,
        _f(1.0), _f(2.0), _f(3.0), _f(4.0),
        (1 << 24) | 65,
        kill_r0,
        0xFFFF,
    ]
    program = parse_program(struct.pack("<" + "I" * len(words), *words))
    assert [ins.name for ins in program.instructions] == ["DEF", "TEXKILL"]
    assert program.constants == [0]
