"""Deterministic software execution oracle for a strict subset of SHIFT D3D9 shader IR.

This module executes the parsed ShaderProgram representation directly. It does not
interpret arbitrary GLSL text and never substitutes unsupported opcodes with a
guess. Unsupported control flow/opcodes are reported explicitly.
"""
from __future__ import annotations

import math
from typing import Any, Iterable

from shader_asm import Instruction, Operand, ShaderProgram


FORMAT = "SHIFT.ReferenceShaderExecution/1"
_VECTOR = (0.0, 0.0, 0.0, 0.0)

_SUPPORTED = {
    "MOV", "ADD", "SUB", "MUL", "MAD", "DP3", "DP4", "MIN", "MAX",
    "SLT", "SGE", "EXP", "EXPP", "LOG", "LOGP", "LIT", "DST", "LRP",
    "FRC", "RCP", "RSQ", "NRM", "ABS", "POW", "CRS", "SINCOS", "CMP",
    "DP2ADD", "TEX", "TEXLDD", "TEXLDL",
}


def _vec(value: Iterable[float] | float | None) -> list[float]:
    if value is None:
        return [0.0, 0.0, 0.0, 0.0]
    if isinstance(value, (int, float)):
        return [float(value)] * 4
    row = [float(x) for x in value]
    if not row:
        return [0.0, 0.0, 0.0, 0.0]
    if len(row) == 1:
        return row * 4
    return (row + [row[-1]] * 4)[:4]


def _swizzle(value: list[float], swizzle: str | None) -> list[float]:
    sw = swizzle or "xyzw"
    indices = {"x": 0, "r": 0, "y": 1, "g": 1, "z": 2, "b": 2, "w": 3, "a": 3}
    return [value[indices[c]] for c in sw]


def _source_modifier(value: list[float], modifier: int | None) -> list[float]:
    m = int(modifier or 0)
    if m == 0:
        return value
    if m == 1:
        return [-x for x in value]
    if m == 2:
        return [x - 0.5 for x in value]
    if m == 3:
        return [0.5 - x for x in value]
    if m == 4:
        return [2.0 * x - 1.0 for x in value]
    if m == 5:
        return [1.0 - 2.0 * x for x in value]
    if m == 6:
        return [1.0 - x for x in value]
    if m == 7:
        return [2.0 * x for x in value]
    if m == 8:
        return [-2.0 * x for x in value]
    if m == 11:
        return [abs(x) for x in value]
    if m == 12:
        return [-abs(x) for x in value]
    if m == 13:
        return [1.0 if x == 0.0 else 0.0 for x in value]
    raise ValueError(f"unsupported source modifier {m}")


def _write_mask(old: list[float], value: list[float], mask: str | None) -> list[float]:
    out = list(old)
    indices = {"x": 0, "r": 0, "y": 1, "g": 1, "z": 2, "b": 2, "w": 3, "a": 3}
    for index, channel in enumerate(mask or "xyzw"):
        out[indices[channel]] = value[index]
    return out


def _component(a: list[float], op, b: list[float] | None = None) -> list[float]:
    return [
        float(op(x, y)) if b is not None else float(op(x))
        for x, y in zip(a, b or [0.0] * 4)
    ]


class ReferenceShaderState:
    def __init__(
        self,
        program: ShaderProgram,
        *,
        inputs: dict[int, Iterable[float]] | None = None,
        constants: dict[str, dict[int, Iterable[float]]] | None = None,
        textures: dict[int, dict[str, Any]] | None = None,
        samplers: dict[int, dict[str, Any]] | None = None,
    ) -> None:
        self.program = program
        self.inputs = {int(k): _vec(v) for k, v in (inputs or {}).items()}
        self.constants = {
            str(bank): {int(k): _vec(v) for k, v in rows.items()}
            for bank, rows in (constants or {}).items()
        }
        self.textures = {int(k): v for k, v in (textures or {}).items()}
        self.samplers = {int(k): dict(v) for k, v in (samplers or {}).items()}
        self.temps = {int(i): [0.0, 0.0, 0.0, 0.0] for i in program.temps}
        self.outputs: dict[int, list[float]] = {}
        self.depth: float | None = None

    def _read(self, operand: Operand) -> list[float]:
        if operand.reg_type is None:
            return _vec(operand.value if isinstance(operand.value, (int, float)) else None)

        rt = operand.reg_type
        idx = int(operand.index or 0)
        if operand.relative:
            raise ValueError("dynamic relative register addressing is not yet supported by reference executor")

        if rt == 0:
            value = self.temps.setdefault(idx, [0.0] * 4)
        elif rt == 1:
            value = self.inputs.get(idx, [0.0] * 4)
        elif rt in (2, 11, 12, 13):
            bank = {2: "c", 11: "c2", 12: "c3", 13: "c4"}[rt]
            value = self.constants.get(bank, {}).get(idx, [0.0] * 4)
        else:
            raise ValueError(f"unsupported source register type {rt}")
        value = _swizzle(list(value), operand.swizzle)
        return _source_modifier(value, operand.source_modifier)

    def _write(self, operand: Operand, value: Iterable[float]) -> None:
        row = _vec(value)
        if operand.result_modifier not in (None, 0, 1):
            raise ValueError(f"unsupported result modifier {operand.result_modifier}")
        if operand.result_modifier == 1:
            row = [max(0.0, min(1.0, x)) for x in row]

        rt = operand.reg_type
        idx = int(operand.index or 0)
        if rt == 0:
            self.temps[idx] = _write_mask(self.temps.get(idx, [0.0] * 4), row, operand.write_mask)
        elif rt == 8:
            self.outputs[idx] = _write_mask(self.outputs.get(idx, [0.0, 0.0, 0.0, 1.0]), row, operand.write_mask)
        elif rt == 9:
            self.depth = row[0]
        elif rt in (4, 5, 6):
            self.outputs[idx] = _write_mask(self.outputs.get(idx, [0.0] * 4), row, operand.write_mask)
        else:
            raise ValueError(f"unsupported destination register type {rt}")

    def _texture(self, sampler: Operand, coord: list[float]) -> list[float]:
        from texture_reference import sample_texture_2d

        idx = int(sampler.index or 0)
        image = self.textures.get(idx)
        if image is None:
            raise ValueError(f"texture sampler s{idx} has no reference image")
        return list(sample_texture_2d(image, coord[0], coord[1], self.samplers.get(idx, {})))

    def execute(self) -> dict[str, Any]:
        unsupported = [
            {"opcode": ins.opcode, "name": ins.name, "offset": ins.offset}
            for ins in self.program.instructions
            if ins.name not in _SUPPORTED and ins.name not in {
                "NOP", "DCL", "DEF", "DEFI", "DEFB", "LABEL", "COMMENT", "PHASE"
            }
        ]
        if unsupported:
            return {
                "format": FORMAT,
                "status": "unsupported",
                "stage": self.program.stage,
                "blocking_reasons": [
                    f"shader-opcode:unsupported:{item['name']}:{item['opcode']}"
                    for item in unsupported
                ],
                "unsupported": unsupported,
                "color": None,
            }

        try:
            for ins in self.program.instructions:
                name = ins.name
                o = ins.operands
                if name in {"NOP", "DCL", "DEF", "DEFI", "DEFB", "LABEL", "COMMENT", "PHASE"}:
                    continue
                if ins.predicate is not None:
                    raise ValueError("predicated shader instructions are not yet supported")

                if name == "MOV":
                    self._write(o[0], self._read(o[1]))
                elif name == "ADD":
                    self._write(o[0], _component(self._read(o[1]), lambda a, b: a + b, self._read(o[2])))
                elif name == "SUB":
                    self._write(o[0], _component(self._read(o[1]), lambda a, b: a - b, self._read(o[2])))
                elif name == "MUL":
                    self._write(o[0], _component(self._read(o[1]), lambda a, b: a * b, self._read(o[2])))
                elif name == "MAD":
                    a, b, c = self._read(o[1]), self._read(o[2]), self._read(o[3])
                    self._write(o[0], [a[i] * b[i] + c[i] for i in range(4)])
                elif name == "DP3":
                    a, b = self._read(o[1]), self._read(o[2])
                    self._write(o[0], [sum(a[i] * b[i] for i in range(3))] * 4)
                elif name == "DP4":
                    a, b = self._read(o[1]), self._read(o[2])
                    self._write(o[0], [sum(a[i] * b[i] for i in range(4))] * 4)
                elif name == "MIN":
                    self._write(o[0], _component(self._read(o[1]), min, self._read(o[2])))
                elif name == "MAX":
                    self._write(o[0], _component(self._read(o[1]), max, self._read(o[2])))
                elif name in {"SLT", "SGE"}:
                    a, b = self._read(o[1]), self._read(o[2])
                    cmp = (lambda x, y: 1.0 if x < y else 0.0) if name == "SLT" else (lambda x, y: 1.0 if x >= y else 0.0)
                    self._write(o[0], _component(a, cmp, b))
                elif name in {"EXP", "EXPP"}:
                    self._write(o[0], [2.0 ** x if math.isfinite(x) else 0.0 for x in self._read(o[1])])
                elif name in {"LOG", "LOGP"}:
                    self._write(o[0], [math.log2(max(abs(x), 1.0e-30)) for x in self._read(o[1])])
                elif name == "LIT":
                    x = self._read(o[1])
                    y = max(x[1], 0.0)
                    z = (y ** max(-128.0, min(128.0, x[3]))) if x[2] > 0.0 else 0.0
                    self._write(o[0], [1.0, y, z, 1.0])
                elif name == "DST":
                    a, b = self._read(o[1]), self._read(o[2])
                    self._write(o[0], [1.0, a[1] * b[1], a[2], b[3]])
                elif name == "LRP":
                    t, a, b = self._read(o[1]), self._read(o[2]), self._read(o[3])
                    self._write(o[0], [(1.0 - t[i]) * b[i] + t[i] * a[i] for i in range(4)])
                elif name == "FRC":
                    self._write(o[0], [x - math.floor(x) for x in self._read(o[1])])
                elif name == "RCP":
                    self._write(o[0], [1.0 / x if x != 0.0 else math.inf for x in self._read(o[1])])
                elif name == "RSQ":
                    self._write(o[0], [1.0 / math.sqrt(abs(x)) if x != 0.0 else math.inf for x in self._read(o[1])])
                elif name == "NRM":
                    x = self._read(o[1])
                    length = math.sqrt(sum(v * v for v in x[:3]))
                    self._write(o[0], [v / length if length else 0.0 for v in x[:3]] + [0.0])
                elif name == "ABS":
                    self._write(o[0], [abs(x) for x in self._read(o[1])])
                elif name == "POW":
                    a, b = self._read(o[1]), self._read(o[2])
                    self._write(o[0], [math.pow(abs(a[i]), b[i]) for i in range(4)])
                elif name == "CRS":
                    a, b = self._read(o[1]), self._read(o[2])
                    self._write(o[0], [
                        a[1] * b[2] - a[2] * b[1],
                        a[2] * b[0] - a[0] * b[2],
                        a[0] * b[1] - a[1] * b[0],
                        0.0,
                    ])
                elif name == "SINCOS":
                    x = self._read(o[1])
                    self._write(o[0], [math.sin(v) if i == 0 else math.cos(v) if i == 1 else 0.0 for i, v in enumerate(x)])
                elif name == "CMP":
                    cond, a, b = self._read(o[1]), self._read(o[2]), self._read(o[3])
                    self._write(o[0], [a[i] if cond[i] >= 0.0 else b[i] for i in range(4)])
                elif name == "DP2ADD":
                    a, b, c = self._read(o[1]), self._read(o[2]), self._read(o[3])
                    value = a[0] * b[0] + a[1] * b[1] + c[0]
                    self._write(o[0], [value] * 4)
                elif name in {"TEX", "TEXLDD", "TEXLDL"}:
                    self._write(o[0], self._texture(o[2], self._read(o[1])))
                else:
                    raise ValueError(f"unhandled supported opcode {name}")

        except (ValueError, OverflowError, ZeroDivisionError) as exc:
            return {
                "format": FORMAT,
                "status": "error",
                "stage": self.program.stage,
                "blocking_reasons": [f"shader-execution:{type(exc).__name__}:{exc}"],
                "unsupported": [],
                "color": None,
            }

        return {
            "format": FORMAT,
            "status": "executed",
            "stage": self.program.stage,
            "blocking_reasons": [],
            "unsupported": [],
            "color": self.outputs.get(0),
            "depth": self.depth,
            "temps": {str(k): list(v) for k, v in sorted(self.temps.items())},
        }


def shader_program_from_ir(payload: dict[str, Any]) -> ShaderProgram:
    """Rehydrate a SHIFT.ShaderProgram/1 JSON record for reference execution."""
    if payload.get("schema") != "SHIFT.ShaderProgram/1":
        raise ValueError("invalid shader IR schema")
    operands = []
    instructions = []
    for record in payload.get("instructions", []) or []:
        decoded_operands = []
        for raw in record.get("operands", []) or []:
            decoded_operands.append(Operand(**{
                key: raw.get(key)
                for key in Operand.__dataclass_fields__
                if key in raw
            }))
        predicate = record.get("predicate")
        decoded_predicate = (
            Operand(**{
                key: predicate.get(key)
                for key in Operand.__dataclass_fields__
                if key in predicate
            })
            if predicate
            else None
        )
        instructions.append(Instruction(
            offset=int(record.get("offset", 0)),
            opcode=int(record.get("opcode", 0)),
            name=str(record.get("name", "")),
            token=int(record.get("token", 0)),
            length=int(record.get("length", 0)),
            controls=int(record.get("controls", 0)),
            predicated=bool(record.get("predicated", False)),
            operands=decoded_operands,
            predicate=decoded_predicate,
        ))
    return ShaderProgram(
        offset=int(payload.get("offset", 0)),
        end=int(payload.get("end", 0)),
        stage=str(payload.get("stage", "unknown")),
        major=int((payload.get("shader_model") or [3, 0])[0]),
        minor=int((payload.get("shader_model") or [3, 0])[1]),
        instructions=instructions,
        inputs=list(payload.get("inputs", []) or []),
        outputs=list(payload.get("outputs", []) or []),
        samplers=[int(x) for x in payload.get("samplers", []) or []],
        constants=[int(x) for x in payload.get("constants", []) or []],
        temps=[int(x) for x in payload.get("temps", []) or []],
        unsupported_opcodes=[int(x) for x in payload.get("unsupported_opcodes", []) or []],
        const_ints=[int(x) for x in payload.get("const_ints", []) or []],
        const_bools=[int(x) for x in payload.get("const_bools", []) or []],
        sampler_types={int(k): str(v) for k, v in (payload.get("sampler_types") or {}).items()},
    )


def validate_pixel_program_inputs(program: ShaderProgram) -> dict[str, Any]:
    """Validate the varyings currently supported by the texture reference renderer."""
    unsupported = []
    for item in program.inputs:
        usage = str(item.get("usage") or "").upper()
        index = int(item.get("index", 0))
        if usage != "TEXCOORD" or index != 0:
            unsupported.append({
                "usage": usage,
                "index": index,
                "register": item.get("register"),
            })
    if program.stage != "pixel":
        unsupported.append({"reason": "not-pixel-stage", "stage": program.stage})
    return {
        "format": "SHIFT.ReferencePixelInputValidation/1",
        "valid": not unsupported,
        "unsupported": unsupported,
        "blocking_reasons": [
            f"pixel-input:unsupported:{item.get('usage')}:{item.get('index')}"
            for item in unsupported
        ],
    }


def material_constants_from_uniform_binding(
    uniform_binding: dict[str, Any] | None,
) -> dict[str, Any]:
    """Convert a MaterialUniformBinding/1 float payload into D3D9-style vec4 banks."""
    binding = uniform_binding or {}
    if binding.get("format") not in (None, "SHIFT.MaterialUniformBinding/1"):
        return {
            "format": "SHIFT.ReferenceConstantBank/1",
            "status": "unsupported",
            "blocking_reasons": ["uniform-binding:invalid-format"],
            "banks": {"c": {}},
        }

    banks: dict[str, dict[int, list[float]]] = {"c": {}, "c2": {}, "c3": {}, "c4": {}}
    reasons: list[str] = []
    for item in binding.get("bindings", []) or []:
        if item.get("binding") != "material-constant":
            reasons.append(f"uniform-binding:unsupported-binding:{item.get('binding')}")
            continue
        if int(item.get("register_set") or 0) != 2:
            reasons.append(
                f"uniform-binding:unsupported-register-set:{item.get('register_set')}"
            )
            continue
        ctab_type = str(item.get("ctab_type") or "").lower()
        values = item.get("value")
        if isinstance(values, (int, float)):
            flat = [float(values)]
        elif isinstance(values, list):
            flat = [float(x) for x in values]
        else:
            reasons.append(f"uniform-binding:value-not-numeric:{item.get('name')}")
            continue

        reg = int(item.get("register_index", -1))
        count = int(item.get("register_count", 0))
        if reg < 0 or count <= 0:
            reasons.append(f"uniform-binding:register-range-invalid:{item.get('name')}")
            continue

        if ctab_type in {"float", "float1", "float2", "float3", "float4"}:
            banks["c"][reg] = (flat + [0.0] * 4)[:4]
            continue
        if ctab_type == "float4x4":
            if len(flat) < 16 or count < 4:
                reasons.append(f"uniform-binding:matrix-payload-invalid:{item.get('name')}")
                continue
            for row in range(4):
                banks["c"][reg + row] = flat[row * 4:(row + 1) * 4]
            continue

        reasons.append(
            f"uniform-binding:unsupported-ctab-type:{item.get('ctab_type')}"
        )

    return {
        "format": "SHIFT.ReferenceConstantBank/1",
        "status": "ready" if not reasons else "unsupported",
        "blocking_reasons": list(dict.fromkeys(reasons)),
        "banks": banks,
    }


def execute_shader_ir(
    payload: dict[str, Any],
    *,
    inputs: dict[int, Iterable[float]] | None = None,
    constants: dict[str, dict[int, Iterable[float]]] | None = None,
    textures: dict[int, dict[str, Any]] | None = None,
    samplers: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Execute one embedded SHIFT.ShaderProgram/1 payload."""
    program = shader_program_from_ir(payload)
    return execute_shader(
        program,
        inputs=inputs,
        constants=constants,
        textures=textures,
        samplers=samplers,
    )


def execute_shader(
    program: ShaderProgram,
    *,
    inputs: dict[int, Iterable[float]] | None = None,
    constants: dict[str, dict[int, Iterable[float]]] | None = None,
    textures: dict[int, dict[str, Any]] | None = None,
    samplers: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return ReferenceShaderState(
        program,
        inputs=inputs,
        constants=constants,
        textures=textures,
        samplers=samplers,
    ).execute()
