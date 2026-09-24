"""Deterministic software vertex-stage adapter for SHIFT ShaderProgram/1."""
from __future__ import annotations

import re
from typing import Any, Iterable

from shader_reference import execute_shader_ir


FORMAT = "SHIFT.ReferenceVertexExecution/1"

_OUTPUT_REGISTER_TYPES = {
    "or": 4,
    "od": 5,
    "ot": 6,
    "oc": 8,
    "odepth": 9,
}


def _vec4(value: Iterable[float] | None, *, default_w: float = 1.0) -> tuple[float, float, float, float]:
    row = [float(x) for x in (value or [])]
    if not row:
        row = [0.0, 0.0, 0.0]
    source_len = len(row)
    row = (row + [0.0] * 4)[:4]
    if source_len == 3:
        row[3] = default_w
    return tuple(row)  # type: ignore[return-value]


def _row(mesh: dict[str, Any], semantic: str, index: int, vertex_index: int) -> tuple[float, float, float, float] | None:
    semantic = semantic.upper()
    rows = None
    if semantic == "POSITION" and index == 0:
        rows = mesh.get("vertices")
    elif semantic == "NORMAL" and index == 0:
        rows = mesh.get("normals")
    elif semantic == "TANGENT" and index == 0:
        rows = mesh.get("tangents")
    elif semantic == "BINORMAL" and index == 0:
        rows = mesh.get("tangents2")
    elif semantic == "BLENDWEIGHT" and index == 0:
        rows = mesh.get("bone_weights")
    elif semantic == "BLENDINDICES" and index == 0:
        rows = mesh.get("bone_indices")
    elif semantic == "TEXCOORD" and 0 <= index <= 4:
        layers = mesh.get("uv_layers") or {}
        rows = layers.get(str(130 + index)) or layers.get(130 + index)
        if rows is None and index == 0:
            rows = mesh.get("uvs")
    if rows is None:
        return None
    try:
        value = rows[vertex_index]
    except (IndexError, KeyError, TypeError):
        return None
    return _vec4(value, default_w=1.0)


def build_vertex_inputs(
    program: dict[str, Any],
    mesh: dict[str, Any],
    vertex_index: int,
) -> dict[int, tuple[float, float, float, float]]:
    inputs: dict[int, tuple[float, float, float, float]] = {}
    for item in program.get("inputs", []) or []:
        usage = str(item.get("usage") or "").upper()
        semantic_index = int(item.get("index", 0))
        match = re.search(r"v(\d+)", str(item.get("register", "")))
        if not match:
            raise ValueError(f"vertex shader input has no recoverable register: {item}")
        register = int(match.group(1))
        value = _row(mesh, usage, semantic_index, vertex_index)
        if value is None:
            raise ValueError(
                f"vertex shader requires {usage}{semantic_index} but mesh has no matching attribute"
            )
        inputs[register] = value
    return inputs


def _parse_output_register(register: str) -> tuple[int, int] | None:
    raw = str(register or "").strip().lower()
    for prefix, reg_type in _OUTPUT_REGISTER_TYPES.items():
        if raw.startswith(prefix):
            suffix = raw[len(prefix):]
            if suffix.isdigit():
                return reg_type, int(suffix)
            if prefix == "odepth" and not suffix:
                return reg_type, 0
    return None


def extract_vertex_outputs(program: dict[str, Any], execution: dict[str, Any]) -> dict[str, Any]:
    output_registers = {
        tuple(int(part) for part in key.split(":", 1)): list(value)
        for key, value in (execution.get("output_registers") or {}).items()
        if ":" in key
    }
    outputs: dict[str, list[float]] = {}
    position = None
    for item in program.get("outputs", []) or []:
        usage = str(item.get("usage") or "").upper()
        semantic_index = int(item.get("index", 0))
        parsed = _parse_output_register(str(item.get("register", "")))
        if parsed is None:
            continue
        value = output_registers.get(parsed)
        if value is None:
            continue
        outputs[f"{usage}{semantic_index}"] = value
        if usage in {"POSITION", "POSITIONT"} and semantic_index == 0:
            position = value
    if position is None:
        return {
            "status": "error",
            "blocking_reasons": ["vertex-output:POSITION0-missing"],
            "outputs": outputs,
            "position_clip": None,
            "varyings": {},
        }

    varyings = {
        key: value
        for key, value in outputs.items()
        if key not in {"POSITION0", "POSITIONT0"}
    }
    return {
        "status": "executed",
        "blocking_reasons": [],
        "outputs": outputs,
        "position_clip": position,
        "varyings": varyings,
    }


def execute_vertex(
    program: dict[str, Any],
    mesh: dict[str, Any],
    vertex_index: int,
    *,
    constants: dict[str, dict[int, Iterable[float]]] | None = None,
) -> dict[str, Any]:
    if program.get("schema") != "SHIFT.ShaderProgram/1":
        return {
            "format": FORMAT,
            "status": "unsupported",
            "blocking_reasons": ["vertex-program:invalid-schema"],
        }
    if str(program.get("stage", "")).lower() != "vertex":
        return {
            "format": FORMAT,
            "status": "unsupported",
            "blocking_reasons": ["vertex-program:not-vertex-stage"],
        }

    inputs = build_vertex_inputs(program, mesh, vertex_index)
    execution = execute_shader_ir(
        program,
        inputs=inputs,
        constants=constants,
    )
    if execution.get("status") != "executed":
        return {
            "format": FORMAT,
            **execution,
        }

    extracted = extract_vertex_outputs(program, execution)
    return {
        "format": FORMAT,
        **extracted,
        "vertex_index": vertex_index,
        "shader_execution": execution,
    }


def execute_vertex_program(
    program: dict[str, Any],
    mesh: dict[str, Any],
    *,
    constants: dict[str, dict[int, Iterable[float]]] | None = None,
) -> dict[str, Any]:
    vertices = mesh.get("vertices") or []
    results = [
        execute_vertex(program, mesh, index, constants=constants)
        for index in range(len(vertices))
    ]
    if any(result.get("status") != "executed" for result in results):
        failures = [
            reason
            for result in results
            for reason in result.get("blocking_reasons", [])
        ]
        return {
            "format": FORMAT,
            "status": "error",
            "blocking_reasons": failures,
            "vertices": results,
        }
    return {
        "format": FORMAT,
        "status": "executed",
        "blocking_reasons": [],
        "vertex_count": len(results),
        "vertices": results,
    }
