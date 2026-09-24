"""Build a fail-closed runtime shader execution contract for one captured frame.

This is the bridge between the runtime D3D9 capture and the existing neutral
RenderCommand/reference-renderer layer. It does not invent texture contents:
external stages remain runtime object identities until mapped to real resources.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWRuntimeRenderContract/1"


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _find_selected_frame(
    runtime_report: Mapping[str, Any],
    selection: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    selected = _as_mapping(selection.get("selected"))
    if not selected:
        return None
    target_frame = selected.get("frame")
    frames = runtime_report.get("frames") or []
    for frame in frames:
        if isinstance(frame, Mapping) and frame.get("frame") == target_frame:
            return frame
    return None


def _required_external_stages(material_input: Mapping[str, Any]) -> list[int]:
    binding = _as_mapping(material_input.get("material_binding"))
    rows = binding.get("bindings")
    if not isinstance(rows, list):
        rows = material_input.get("bindings")
    stages: set[int] = set()
    for row in rows or []:
        if not isinstance(row, Mapping):
            continue
        if row.get("binding") != "external-or-specialised":
            continue
        value = row.get("d3d9_sampler_register")
        if value is None:
            value = row.get("slot")
        try:
            stages.add(int(value))
        except (TypeError, ValueError):
            continue
    return sorted(stages)


def _external_texture_state(
    frame: Mapping[str, Any],
    stages: list[int],
) -> dict[str, Any]:
    latest: dict[int, Any] = {}
    timeline = []
    for row in frame.get("texture_bindings") or []:
        if not isinstance(row, Mapping):
            continue
        try:
            stage = int(row.get("stage"))
        except (TypeError, ValueError):
            continue
        texture_ptr = row.get("texture_ptr")
        latest[stage] = texture_ptr
        timeline.append({
            "stage": stage,
            "texture_ptr": texture_ptr,
            "line": row.get("line"),
        })
    missing = [stage for stage in stages if not latest.get(stage)]
    return {
        "required_stages": stages,
        "latest_bindings": [
            {"stage": stage, "texture_ptr": latest.get(stage)}
            for stage in stages
        ],
        "missing_stages": missing,
        "timeline": timeline,
        "ready": not missing,
    }


def _same_meb_resource(
    material_input: Mapping[str, Any],
    frame: Mapping[str, Any],
) -> bool | None:
    provenance = _as_mapping(material_input.get("provenance"))
    mesh = _as_mapping(provenance.get("mesh_entry"))
    binding = _as_mapping(frame.get("vertex_declaration") or frame.get("binding"))
    expected_sha = mesh.get("sha256") or mesh.get("resource_sha256")
    actual_sha = binding.get("resource_sha256")
    if expected_sha and actual_sha:
        return str(expected_sha) == str(actual_sha)
    expected_path = mesh.get("path")
    actual_path = binding.get("resource_path")
    if expected_path and actual_path:
        def norm(value: Any) -> str:
            return str(value).replace("\\", "/").strip("/").lower()
        return norm(expected_path) == norm(actual_path)
    return None


def _constant_banks(frame: Mapping[str, Any]) -> dict[str, Any]:
    banks: dict[str, dict[int, list[float]]] = {"vertex": {}, "pixel": {}}
    writes = []
    for row in frame.get("constant_writes") or []:
        if not isinstance(row, Mapping):
            continue
        stage = str(row.get("stage") or "").lower()
        if stage not in banks:
            continue
        try:
            start = int(row.get("start_register"))
            count = int(row.get("vector4f_count", row.get("register_count")))
        except (TypeError, ValueError):
            continue
        values = row.get("values")
        if not isinstance(values, list) or len(values) != count * 4:
            continue
        for index in range(count):
            register = start + index
            banks[stage][register] = [
                float(value) for value in values[index * 4:(index + 1) * 4]
            ]
        writes.append({
            "stage": stage,
            "start_register": start,
            "vector4f_count": count,
            "line": row.get("line"),
        })
    return {
        "banks": {
            stage: {str(register): values for register, values in sorted(bank.items())}
            for stage, bank in banks.items()
        },
        "write_count": len(writes),
        "writes": writes,
        "ready": bool(writes),
    }


def _shader_identity(frame: Mapping[str, Any]) -> dict[str, Any]:
    identity = _as_mapping(frame.get("shader_permutation_identity"))
    vs = _as_mapping(frame.get("vertex_shader"))
    ps = _as_mapping(frame.get("pixel_shader"))
    result = {
        "identity_sha256": identity.get("identity_sha256"),
        "pair_byte_sha256": identity.get("pair_byte_sha256"),
        "vertex_byte_sha256": (
            _as_mapping(_as_mapping(identity.get("payload")).get("vertex"))
        ).get("byte_sha256"),
        "pixel_byte_sha256": (
            _as_mapping(_as_mapping(identity.get("payload")).get("pixel"))
        ).get("byte_sha256"),
        "vertex_shader_ptr": vs.get("shader_ptr"),
        "pixel_shader_ptr": ps.get("shader_ptr"),
        "vertex_create_known": bool(vs.get("create_known")),
        "pixel_create_known": bool(ps.get("create_known")),
    }
    result["ready"] = bool(
        result["identity_sha256"]
        and result["vertex_shader_ptr"]
        and result["pixel_shader_ptr"]
        and result["vertex_create_known"]
        and result["pixel_create_known"]
    )
    return result


def build_runtime_render_contract(
    material_input: Mapping[str, Any],
    runtime_report: Mapping[str, Any],
    selection: Mapping[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []

    if selection.get("format") != "SHIFT.BMWRuntimeShaderSelection/1":
        blockers.append("shader-selection:invalid-format")
    if selection.get("ready") is not True:
        blockers.extend(selection.get("blocking_reasons") or ["shader-selection:not-ready"])

    frame = _find_selected_frame(runtime_report, selection)
    if frame is None:
        blockers.append("runtime:selected-frame-missing")
        frame = {}

    same_resource = _same_meb_resource(material_input, frame)
    if same_resource is not True:
        blockers.append("runtime:same-meb-resource-not-proven")

    shader = _shader_identity(frame)
    if not shader["ready"]:
        blockers.append("runtime:shader-identity-not-ready")

    draws = list(frame.get("draws") or [])
    if not draws:
        blockers.append("runtime:indexed-draw-missing")

    constants = _constant_banks(frame)
    if not constants["ready"]:
        blockers.append("runtime:constant-writes-missing")

    external_stages = _required_external_stages(material_input)
    external_textures = _external_texture_state(frame, external_stages)
    if not external_textures["ready"]:
        blockers.append(
            "runtime:external-texture-bindings-missing:"
            + ",".join(str(x) for x in external_textures["missing_stages"])
        )

    declaration = _as_mapping(frame.get("vertex_declaration") or frame.get("binding"))
    declaration_ready = bool(
        declaration.get("bound_declaration_valid")
        or declaration.get("create_known")
    )
    if not declaration_ready:
        blockers.append("runtime:vertex-declaration-not-ready")

    selected = _as_mapping(selection.get("selected"))
    contract = {
        "format": FORMAT,
        "status": "ready" if not blockers else "blocked",
        "ready_for_shader_reference": not blockers,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "frame": {
            "frame": frame.get("frame"),
            "same_meb_resource": same_resource,
            "declaration": {
                "pointer": declaration.get("declaration_ptr"),
                "resource_path": declaration.get("resource_path"),
                "resource_sha256": declaration.get("resource_sha256"),
                "ready": declaration_ready,
            },
            "shader_selection": {
                "candidate_file": selected.get("candidate_file"),
                "program_offset": selected.get("candidate_program_offset"),
                "score": selected.get("score"),
            },
            "shader": shader,
            "draws": draws,
            "constants": constants,
            "external_textures": external_textures,
        },
        "provenance": {
            "selection_format": selection.get("format"),
            "runtime_report_format": runtime_report.get("format"),
            "runtime_frame": frame.get("frame"),
            "material_format": material_input.get("format"),
        },
        "render_input": {
            "format": "SHIFT.RenderCommandInput/1",
            "ready": not blockers,
            "shader": {
                "identity_sha256": shader.get("identity_sha256"),
                "pair_byte_sha256": shader.get("pair_byte_sha256"),
                "vertex_byte_sha256": shader.get("vertex_byte_sha256"),
                "pixel_byte_sha256": shader.get("pixel_byte_sha256"),
            },
            "draws": draws,
            "constant_banks": constants["banks"],
            "external_samplers": [
                {
                    "stage": stage,
                    "texture_ptr": next(
                        (
                            row.get("texture_ptr")
                            for row in external_textures["latest_bindings"]
                            if row.get("stage") == stage
                        ),
                        None,
                    ),
                    "resource": "runtime-external",
                }
                for stage in external_stages
            ],
        },
    }
    return contract


def validate_files(
    material_input_path: str | Path,
    runtime_report_path: str | Path,
    selection_path: str | Path,
) -> dict[str, Any]:
    material = json.loads(Path(material_input_path).read_text(encoding="utf-8"))
    runtime = json.loads(Path(runtime_report_path).read_text(encoding="utf-8"))
    selection = json.loads(Path(selection_path).read_text(encoding="utf-8"))
    return build_runtime_render_contract(material, runtime, selection)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a fail-closed BMW runtime shader execution contract"
    )
    parser.add_argument("material_input")
    parser.add_argument("runtime_report")
    parser.add_argument("selection")
    parser.add_argument("output")
    args = parser.parse_args()
    report = validate_files(args.material_input, args.runtime_report, args.selection)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready_for_shader_reference": report["ready_for_shader_reference"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready_for_shader_reference"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
