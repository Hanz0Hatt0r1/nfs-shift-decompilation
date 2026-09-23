import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

from shader_ir import parse_shader_blobs
from shader_asm import parse_program
from shader_backend import program_to_ir, to_glsl

FIX = Path(__file__).parent / "fixtures" / "glass.fxo"


def test_shader_program_ir_schema():
    data = FIX.read_bytes()
    blob = parse_shader_blobs(data)[0]
    p = parse_program(data, blob.offset, blob.end, blob.stage, blob.major, blob.minor)
    ir = program_to_ir(p)
    assert ir["schema"] == "SHIFT.ShaderProgram/1"
    assert ir["stage"] in ("vertex", "pixel")
    assert ir["instructions"]


def test_backend_emits_gles31():
    data = FIX.read_bytes()
    blob = parse_shader_blobs(data)[0]
    p = parse_program(data, blob.offset, blob.end, blob.stage, blob.major, blob.minor)
    glsl = to_glsl(p)
    assert glsl.startswith("#version 310 es")
    assert "void main()" in glsl
    assert "unsupported" in glsl or "texture" in glsl
