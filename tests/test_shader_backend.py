import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from shader_asm import parse_program
from shader_backend import program_to_ir, to_glsl


def _shader(stage: str) -> bytes:
    version = 0xFFFE0300 if stage == "vertex" else 0xFFFF0300
    words = [version]
    if stage == "vertex":
        # dcl_position0 v0; dcl_texcoord0 oT0; mov oT0, v0
        words += [
            (2 << 24) | 31, 0, 0x80000000 | 0 | (15 << 16) | (1 << 28),
            (2 << 24) | 31, 5, 0x80000000 | 0 | (15 << 16) | (6 << 28),
            (2 << 24) | 1, 0x80000000 | 0 | (15 << 16) | (6 << 28),
            0x80000000 | 0 | (0xE4 << 16) | (1 << 28),
        ]
    else:
        # dcl_texcoord0 v0; mov oC0, v0
        words += [
            (2 << 24) | 31, 5, 0x80000000 | 0 | (15 << 16) | (1 << 28),
            (2 << 24) | 1, 0x80000000 | 0 | (15 << 16) | (8 << 28),
            0x80000000 | 0 | (0xE4 << 16) | (1 << 28),
        ]
    words.append(0xFFFF)
    return struct.pack("<" + "I" * len(words), *words)


def test_shader_program_ir_schema():
    p = parse_program(_shader("vertex"))
    ir = program_to_ir(p)
    assert ir["schema"] == "SHIFT.ShaderProgram/1"
    assert ir["stage"] == "vertex"
    assert ir["instructions"]


@pytest.mark.parametrize("stage,validator_stage", [("vertex", "vert"), ("pixel", "frag")])
def test_backend_emits_compilable_gles31(stage, validator_stage, tmp_path):
    validator = shutil.which("glslangValidator")
    if validator is None:
        pytest.skip("glslangValidator is not installed")

    p = parse_program(_shader(stage))
    glsl = to_glsl(p)
    assert glsl.startswith("#version 310 es")
    assert "void main()" in glsl

    path = tmp_path / ("shader.vert" if stage == "vertex" else "shader.frag")
    path.write_text(glsl, encoding="utf-8")
    proc = subprocess.run(
        [validator, "-S", validator_stage, str(path)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_backend_reuses_canonical_glsl_lowering():
    import shader_asm
    assert to_glsl is shader_asm.to_glsl


def test_sampler_type_and_relative_addressing_are_preserved():
    # ps_3_0, dcl_cube s0, mov r0, c[a0.x+2]
    version = 0xFFFF0300
    dcl = (2 << 24) | 31
    cube = (3 << 27)
    sampler = 0x80000000 | ((10 & 7) << 28) | ((10 & 0x18) << 8) | (15 << 16)
    rel_const = 0x80000000 | (2 << 28) | 2 | (0xE4 << 16) | (1 << 13)
    rel_addr = 0x80000000 | (3 << 28) | (0 << 16)
    mov = (3 << 24) | 1
    dst = 0x80000000 | 0 | (15 << 16)
    end = 0xFFFF
    import struct
    data = struct.pack("<IIIIIIIIII", version, dcl, cube, sampler, mov, dst, rel_const, rel_addr, end, 0)
    p = parse_program(data[:-4])
    assert p.sampler_types[0] == "samplerCube"
    src = p.instructions[1].operands[1]
    assert src.relative is True
    assert src.relative_token == rel_addr
    glsl = to_glsl(p)
    assert "samplerCube tex0" in glsl
    assert "c[int(a0.x)+2]" in glsl
