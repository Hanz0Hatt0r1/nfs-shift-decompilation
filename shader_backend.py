from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path

from shader_asm import ShaderProgram, parse_program


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
    }


def _src(o, stage: str) -> str:
    names = {0:"r", 1:"in_", 2:"c", 3:"a", 6:"out_", 8:"fragColor",
             9:"gl_FragDepth", 10:"tex", 11:"c", 12:"c", 13:"c",
             16:"h", 17:"misc", 19:"predicate"}
    rt, idx = o.reg_type, o.index or 0
    if rt == 2 or rt in (11, 12, 13):
        base = f"c[{idx}]"
    elif rt == 0:
        base = f"r{idx}"
    elif rt == 1:
        base = f"in_{idx}"
    elif rt == 10:
        base = f"tex{idx}"
    else:
        base = f"{names.get(rt, 'reg_'+str(rt))}{idx}"
    if o.kind == "source":
        sw = o.swizzle or "xyzw"
        if sw != "xyzw":
            base += "." + sw
        m = o.source_modifier or 0
        if m == 1: base = "-(" + base + ")"
        elif m == 6: base = "(1.0-" + base + ")"
        elif m == 7: base = "(" + base + "*2.0)"
        elif m == 8: base = "(-" + base + "*2.0)"
        elif m == 11: base = "abs(" + base + ")"
        elif m == 12: base = "-abs(" + base + ")"
    return base


def _dst(o, expr: str, stage: str) -> str:
    lhs = _src(o, stage)
    if o.write_mask and o.write_mask != "xyzw":
        lhs += "." + o.write_mask
    return f"{lhs} = {expr};"


def to_glsl(program: ShaderProgram) -> str:
    """Lower the common SHIFT D3D9 subset to GLES 3.1 GLSL.

    This is deliberately a transparent backend: unsupported instructions are
    emitted as comments instead of silently being discarded.
    """
    lines = ["#version 310 es", "precision highp float;", "precision highp int;"]
    for i in program.temps:
        lines.append(f"vec4 r{i}=vec4(0.0);")
    maxc = max(program.constants + [0])
    lines.append(f"vec4 c[{max(1, maxc + 1)}];")
    for s in program.samplers:
        lines.append(f"layout(binding={s}) uniform sampler2D tex{s};")
    for d in program.inputs:
        reg = str(d.get("register", "v0"))
        try: loc = int(reg.split("v", 1)[1].split(".", 1)[0])
        except Exception: loc = 0
        lines.append(f"layout(location={loc}) in vec4 in_{loc};")
    if program.stage == "vertex":
        for d in program.outputs:
            lines.append(f"layout(location={d.get('index', 0)}) out vec4 out_{d.get('index', 0)};")
    else:
        lines.append("layout(location=0) out vec4 fragColor0;")
    lines.append("void main(){")

    for ins in program.instructions:
        o, n = ins.operands, ins.name
        try:
            if n == "DCL" or n in ("DEF", "DEFI", "DEFB"):
                continue
            if n == "MOV" and len(o) >= 2: lines.append("  " + _dst(o[0], _src(o[1], program.stage), program.stage))
            elif n == "ADD" and len(o) >= 3: lines.append("  " + _dst(o[0], f"({_src(o[1],program.stage)}+{_src(o[2],program.stage)})", program.stage))
            elif n == "SUB" and len(o) >= 3: lines.append("  " + _dst(o[0], f"({_src(o[1],program.stage)}-{_src(o[2],program.stage)})", program.stage))
            elif n == "MUL" and len(o) >= 3: lines.append("  " + _dst(o[0], f"({_src(o[1],program.stage)}*{_src(o[2],program.stage)})", program.stage))
            elif n == "MAD" and len(o) >= 4: lines.append("  " + _dst(o[0], f"({_src(o[1],program.stage)}*{_src(o[2],program.stage)}+{_src(o[3],program.stage)})", program.stage))
            elif n == "DP3" and len(o) >= 3: lines.append("  " + _dst(o[0], f"vec4(dot({_src(o[1],program.stage)}.xyz,{_src(o[2],program.stage)}.xyz))", program.stage))
            elif n == "DP4" and len(o) >= 3: lines.append("  " + _dst(o[0], f"vec4(dot({_src(o[1],program.stage)},{_src(o[2],program.stage)}))", program.stage))
            elif n == "MIN" and len(o) >= 3: lines.append("  " + _dst(o[0], f"min({_src(o[1],program.stage)},{_src(o[2],program.stage)})", program.stage))
            elif n == "MAX" and len(o) >= 3: lines.append("  " + _dst(o[0], f"max({_src(o[1],program.stage)},{_src(o[2],program.stage)})", program.stage))
            elif n == "SLT" and len(o) >= 3: lines.append("  " + _dst(o[0], f"mix(vec4(0.0),vec4(1.0),lessThan({_src(o[1],program.stage)},{_src(o[2],program.stage)}))", program.stage))
            elif n == "SGE" and len(o) >= 3: lines.append("  " + _dst(o[0], f"mix(vec4(0.0),vec4(1.0),greaterThanEqual({_src(o[1],program.stage)},{_src(o[2],program.stage)}))", program.stage))
            elif n == "RCP" and len(o) >= 2: lines.append("  " + _dst(o[0], f"(1.0/{_src(o[1],program.stage)})", program.stage))
            elif n == "RSQ" and len(o) >= 2: lines.append("  " + _dst(o[0], f"(1.0/sqrt(abs({_src(o[1],program.stage)})))", program.stage))
            elif n == "NRM" and len(o) >= 2: lines.append("  " + _dst(o[0], f"vec4(normalize({_src(o[1],program.stage)}.xyz),0.0)", program.stage))
            elif n == "FRC" and len(o) >= 2: lines.append("  " + _dst(o[0], f"fract({_src(o[1],program.stage)})", program.stage))
            elif n == "ABS" and len(o) >= 2: lines.append("  " + _dst(o[0], f"abs({_src(o[1],program.stage)})", program.stage))
            elif n == "POW" and len(o) >= 3: lines.append("  " + _dst(o[0], f"pow(abs({_src(o[1],program.stage)}),{_src(o[2],program.stage)})", program.stage))
            elif n == "LRP" and len(o) >= 4: lines.append("  " + _dst(o[0], f"mix({_src(o[3],program.stage)},{_src(o[2],program.stage)},{_src(o[1],program.stage)})", program.stage))
            elif n in ("CMP",) and len(o) >= 4: lines.append("  " + _dst(o[0], f"mix({_src(o[3],program.stage)},{_src(o[2],program.stage)},greaterThanEqual({_src(o[1],program.stage)},vec4(0.0)))", program.stage))
            elif n == "TEX" and len(o) >= 3: lines.append("  " + _dst(o[0], f"texture({_src(o[2],program.stage)},{_src(o[1],program.stage)}.xy)", program.stage))
            elif n == "TEXLDD" and len(o) >= 5: lines.append("  " + _dst(o[0], f"textureGrad({_src(o[2],program.stage)},{_src(o[1],program.stage)}.xy,{_src(o[3],program.stage)}.xy,{_src(o[4],program.stage)}.xy)", program.stage))
            elif n == "TEXLDL" and len(o) >= 3: lines.append("  " + _dst(o[0], f"textureLod({_src(o[2],program.stage)},{_src(o[1],program.stage)}.xy,{_src(o[1],program.stage)}.w)", program.stage))
            elif n == "DSX": lines.append("  " + _dst(o[0], f"dFdx({_src(o[1],program.stage)})", program.stage))
            elif n == "DSY": lines.append("  " + _dst(o[0], f"dFdy({_src(o[1],program.stage)})", program.stage))
            elif n == "ELSE": lines.append("  } else {")
            elif n == "ENDIF": lines.append("  }")
            elif n == "IFC" and len(o) >= 2: lines.append(f"  if (all(greaterThanEqual({_src(o[0],program.stage)},{_src(o[1],program.stage)}))) {{")
            elif n == "LOOP": lines.append("  for(int shift_loop=0;shift_loop<256;++shift_loop){")
            elif n == "ENDLOOP": lines.append("  }")
            elif n == "REP": lines.append("  for(int shift_rep=0;shift_rep<256;++shift_rep){")
            elif n == "ENDREP": lines.append("  }")
            else: lines.append(f"  /* unsupported {n} opcode={ins.opcode} */")
        except Exception as exc:
            lines.append(f"  /* translator error {n}: {exc} */")
    lines.append("}")
    return "\n".join(lines) + "\n"


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
