from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path

from shader_asm import ShaderProgram, parse_program, to_glsl


def program_to_ir(program: ShaderProgram) -> dict:
    """Serialize the parsed D3D9 program into the platform-neutral SHIFT IR."""
    return {
        "schema": "SHIFT.ShaderProgram/1",
        "stage": program.stage,
        "shader_model": [program.major, program.minor],
        "offset": program.offset,
        "end": program.end,
        "inputs": program.inputs,
        "outputs": program.outputs,
        "samplers": program.samplers,
        "constants": program.constants,
        "temps": program.temps,
        "unsupported_opcodes": program.unsupported_opcodes,
        "instructions": [asdict(i) for i in program.instructions],
        "const_ints": program.const_ints,
        "const_bools": program.const_bools,
        "sampler_types": program.sampler_types,
    }


def translate_blob(data: bytes, offset: int, end: int, stage: str, major: int, minor: int):
    program = parse_program(data, offset, end, stage, major, minor)
    return program_to_ir(program), to_glsl(program)


def write_translation(data: bytes, offset: int, end: int, stage: str, major: int, minor: int, out_dir: str | Path, stem: str):
    ir, glsl = translate_blob(data, offset, end, stage, major, minor)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / (stem + ".json")).write_text(json.dumps(ir, indent=2), encoding="utf-8")
    (out / (stem + ".glsl")).write_text(glsl, encoding="utf-8")
    return ir, glsl
