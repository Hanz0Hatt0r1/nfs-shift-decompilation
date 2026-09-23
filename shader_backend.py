from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path

from shader_asm import ShaderProgram, parse_program, to_glsl
from shader_interface import build_varying_locations


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



def translate_pair(
    vertex: ShaderProgram,
    pixel: ShaderProgram,
    *,
    vertex_properties: list[str | dict] | tuple[str | dict, ...] = (),
) -> dict:
    """Translate a matched D3D9 VS/PS pair into a shared GLSL interface."""
    from shader_interface import build_vertex_input_locations

    linkage = build_varying_locations(vertex, pixel)
    if not linkage["valid"]:
        raise ValueError("cannot translate unmatched VS/PS pair to a linked GLSL interface")

    input_linkage = (
        build_vertex_input_locations(vertex, vertex_properties)
        if vertex_properties
        else {"valid": True, "input_locations": {}, "bindings": [], "unresolved": [], "score": 1.0}
    )
    if not input_linkage["valid"]:
        raise ValueError("cannot translate VS: one or more vertex inputs lack a target VertexLayout location")

    return {
        "format": "SHIFT.LinkedShaderPair/1",
        "vertex": program_to_ir(vertex),
        "pixel": program_to_ir(pixel),
        "interface": linkage["link"],
        "varying_locations": linkage["semantic_locations"],
        "vertex_input_bindings": input_linkage["bindings"],
        "vertex_input_locations": input_linkage["input_locations"],
        "vertex_glsl": to_glsl(
            vertex,
            input_locations=input_linkage["input_locations"],
            output_locations=linkage["vertex_output_locations"],
        ),
        "pixel_glsl": to_glsl(pixel, input_locations=linkage["pixel_input_locations"]),
    }


def translate_pair_blob(
    data: bytes,
    vertex_offset: int,
    pixel_offset: int,
    *,
    vertex_properties: list[str | dict] | tuple[str | dict, ...] = (),
) -> dict:
    """Parse and translate one VS/PS pair from a single FXO shader blob."""
    blobs = parse_shader_blobs(data)
    vertex_blob = next((b for b in blobs if b.offset == vertex_offset and b.stage == "vertex"), None)
    pixel_blob = next((b for b in blobs if b.offset == pixel_offset and b.stage == "pixel"), None)
    if vertex_blob is None or pixel_blob is None:
        raise ValueError("requested shader pair offsets are not present")
    vertex = parse_program(data, vertex_blob.offset, vertex_blob.end, vertex_blob.stage, vertex_blob.major, vertex_blob.minor)
    pixel = parse_program(data, pixel_blob.offset, pixel_blob.end, pixel_blob.stage, pixel_blob.major, pixel_blob.minor)
    return translate_pair(vertex, pixel, vertex_properties=vertex_properties)

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
