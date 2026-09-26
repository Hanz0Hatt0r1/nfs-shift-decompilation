"""Build draw-local BMW M3 BMT -> D3D9 state witness evidence.

The witness deliberately separates three levels of proof:
- decoded BMT numeric parameters observed in draw-local constant banks;
- runtime shader/texture object pointers observed at the same DrawIndexedPrimitive;
- exact shader permutation and exact DDS-object identity, which this frame dump does not provide.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

FORMAT = "SHIFT.BMWM3RuntimeMaterialWitness/1"
TARGET_STREAM = "0x27b39460"
TARGET_STRIDE = 76
TARGET_NUM_VERTICES = 3550
TARGET_RESOURCE = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
TARGET_RESOURCE_SHA256 = "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"

_FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?|inf|-inf|nan"
_CALL_RE = re.compile(r"^(\d+) ")
_FLOAT_RE = re.compile(_FLOAT)
_STREAM_RE = re.compile(
    r"StreamNumber = (\d+), pStreamData = (\S+), OffsetInBytes = (\d+), Stride = (\d+)"
)
_INDEX_RE = re.compile(r"pIndexData = (\S+)")
_SHADER_RE = re.compile(r"pShader = (\S+)")
_CONST_RE = re.compile(
    r"StartRegister = (\d+), pConstantData = \{(.*)\}, Vector4fCount = (\d+)\)"
)
_TEXTURE_RE = re.compile(r"Stage = (\d+), pTexture = (\S+)")
_SAMPLER_RE = re.compile(r"Sampler = (\d+), Type = (\S+), Value = (\S+)")
_DRAW_RE = re.compile(
    r"PrimitiveType = (\S+), BaseVertexIndex = (\d+), MinVertexIndex = (\d+), "
    r"NumVertices = (\d+), startIndex = (\d+), primCount = (\d+)"
)


def _ptr(value: str) -> str:
    return value.rstrip(")")


def _float_close(actual: float, expected: float, tolerance: float) -> bool:
    if math.isnan(expected):
        return math.isnan(actual)
    if math.isinf(expected):
        return actual == expected
    return math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance)


def _vector_close(actual: Iterable[float], expected: Iterable[float], tolerance: float) -> bool:
    actual = list(actual)
    expected = list(expected)
    return len(actual) == len(expected) and all(
        _float_close(float(a), float(e), tolerance) for a, e in zip(actual, expected)
    )


# Values copied from the decoded retail BMTs already closed in Phase 334.
# Register positions are intentionally discovered from draw-local state rather
# than hard-coded, while BMT parameter names remain provenance.
MATERIAL_WITNESS_PROFILE: tuple[dict[str, Any], ...] = (
    {
        "name": "BMW_M3_E36_PAINT",
        "bmt": "vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt",
        "shader": "render/shaders/bodywork.fx",
        "technique": "Bodywork",
        "primitive_counts": [2098, 2462],
        "witnesses": [
            {"stage": "pixel", "parameter": "primerBasis", "value": [0.129412, 0.129412, 0.129412, 1.0]},
            {"stage": "pixel", "parameter": "metalBasis", "value": [0.035294, 0.035294, 0.035294, 1.0]},
            {"stage": "pixel", "parameter": "dirtBasis", "value": [0.137255, 0.133333, 0.121569, 1.0]},
        ],
        "samplers": [
            {"parameter": "diffuseTexture", "register": 1},
            {"parameter": "specularTexture", "register": 2},
            {"parameter": "scratchControlTexture", "register": 4},
        ],
        "external_samplers": [
            {"name": "sShadowMap_f1_0", "register": 0},
            {"name": "environmentMap", "register": 3},
        ],
    },
    {
        "name": "BMW_M3_E36_BADGING",
        "bmt": "vehicles/bmw_m3_e36/bmw_m3_e36_badging.bmt",
        "shader": "render/shaders/vehicles_basic.fx",
        "technique": "VehicleBasic_Translucent",
        "primitive_counts": [50],
        "witnesses": [
            {"stage": "vertex", "parameter": "fresnelFactor", "value": [0.15, 0.0, 0.0, 0.0]},
            {"stage": "pixel", "parameter": "maxSpecPower", "value": [100.0, 0.0, 0.0, 0.0]},
            {"stage": "pixel", "parameter": "globalSpecularFactor", "value": [1.5, 0.0, 0.0, 0.0]},
            {"stage": "pixel", "parameter": "globalEMapFactor", "value": [0.75, 0.0, 0.0, 0.0]},
        ],
        "samplers": [],
        "sampler_stage_status": "not-proven",
    },
    {
        "name": "GENERIC_WINDOWS",
        "bmt": "vehicles/bmw_m3_e36/generic_windows.bmt",
        "shader": "render/shaders/glass.fx",
        "technique": "Glass",
        "primitive_counts": [204],
        "witnesses": [
            {"stage": "pixel", "parameter": "crackColour", "value": [0.678431, 0.8, 0.8, 0.9]},
            {"stage": "pixel", "parameter": "dirtBasis", "value": [0.6, 0.576471, 0.537255, 0.5]},
            {"stage": "pixel", "parameter": "crackUVoffset", "value": [0.0, 0.0, 3.0, 5.0]},
            {"stage": "pixel", "parameter": "crackStrength", "value": [4.0, 0.0, 0.0, 0.0]},
            {"stage": "pixel", "parameter": "damageStartCracks", "value": [0.18, 0.0, 0.0, 0.0]},
            {"stage": "pixel", "parameter": "damageCrackSlope", "value": [50.0, 0.0, 0.0, 0.0]},
            {"stage": "pixel", "parameter": "crackFinalScale", "value": [0.98, 0.0, 0.0, 0.0]},
        ],
        "samplers": [],
        "sampler_stage_status": "not-proven",
    },
    {
        "name": "GENERIC_GLOSS_BLACK",
        "bmt": "vehicles/bmw_m3_e36/generic_gloss_black.bmt",
        "shader": "render/shaders/vehicles_basic.fx",
        "technique": "VehicleBasic",
        "primitive_counts": [192],
        "witnesses": [
            {"stage": "vertex", "parameter": "fresnelFactor", "value": [0.42, 0.0, 0.0, 0.0]},
            {"stage": "pixel", "parameter": "maxSpecPower", "value": [8192.0, 0.0, 0.0, 0.0]},
        ],
        "samplers": [],
        "sampler_stage_status": "not-proven",
    },
    {
        "name": "BMW_M3_E36_LIGHTSGLASS",
        "bmt": "vehicles/bmw_m3_e36/bmw_m3_e36_lightsglass.bmt",
        "shader": "render/shaders/glass.fx",
        "technique": "Glass",
        "primitive_counts": [28],
        "witnesses": [
            {"stage": "pixel", "parameter": "crackColour", "value": [0.678431, 0.8, 0.8, 0.9]},
            {"stage": "pixel", "parameter": "dirtBasis", "value": [0.501961, 0.482353, 0.45098, 0.5]},
            {"stage": "pixel", "parameter": "crackUVoffset", "value": [0.0, 0.0, 7.0, 14.0]},
            {"stage": "pixel", "parameter": "crackStrength", "value": [25.0, 0.0, 0.0, 0.0]},
            {"stage": "pixel", "parameter": "damageStartCracks", "value": [0.01, 0.0, 0.0, 0.0]},
            {"stage": "pixel", "parameter": "damageCrackSlope", "value": [100.0, 0.0, 0.0, 0.0]},
        ],
        "samplers": [],
        "sampler_stage_status": "not-proven",
    },
)


def parse_frame_dump(text: str, *, target_stream: str = TARGET_STREAM) -> list[dict[str, Any]]:
    state: dict[str, Any] = {
        "streams": {},
        "indices": None,
        "vertex_shader": None,
        "pixel_shader": None,
        "constants": {"vertex": {}, "pixel": {}},
        "textures": {},
        "samplers": {},
    }
    draws: list[dict[str, Any]] = []
    for line in text.splitlines():
        call_match = _CALL_RE.match(line)
        if not call_match:
            continue
        call = int(call_match.group(1))
        if "SetStreamSource(" in line:
            m = _STREAM_RE.search(line)
            if m:
                state["streams"][int(m.group(1))] = {
                    "ptr": _ptr(m.group(2)),
                    "offset": int(m.group(3)),
                    "stride": int(m.group(4)),
                }
        elif "SetIndices(" in line:
            m = _INDEX_RE.search(line)
            if m:
                state["indices"] = _ptr(m.group(1))
        elif "SetVertexShader(" in line:
            m = _SHADER_RE.search(line)
            if m:
                state["vertex_shader"] = _ptr(m.group(1))
        elif "SetPixelShader(" in line:
            m = _SHADER_RE.search(line)
            if m:
                state["pixel_shader"] = _ptr(m.group(1))
        elif "SetVertexShaderConstantF(" in line or "SetPixelShaderConstantF(" in line:
            stage = "vertex" if "SetVertexShaderConstantF(" in line else "pixel"
            m = _CONST_RE.search(line)
            if m:
                start = int(m.group(1))
                values = [float(value) for value in _FLOAT_RE.findall(m.group(2))]
                count = int(m.group(3))
                if len(values) != count * 4:
                    raise ValueError(f"call {call}: constant value count mismatch")
                for index in range(count):
                    state["constants"][stage][start + index] = values[index * 4:index * 4 + 4]
        elif "SetTexture(" in line:
            m = _TEXTURE_RE.search(line)
            if m:
                state["textures"][int(m.group(1))] = _ptr(m.group(2))
        elif "SetSamplerState(" in line:
            m = _SAMPLER_RE.search(line)
            if m:
                sampler = int(m.group(1))
                state["samplers"].setdefault(sampler, {})[m.group(2)] = _ptr(m.group(3))
        elif "DrawIndexedPrimitive(" in line and "NumVertices = 3550" in line:
            m = _DRAW_RE.search(line)
            stream0 = state["streams"].get(0)
            if not m or not stream0:
                continue
            if stream0["ptr"].lower() != target_stream.lower() or stream0["stride"] != TARGET_STRIDE:
                continue
            draws.append({
                "call": call,
                "primitive_type": m.group(1),
                "base_vertex_index": int(m.group(2)),
                "min_vertex_index": int(m.group(3)),
                "num_vertices": int(m.group(4)),
                "start_index": int(m.group(5)),
                "primitive_count": int(m.group(6)),
                "stream0": dict(stream0),
                "index_buffer": state["indices"],
                "vertex_shader": state["vertex_shader"],
                "pixel_shader": state["pixel_shader"],
                "constant_banks": {
                    "vertex": {str(k): list(v) for k, v in state["constants"]["vertex"].items()},
                    "pixel": {str(k): list(v) for k, v in state["constants"]["pixel"].items()},
                },
                "texture_bindings": {str(k): v for k, v in state["textures"].items()},
                "sampler_states": {str(k): dict(v) for k, v in state["samplers"].items()},
            })
    return draws


def _find_witness(stage_banks: Mapping[str, Mapping[str, list[float]]], witness: Mapping[str, Any], tolerance: float) -> dict[str, Any] | None:
    stage = str(witness["stage"])
    expected = [float(value) for value in witness["value"]]
    bank = stage_banks.get(stage) or {}
    for register_key, vector in bank.items():
        if _vector_close(vector, expected, tolerance):
            return {
                "parameter": witness["parameter"],
                "stage": stage,
                "register": int(register_key),
                "expected": expected,
                "observed": list(vector),
                "status": "match",
            }
    return None


def _sampler_observations(draw: Mapping[str, Any], material: Mapping[str, Any]) -> dict[str, Any]:
    textures = {int(k): v for k, v in (draw.get("texture_bindings") or {}).items()}
    samplers = {int(k): v for k, v in (draw.get("sampler_states") or {}).items()}
    rows = []
    for row in material.get("samplers") or []:
        register = int(row["register"])
        rows.append({
            "kind": "material",
            "parameter": row["parameter"],
            "register": register,
            "texture_ptr": textures.get(register),
            "sampler_state": samplers.get(register),
            "texture_object_status": "pointer-observed" if textures.get(register) else "not-observed",
        })
    for row in material.get("external_samplers") or []:
        register = int(row["register"])
        rows.append({
            "kind": "external",
            "parameter": row["name"],
            "register": register,
            "texture_ptr": textures.get(register),
            "sampler_state": samplers.get(register),
            "texture_object_status": "pointer-observed" if textures.get(register) else "not-observed",
        })
    for row in rows:
        state = row.get("sampler_state") or {}
        row["sampler_state"] = {
            key: state[key]
            for key in (
                "D3DSAMP_MINFILTER", "D3DSAMP_MAGFILTER", "D3DSAMP_MIPFILTER",
                "D3DSAMP_ADDRESSU", "D3DSAMP_ADDRESSV", "D3DSAMP_ADDRESSW",
                "D3DSAMP_SRGBTEXTURE",
            )
            if key in state
        }
    return {
        "status": "pointer-observed" if rows and all(row["texture_ptr"] for row in rows) else (
            "not-proven" if not rows else "partial"
        ),
        "material_samplers": rows,
        "observed_stages": sorted(textures),
        "exact_dds_identity": "not-proven",
    }


def match_draw(draw: Mapping[str, Any], material: Mapping[str, Any], *, tolerance: float = 1e-5) -> dict[str, Any]:
    witness_rows = []
    for witness in material.get("witnesses") or []:
        found = _find_witness(draw.get("constant_banks") or {}, witness, tolerance)
        witness_rows.append(found or {
            "parameter": witness["parameter"],
            "stage": witness["stage"],
            "expected": [float(value) for value in witness["value"]],
            "status": "missing",
        })
    matches = [row for row in witness_rows if row["status"] == "match"]
    all_numeric = len(matches) == len(witness_rows) and bool(witness_rows)
    primitive_ok = int(draw["primitive_count"]) in {int(value) for value in material.get("primitive_counts") or []}
    ready = all_numeric and primitive_ok
    return {
        "material": material["name"],
        "bmt": material["bmt"],
        "shader": material["shader"],
        "technique": material["technique"],
        "numeric_witness_status": "match" if all_numeric else "partial",
        "numeric_witness_match_count": len(matches),
        "numeric_witness_expected_count": len(witness_rows),
        "primitive_range_status": "match" if primitive_ok else "mismatch",
        "witnesses": witness_rows,
        "samplers": _sampler_observations(draw, material),
        "shader_object": {
            "vertex_shader": draw.get("vertex_shader"),
            "pixel_shader": draw.get("pixel_shader"),
            "identity_status": "pointer-observed; exact-permutation-not-proven",
        },
        "ready": ready,
    }


def build_report(frame_text: str, *, tolerance: float = 1e-5) -> dict[str, Any]:
    draws = parse_frame_dump(frame_text)
    match_rows: list[dict[str, Any]] = []
    for draw in draws:
        matches = [match_draw(draw, material, tolerance=tolerance) for material in MATERIAL_WITNESS_PROFILE]
        ready_matches = [row for row in matches if row["ready"]]
        if len(ready_matches) == 1:
            match_rows.append({
                "draw": {
                    "call": draw["call"],
                    "primitive_type": draw["primitive_type"],
                    "base_vertex_index": draw["base_vertex_index"],
                    "num_vertices": draw["num_vertices"],
                    "min_vertex_index": draw["min_vertex_index"],
                    "start_index": draw["start_index"],
                    "primitive_count": draw["primitive_count"],
                    "stream0": draw["stream0"],
                    "index_buffer": draw["index_buffer"],
                },
                "match": ready_matches[0],
            })
        elif len(ready_matches) > 1:
            match_rows.append({"draw": {"call": draw["call"]}, "status": "ambiguous", "matches": ready_matches})
    by_material: dict[str, int] = {}
    for row in match_rows:
        name = row.get("match", {}).get("material")
        if name:
            by_material[name] = by_material.get(name, 0) + 1
    return {
        "format": FORMAT,
        "status": "observed" if match_rows else "not-found",
        "ready": bool(match_rows),
        "resource": {"path": TARGET_RESOURCE, "sha256": TARGET_RESOURCE_SHA256},
        "target_stream": {"pointer": TARGET_STREAM, "stride": TARGET_STRIDE, "num_vertices": TARGET_NUM_VERTICES},
        "frame": 30444,
        "target_draw_count": len(draws),
        "matched_draw_count": len([row for row in match_rows if row.get("match")]),
        "material_match_count": by_material,
        "material_match_rows": match_rows,
        "boundary": {
            "draw_local_state": "proven-from-frame-dump",
            "bmt_numeric_parameter_witness": "proven",
            "shader_object_pointer": "observed",
            "exact_shader_permutation": "not-proven",
            "exact_dds_texture_object_identity": "not-proven",
            "raw_runtime_vb_ib_bytes": "not-claimed",
        },
    }


def validate_report(report: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if report.get("format") != FORMAT:
        reasons.append("format:invalid")
    if report.get("target_draw_count") != 28:
        reasons.append(f"draw-count:expected-28:observed-{report.get('target_draw_count')}")
    expected = {
        "BMW_M3_E36_PAINT": 4,
        "BMW_M3_E36_BADGING": 2,
        "GENERIC_WINDOWS": 2,
        "GENERIC_GLOSS_BLACK": 2,
        "BMW_M3_E36_LIGHTSGLASS": 2,
    }
    if report.get("material_match_count") != expected:
        reasons.append("material-match-count:mismatch")
    expected_indices = {
        192: "0x27b396e0",
        2098: "0x27b39560",
        2462: "0x27b395e0",
        50: "0x27b394e0",
        204: "0x27b39660",
        28: "0x27b39760",
    }
    for row in report.get("material_match_rows") or []:
        match = row.get("match") or {}
        draw = row.get("draw") or {}
        expected_index = expected_indices.get(draw.get("primitive_count"))
        if expected_index and draw.get("index_buffer") != expected_index:
            reasons.append(f"draw:{draw.get('call')}:index-buffer-mismatch")
        if (
            draw.get("primitive_type") != "D3DPT_TRIANGLELIST"
            or draw.get("base_vertex_index") != 0
            or draw.get("min_vertex_index") != 0
            or draw.get("num_vertices") != TARGET_NUM_VERTICES
            or draw.get("start_index") != 0
        ):
            reasons.append(f"draw:{draw.get('call')}:geometry-state-mismatch")
        if not match.get("ready"):
            reasons.append(f"draw:{draw.get('call')}:material-witness-not-ready")
        if match.get("samplers", {}).get("exact_dds_identity") != "not-proven":
            reasons.append(f"draw:{draw.get('call')}:dds-boundary-invalid")
        if match.get("shader_object", {}).get("identity_status") != "pointer-observed; exact-permutation-not-proven":
            reasons.append(f"draw:{draw.get('call')}:shader-boundary-invalid")
    return list(dict.fromkeys(reasons))


def validate_frame_dump(path: str | Path) -> dict[str, Any]:
    source_path = Path(path)
    source_bytes = source_path.read_bytes()
    report = build_report(source_bytes.decode("utf-8"))
    report["source"] = {
        "path": source_path.name,
        "sha256": hashlib.sha256(source_bytes).hexdigest(),
        "size": len(source_bytes),
        "trace_sha256": "116b5fed58c79d4e73c7903cf08625abb74b33ce8818b0535c00c67f19ec965d",
    }
    reasons = validate_report(report)
    report["validation"] = {"status": "match" if not reasons else "blocked", "ready": not reasons, "blocking_reasons": reasons}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build BMW M3 draw-local BMT material witness evidence")
    parser.add_argument("frame_dump")
    parser.add_argument("output")
    args = parser.parse_args()
    report = validate_frame_dump(args.frame_dump)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "validation": report["validation"],
        "material_match_count": report["material_match_count"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
