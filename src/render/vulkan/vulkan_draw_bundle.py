"""Prepare one runtime-proven neutral RenderCommand draw for Vulkan.

This is the neutral counterpart to the BMW-specific bundle builder. It accepts
neutral geometry (including SHIFT.NeutralMesh/1 from the IMB adapter), preserves
RuntimeProvenDraw provenance, and reuses the existing native submission,
geometry, constants, texture, sampler and pipeline-state gates.

It intentionally does not claim that the scene world matrix is executed by the
current Vulkan shader path; the geometry packet still performs its historical
geometry-only clip-space normalization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from material_pipeline_state import translate_bmt_pipeline_state
from render_submission_gate import validate_native_submission
from vulkan_constant_packet import build_vulkan_constant_packet
from vulkan_cube_packet import build_vulkan_cube_packet
from vulkan_geometry_packet import export_vulkan_geometry_packet
from vulkan_sampler_contract import (
    build_sampler_contract_report,
    write_sampler_contract_report,
    write_sampler_metadata,
)
from vulkan_texture_packet import build_vulkan_texture_packet
from vulkan_world_transform_packet import build_vulkan_world_transform_packet

FORMAT = "SHIFT.VulkanDrawBundle/1"
RUNTIME_PROVEN_FORMAT = "SHIFT.RuntimeProvenDraw/1"


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (bytes, bytearray)):
        path.write_bytes(bytes(value))
        return
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _mapped_registers(
    value: str | Path | Mapping[str, Any] | None,
) -> set[int]:
    if value is None:
        return set()
    payload = _load(value) if isinstance(value, (str, Path)) else dict(value)
    result: set[int] = set()
    for key in payload:
        try:
            result.add(int(key))
        except (TypeError, ValueError):
            raise ValueError("texture mapping contains an invalid sampler register")
    return result


def _neutral_mesh(value: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    source = dict(value)
    if source.get("format") == "SHIFT.IMBNeutralGeometry/1":
        mesh = source.get("mesh")
        if not isinstance(mesh, Mapping):
            raise ValueError("IMB neutral geometry does not contain mesh")
        return dict(mesh), {
            "input_format": source.get("format"),
            "mesh_format": mesh.get("format"),
            "source_format": mesh.get("source_format"),
        }

    if source.get("format") not in {
        None,
        "SHIFT.MEB",
        "SHIFT.NeutralMesh/1",
    }:
        raise ValueError(
            "mesh must be SHIFT.MEB, SHIFT.NeutralMesh/1, "
            "SHIFT.IMBNeutralGeometry/1, or an untagged neutral mesh"
        )
    return source, {
        "input_format": source.get("format"),
        "mesh_format": source.get("format"),
        "source_format": source.get("source_format"),
    }


def _runtime_provenance_gate(
    submesh: Mapping[str, Any],
    *,
    required: bool,
) -> dict[str, Any]:
    reasons: list[str] = []
    provenance = submesh.get("runtime_provenance")
    if provenance is None:
        if required:
            reasons.append("vulkan-draw-bundle:runtime-provenance-missing")
        return {
            "format": "SHIFT.VulkanDrawRuntimeProvenanceGate/1",
            "required": required,
            "ready": not reasons,
            "blocking_reasons": reasons,
            "provenance": None,
        }
    if not isinstance(provenance, Mapping):
        reasons.append("vulkan-draw-bundle:runtime-provenance-invalid")
        return {
            "format": "SHIFT.VulkanDrawRuntimeProvenanceGate/1",
            "required": required,
            "ready": False,
            "blocking_reasons": reasons,
            "provenance": None,
        }

    if provenance.get("format") != RUNTIME_PROVEN_FORMAT:
        reasons.append("vulkan-draw-bundle:runtime-provenance-format-invalid")
    if provenance.get("status") != "proven":
        reasons.append("vulkan-draw-bundle:runtime-provenance-not-proven")

    resource = provenance.get("resource") or {}
    if not isinstance(resource, Mapping):
        reasons.append("vulkan-draw-bundle:runtime-resource-invalid")
        resource = {}
    if resource.get("source_kind") != "IMB":
        reasons.append("vulkan-draw-bundle:runtime-resource-not-imb")
    if not resource.get("path"):
        reasons.append("vulkan-draw-bundle:runtime-resource-path-missing")
    if _sha256(resource.get("sha256")) is None:
        reasons.append("vulkan-draw-bundle:runtime-resource-sha256-invalid")

    selection = provenance.get("shader_selection") or {}
    if not isinstance(selection, Mapping):
        selection = {}
        reasons.append("vulkan-draw-bundle:runtime-selection-invalid")
    if selection.get("selection_source") != "runtime-admission":
        reasons.append("vulkan-draw-bundle:runtime-selection-source-invalid")
    if selection.get("selection_status") != "unique":
        reasons.append("vulkan-draw-bundle:runtime-selection-not-unique")
    if selection.get("runtime_selection_ready") is not True:
        reasons.append("vulkan-draw-bundle:runtime-selection-not-ready")

    draw_range = provenance.get("draw_range") or {}
    try:
        first_index = int(draw_range.get("first_index"))
        index_count = int(draw_range.get("index_count"))
        primitive_count = int(draw_range.get("primitive_count"))
        command_first = int(submesh.get("first_index"))
        command_count = int(submesh.get("index_count"))
    except (TypeError, ValueError):
        reasons.append("vulkan-draw-bundle:runtime-draw-range-invalid")
    else:
        if (
            first_index != command_first
            or index_count != command_count
            or index_count <= 0
            or index_count % 3
            or primitive_count != index_count // 3
        ):
            reasons.append("vulkan-draw-bundle:runtime-draw-range-mismatch")

    return {
        "format": "SHIFT.VulkanDrawRuntimeProvenanceGate/1",
        "required": required,
        "ready": not reasons,
        "blocking_reasons": list(dict.fromkeys(reasons)),
        "provenance": json.loads(json.dumps(provenance)),
    }


def _shader_sources(
    command: Mapping[str, Any],
    output: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, submesh in enumerate(command.get("submeshes", []) or []):
        shader = submesh.get("shader") or {}
        for stage in ("vertex", "pixel"):
            source = shader.get(f"vulkan_{stage}_glsl") or shader.get(stage)
            if not source:
                continue
            target = output / "shaders" / f"submesh_{index}.{stage}.glsl"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(source), encoding="utf-8")
            rows.append({
                "submesh_index": index,
                "stage": stage,
                "path": str(target.relative_to(output)),
                "sha256": _hash(target),
                "source_format": "GLSL-from-RenderCommand/1",
                "vulkan_compilation": "not-run",
            })
    return rows


def build_vulkan_draw_bundle(
    render_command: str | Path | Mapping[str, Any],
    mesh: str | Path | Mapping[str, Any],
    output_dir: str | Path,
    *,
    textures: str | Path | Mapping[str, Any] | None = None,
    external_textures: str | Path | Mapping[str, Any] | None = None,
    environment_cube: str | Path | Mapping[str, Any] | None = None,
    command_index: int = 0,
    submesh_index: int = 0,
    require_runtime_provenance: bool = True,
) -> dict[str, Any]:
    command_source = (
        _load(render_command)
        if isinstance(render_command, (str, Path))
        else dict(render_command)
    )
    mesh_input = (
        _load(mesh)
        if isinstance(mesh, (str, Path))
        else dict(mesh)
    )
    mesh_source, mesh_provenance = _neutral_mesh(mesh_input)

    input_format = command_source.get("format")
    if input_format not in {"SHIFT.RenderBinding/1", "SHIFT.RenderCommand/1"}:
        raise ValueError(
            "input must be SHIFT.RenderBinding/1 or SHIFT.RenderCommand/1"
        )
    commands = (
        [command_source]
        if input_format == "SHIFT.RenderCommand/1"
        else list(command_source.get("render_commands") or [])
    )
    if command_index < 0 or command_index >= len(commands):
        raise ValueError(f"command index out of range: {command_index}")
    selected_command = commands[command_index]
    if not isinstance(selected_command, Mapping):
        raise ValueError(f"render command {command_index} is not an object")
    submeshes = list(selected_command.get("submeshes") or [])
    if submesh_index < 0 or submesh_index >= len(submeshes):
        raise ValueError(f"submesh index out of range: {submesh_index}")
    if not isinstance(submeshes[submesh_index], Mapping):
        raise ValueError(f"submesh {submesh_index} is not an object")

    selected = dict(selected_command)
    selected_submesh = dict(submeshes[submesh_index])
    selected["submeshes"] = [selected_submesh]
    selected["runtime_proven_draw_count"] = (
        1 if selected_submesh.get("runtime_provenance") is not None else 0
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    runtime_gate = _runtime_provenance_gate(
        selected_submesh,
        required=require_runtime_provenance,
    )
    native_gate = validate_native_submission(selected)
    early_blockers = list(runtime_gate["blocking_reasons"])
    early_blockers.extend(native_gate.get("blocking_reasons") or [])
    if early_blockers:
        report = {
            "format": FORMAT,
            "version": 1,
            "status": "blocked",
            "ready": False,
            "blocking_reasons": list(dict.fromkeys(early_blockers)),
            "source": {
                "render_command_format": input_format,
                "command_index": command_index,
                "submesh_index": submesh_index,
                "mesh_ref": (selected_command.get("mesh") or {}).get("ref"),
                "mesh_provenance": mesh_provenance,
            },
            "runtime_provenance_gate": runtime_gate,
            "native_submission_gate": native_gate,
            "artifacts": {},
            "external_samplers": [],
            "scene_transform": {
                "world_matrix": selected_command.get("world_matrix"),
                "execution_status": "not-applied-by-vulkan-geometry-path",
            },
            "native_execution": {
                "status": "blocked-by-admission-gate",
            },
        }
        _write(out / "bundle_manifest.json", report)
        report["manifest_sha256"] = _hash(out / "bundle_manifest.json")
        return report

    geometry_path = out / "geometry.svpk"
    constants_path = out / "constants.svcp"
    geometry = export_vulkan_geometry_packet(
        selected,
        mesh_source,
        geometry_path,
        submesh_index=0,
    )
    constants = build_vulkan_constant_packet(selected, constants_path)

    texture_report = None
    texture_path: Path | None = None
    material_textures_required = bool(selected_submesh.get("textures"))
    if (
        textures is not None
        or (
            external_textures is not None
            and not material_textures_required
        )
    ):
        texture_path = out / "textures.svtp"
        texture_report = build_vulkan_texture_packet(
            selected,
            textures if textures is not None else {},
            texture_path,
            external_textures=external_textures,
        )

    has_s3_cube = any(
        str(row.get("sampler_type") or "") == "samplerCube"
        and int(
            row.get(
                "d3d9_sampler_register",
                row.get("slot", -1),
            )
        ) == 3
        for row in (selected_submesh.get("external_samplers") or [])
    )
    cube_report = None
    cube_path: Path | None = None
    if has_s3_cube and environment_cube is not None:
        cube_path = out / "environment_cube.svcp"
        cube_report = build_vulkan_cube_packet(
            selected,
            environment_cube,
            cube_path,
        )

    shader_rows = _shader_sources(selected, out)

    sampler_report = build_sampler_contract_report(selected)
    sampler_contract_path = out / "sampler_contracts.json"
    sampler_report = write_sampler_contract_report(
        sampler_report,
        sampler_contract_path,
    )
    sampler_metadata_path = out / "sampler_contracts.meta.json"
    sampler_metadata = None
    if texture_report is not None and texture_path is not None:
        sampler_metadata = write_sampler_metadata(
            sampler_report,
            texture_path,
            sampler_metadata_path,
        )

    gate_path = out / "native_submission_gate.json"
    _write(gate_path, native_gate)
    runtime_gate_path = out / "runtime_provenance_gate.json"
    _write(runtime_gate_path, runtime_gate)

    pipeline_state = translate_bmt_pipeline_state(
        selected_submesh.get("render_state") or {}
    )
    pipeline_state_path = out / "pipeline_state.json"
    _write(pipeline_state_path, pipeline_state)

    world_matrix = selected_command.get("world_matrix")
    world_transform_report = None
    world_transform_path: Path | None = None
    world_transform_error: str | None = None
    if world_matrix is not None:
        world_transform_path = out / "world_transform.svwt"
        try:
            world_transform_report = build_vulkan_world_transform_packet(
                {"world_matrix": world_matrix},
                world_transform_path,
            )
        except (TypeError, ValueError) as error:
            world_transform_error = type(error).__name__
            world_transform_path = None

    artifacts = {
        "runtime_provenance_gate": {
            "path": str(runtime_gate_path.relative_to(out)),
            "sha256": _hash(runtime_gate_path),
            "ready": bool(runtime_gate.get("ready")),
        },
        "native_submission_gate": {
            "path": str(gate_path.relative_to(out)),
            "sha256": _hash(gate_path),
            "ready": bool(native_gate.get("ready")),
        },
        "pipeline_state": {
            "path": str(pipeline_state_path.relative_to(out)),
            "sha256": _hash(pipeline_state_path),
            "ready": bool(pipeline_state.get("ready")),
            "blocking_reasons": (
                pipeline_state.get("blocking_reasons") or []
            ),
            "state_format": pipeline_state.get("format"),
            "vulkan": pipeline_state.get("vulkan"),
        },
        "geometry": {
            "path": str(geometry_path.relative_to(out)),
            "sha256": _hash(geometry_path),
            "ready": True,
            "source_mesh_format": mesh_provenance.get("mesh_format"),
        },
        "world_transform": (
            None
            if world_transform_report is None or world_transform_path is None
            else {
                "path": str(world_transform_path.relative_to(out)),
                "sha256": _hash(world_transform_path),
                "ready": True,
                "format": world_transform_report.get("format"),
                "translation_xyz": world_transform_report.get(
                    "translation_xyz"
                ),
            }
        ),
        "constants": {
            "path": str(constants_path.relative_to(out)),
            "sha256": _hash(constants_path),
            "ready": bool(constants.get("ready")),
            "blocking_reasons": constants.get("blocking_reasons") or [],
        },
        "textures": (
            None
            if texture_report is None or texture_path is None
            else {
                "path": str(texture_path.relative_to(out)),
                "sha256": _hash(texture_path),
                "ready": True,
                "texture_count": texture_report.get("texture_count"),
            }
        ),
        "environment_cube": (
            None
            if cube_report is None or cube_path is None
            else {
                "path": str(cube_path.relative_to(out)),
                "sha256": _hash(cube_path),
                "ready": True,
                "register": 3,
            }
        ),
        "shaders": shader_rows,
        "sampler_contracts": {
            "path": str(sampler_contract_path.relative_to(out)),
            "sha256": _hash(sampler_contract_path),
            "ready": bool(sampler_report.get("ready")),
            "blocking_reasons": (
                sampler_report.get("blocking_reasons") or []
            ),
            "metadata_path": (
                str(sampler_metadata_path.relative_to(out))
                if sampler_metadata is not None
                else None
            ),
            "metadata_sha256": (
                sampler_metadata.get("sha256")
                if sampler_metadata is not None
                else None
            ),
        },
    }

    blockers = list(constants.get("blocking_reasons") or [])
    blockers.extend(pipeline_state.get("blocking_reasons") or [])
    blockers.extend(sampler_report.get("blocking_reasons") or [])
    if world_transform_error is not None:
        blockers.append(
            "vulkan-draw-bundle:world-transform-packet-invalid:"
            + world_transform_error
        )
    if textures is None and selected_submesh.get("textures"):
        blockers.append("vulkan-draw-bundle:material-textures-not-supplied")
    if has_s3_cube and environment_cube is None:
        blockers.append("vulkan-draw-bundle:environment-cube-not-supplied")

    transform_status = (
        "identity-or-none"
        if world_matrix is None
        else "packet-invalid"
        if world_transform_report is None
        else "packet-emitted-not-executed"
    )

    _mapped_registers(external_textures)
    packet_external_registers = {
        int(row.get("register"))
        for row in (
            (texture_report or {}).get("textures") or []
        )
        if row.get("source_kind") == "external"
    }

    external = [
        {
            "sampler": row.get("sampler"),
            "sampler_type": row.get("sampler_type"),
            "d3d9_sampler_register": row.get(
                "d3d9_sampler_register",
                row.get("slot"),
            ),
            "status": (
                "provided-to-vulkan-texture-packet"
                if (
                    str(row.get("sampler_type") or "") == "sampler2D"
                    and int(
                        row.get(
                            "d3d9_sampler_register",
                            row.get("slot", -1),
                        )
                    ) in packet_external_registers
                )
                else "provided-to-vulkan-cube-packet"
                if (
                    str(row.get("sampler_type") or "") == "samplerCube"
                    and int(
                        row.get(
                            "d3d9_sampler_register",
                            row.get("slot", -1),
                        )
                    ) == 3
                    and cube_report is not None
                )
                else "requires-runtime-resource"
            ),
        }
        for row in (selected_submesh.get("external_samplers") or [])
    ]

    report = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not blockers else "partial",
        "ready": not blockers,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "source": {
            "render_command_format": input_format,
            "command_index": command_index,
            "submesh_index": submesh_index,
            "mesh_ref": (selected_command.get("mesh") or {}).get("ref"),
            "mesh_provenance": mesh_provenance,
        },
        "target": {
            "vertex_count": (
                selected_command.get("mesh") or {}
            ).get("vertex_count"),
            "triangle_count": (
                selected_command.get("mesh") or {}
            ).get("triangle_count"),
        },
        "runtime_provenance_gate": runtime_gate,
        "native_submission_gate": native_gate,
        "scene_transform": {
            "world_matrix": world_matrix,
            "execution_status": transform_status,
            "blocking_for_scene_native_submission": world_matrix is not None,
            "packet": (
                None
                if world_transform_report is None or world_transform_path is None
                else {
                    "format": world_transform_report.get("format"),
                    "path": str(world_transform_path.relative_to(out)),
                    "sha256": _hash(world_transform_path),
                    "translation_xyz": world_transform_report.get(
                        "translation_xyz"
                    ),
                }
            ),
            "reason": (
                "world transform is serialized for native consumption but "
                "the material Vulkan path has not consumed SVWT yet"
                if world_transform_report is not None
                else "world transform could not be serialized"
                if world_matrix is not None
                else None
            ),
        },
        "artifacts": artifacts,
        "external_samplers": external,
        "native_execution": {
            "status": "not-run",
            "reason": (
                "atomic bundle preparation does not claim a native render "
                "or scene-transform execution"
            ),
        },
        "boundary": {
            "neutral_mesh_container_equivalence": False,
            "runtime_provenance_required": require_runtime_provenance,
            "scene_world_transform_serialized": (
                world_matrix is None or world_transform_report is not None
            ),
            "scene_world_transform_executed": False,
            "retail_world_constant_register_assigned": False,
            "preserves_bmw_bundle_abi": True,
            "external_2d_snapshot_registers": sorted(
                packet_external_registers
            ),
            "external_2d_snapshot_count": len(
                packet_external_registers
            ),
        },
    }
    _write(out / "bundle_manifest.json", report)
    report["manifest_sha256"] = _hash(out / "bundle_manifest.json")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare one SHIFT.VulkanDrawBundle/1"
    )
    parser.add_argument("render_command")
    parser.add_argument("mesh")
    parser.add_argument("output_dir")
    parser.add_argument("--textures")
    parser.add_argument(
        "--external-textures",
        help=(
            "optional JSON mapping explicit external sampler2D registers "
            "to ReferenceTexture/1 snapshots"
        ),
    )
    parser.add_argument("--environment-cube")
    parser.add_argument("--command-index", type=int, default=0)
    parser.add_argument("--submesh-index", type=int, default=0)
    parser.add_argument(
        "--allow-static",
        action="store_true",
        help="do not require SHIFT.RuntimeProvenDraw/1",
    )
    args = parser.parse_args(argv)
    result = build_vulkan_draw_bundle(
        args.render_command,
        args.mesh,
        args.output_dir,
        textures=args.textures,
        external_textures=args.external_textures,
        environment_cube=args.environment_cube,
        command_index=args.command_index,
        submesh_index=args.submesh_index,
        require_runtime_provenance=not args.allow_static,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
