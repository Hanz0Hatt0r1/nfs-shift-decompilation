"""Build an ordered Vulkan child-bundle set from NativeSceneBundle/1.

Phase 580 resolves each runtime-proven Silverstone IMB draw back through the
extracted IR, reconstructs the exact IMB neutral geometry, resolves ordinary
material DDS resources, builds one SHIFT.VulkanDrawBundle/1 per scene draw, and
revalidates every child against the Phase 578 scene hashes.

The set remains distinct from native scene execution. SGB world transforms are
transported independently through SVWT. Renderer-owned samplers are never
invented; Phase 589 may satisfy an external sampler2D only from an exact
provenance-bearing scene snapshot contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from imb_neutral_geometry import build_imb_neutral_geometry
from native_scene_external_sampler_cube_snapshots import (
    FORMAT as EXTERNAL_CUBE_SNAPSHOT_FORMAT,
    resolve_draw_external_sampler_cube_snapshot,
    validate_external_sampler_cube_snapshot_contract,
)
from native_scene_external_sampler_snapshots import (
    FORMAT as EXTERNAL_SNAPSHOT_FORMAT,
    resolve_draw_external_sampler2d_snapshots,
    validate_external_sampler_snapshot_contract,
)
from texture_reference import CUBE_FORMAT, FORMAT as TEXTURE_FORMAT, decode_dds
from vulkan_draw_bundle import build_vulkan_draw_bundle

FORMAT = "SHIFT.NativeSceneVulkanSet/1"
SCENE_FORMAT = "SHIFT.NativeSceneBundle/1"
BRIDGE_FORMAT = "SHIFT.SGBRenderBindingBridge/1"


def _load(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha_json(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _world_matrix(value: Any) -> list[float] | None:
    if (
        isinstance(value, list)
        and len(value) == 4
        and all(isinstance(row, list) and len(row) == 4 for row in value)
    ):
        value = [item for row in value for item in row]
    if not isinstance(value, list) or len(value) != 16:
        return None
    result: list[float] = []
    for item in value:
        if not isinstance(item, (int, float)):
            return None
        result.append(float(item))
    return result


def _manifest_rows(root: Path) -> list[dict[str, Any]]:
    value = _load(root / "manifest.json")
    if not isinstance(value, list):
        raise ValueError("IR manifest.json must be a JSON array")
    return [
        dict(row)
        for row in value
        if isinstance(row, Mapping) and "error" not in row
    ]


def _exact_row(
    rows: list[dict[str, Any]],
    *,
    path: Any,
    archive: Any = None,
    sha256: Any = None,
) -> tuple[dict[str, Any] | None, str | None]:
    target = _norm(path)
    hits = [row for row in rows if _norm(row.get("path")) == target]
    if archive:
        hits = [
            row for row in hits
            if str(row.get("archive") or "") == str(archive)
        ]
    if sha256:
        expected = str(sha256).lower()
        hits = [
            row for row in hits
            if str(row.get("sha256") or "").lower() == expected
        ]
    if len(hits) == 1:
        return hits[0], None
    if not hits:
        return None, "not-found"
    return None, f"ambiguous:{len(hits)}"


def _raw_path(root: Path, row: Mapping[str, Any]) -> Path | None:
    raw = row.get("raw")
    if not raw:
        return None
    path = root / str(raw)
    return path if path.is_file() else None


def _shader_identity(submesh: Mapping[str, Any]) -> dict[str, Any]:
    shader = submesh.get("shader") or {}
    permutation = shader.get("permutation_identity") or {}
    return {
        "source_payload_sha256": shader.get("source_payload_sha256"),
        "pair_sha256": shader.get("pair_sha256"),
        "vertex_sha256": shader.get("vertex_sha256"),
        "pixel_sha256": shader.get("pixel_sha256"),
        "permutation_identity_sha256": (
            permutation.get("identity_sha256")
            if isinstance(permutation, Mapping)
            else None
        ),
    }


def _verify_scene_draw(
    draw: Mapping[str, Any],
    command: Mapping[str, Any],
    submesh: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    hashes = draw.get("hashes") or {}
    if _sha_json(command) != hashes.get("render_command_sha256"):
        reasons.append("scene-hash:render-command-mismatch")
    if _sha_json(submesh) != hashes.get("submesh_sha256"):
        reasons.append("scene-hash:submesh-mismatch")
    provenance = submesh.get("runtime_provenance")
    if _sha_json(provenance) != hashes.get("runtime_provenance_sha256"):
        reasons.append("scene-hash:runtime-provenance-mismatch")

    world = _world_matrix(command.get("world_matrix"))
    if world is None:
        reasons.append("scene-hash:world-matrix-invalid")
    else:
        if _sha_json(world) != hashes.get("world_matrix_sha256"):
            reasons.append("scene-hash:world-matrix-mismatch")
        if world != _world_matrix(draw.get("world_matrix")):
            reasons.append("scene-hash:world-matrix-value-mismatch")

    if _shader_identity(submesh) != draw.get("shader_identity"):
        reasons.append("scene-hash:shader-identity-mismatch")

    draw_identity = {
        "resource": draw.get("resource"),
        "primitive_index": draw.get("primitive_index"),
        "draw_range": draw.get("draw_range"),
        "shader_identity": draw.get("shader_identity"),
        "world_matrix": draw.get("world_matrix"),
    }
    if _sha_json(draw_identity) != hashes.get("draw_identity_sha256"):
        reasons.append("scene-hash:draw-identity-mismatch")

    provenance = provenance if isinstance(provenance, Mapping) else {}
    resource = provenance.get("resource") or {}
    if _norm(resource.get("path")) != _norm(
        (draw.get("resource") or {}).get("path")
    ):
        reasons.append("scene-identity:resource-path-mismatch")
    if str(resource.get("sha256") or "").lower() != str(
        (draw.get("resource") or {}).get("sha256") or ""
    ).lower():
        reasons.append("scene-identity:resource-sha256-mismatch")
    if provenance.get("primitive_index") != draw.get("primitive_index"):
        reasons.append("scene-identity:primitive-index-mismatch")
    if provenance.get("draw_range") != draw.get("draw_range"):
        reasons.append("scene-identity:draw-range-mismatch")
    if provenance.get("binding_index") != draw.get("binding_index"):
        reasons.append("scene-identity:binding-index-mismatch")
    return list(dict.fromkeys(reasons))


def _primitive_matches(
    neutral: Mapping[str, Any],
    draw: Mapping[str, Any],
) -> bool:
    try:
        primitive_index = int(draw.get("primitive_index"))
    except (TypeError, ValueError):
        return False
    primitives = [
        row
        for row in (neutral.get("primitives") or [])
        if isinstance(row, Mapping)
    ]
    matches = [
        row
        for row in primitives
        if row.get("index") == primitive_index
    ]
    if len(matches) != 1:
        return False
    primitive = matches[0]
    draw_range = draw.get("draw_range") or {}
    try:
        return (
            int(primitive.get("first_index"))
            == int(draw_range.get("first_index"))
            and int(primitive.get("index_count"))
            == int(draw_range.get("index_count"))
            and int(primitive.get("triangle_count"))
            == int(draw_range.get("primitive_count"))
        )
    except (TypeError, ValueError):
        return False


def _texture_map_for_submesh(
    *,
    root: Path,
    rows: list[dict[str, Any]],
    render_binding: Mapping[str, Any],
    submesh: Mapping[str, Any],
    prefer_archive: Any,
) -> tuple[dict[int, dict[str, Any]], list[str], list[dict[str, Any]]]:
    resources = render_binding.get("resources") or {}
    texture_rows = {
        str(row.get("id")): row
        for row in (resources.get("textures") or [])
        if isinstance(row, Mapping) and row.get("id")
    }
    decoded: dict[int, dict[str, Any]] = {}
    blockers: list[str] = []
    sources: list[dict[str, Any]] = []

    for texture in submesh.get("textures") or []:
        if not isinstance(texture, Mapping):
            blockers.append("texture:invalid-command-row")
            continue
        if texture.get("resource") == "external":
            continue
        try:
            register = int(texture.get("d3d9_sampler_register"))
        except (TypeError, ValueError):
            blockers.append("texture:sampler-register-invalid")
            continue
        texture_id = str(texture.get("texture_id") or "")
        resource = texture_rows.get(texture_id)
        if resource is None:
            blockers.append(
                f"texture:s{register}:renderer-resource-not-found"
            )
            continue
        path = resource.get("path")
        expected_sha256 = str(resource.get("sha256") or "").lower()
        if len(expected_sha256) != 64:
            blockers.append(
                f"texture:s{register}:renderer-resource-sha256-invalid"
            )
            continue
        row, error = _exact_row(
            rows,
            path=path,
            archive=prefer_archive,
            sha256=expected_sha256,
        )
        if row is None and error == "not-found":
            row, error = _exact_row(
                rows,
                path=path,
                sha256=expected_sha256,
            )
        if row is None:
            path_hits = [
                candidate
                for candidate in rows
                if _norm(candidate.get("path")) == _norm(path)
            ]
            if error == "not-found" and path_hits:
                blockers.append(
                    f"texture:s{register}:ir-resource-sha256-mismatch"
                )
            else:
                blockers.append(
                    f"texture:s{register}:ir-resource-{error or 'not-found'}"
                )
            continue
        raw = _raw_path(root, row)
        if raw is None:
            blockers.append(f"texture:s{register}:raw-payload-missing")
            continue
        manifest_decoded_sha256 = str(
            row.get("decoded_sha256") or ""
        ).lower()
        raw_sha256 = _sha_file(raw)
        if manifest_decoded_sha256:
            if manifest_decoded_sha256 != expected_sha256:
                blockers.append(
                    f"texture:s{register}:ir-decoded-sha256-mismatch"
                )
                continue
            if raw_sha256 != manifest_decoded_sha256:
                blockers.append(
                    f"texture:s{register}:raw-payload-sha256-mismatch"
                )
                continue
        try:
            image = decode_dds(raw.read_bytes())
        except (OSError, ValueError, TypeError) as exc:
            blockers.append(
                f"texture:s{register}:decode-failed:{type(exc).__name__}"
            )
            continue
        if image.get("format") != TEXTURE_FORMAT:
            blockers.append(f"texture:s{register}:not-2d-texture")
            continue
        if register in decoded:
            blockers.append(f"texture:s{register}:duplicate-register")
            continue
        decoded[register] = image
        sources.append({
            "register": register,
            "texture_id": texture_id,
            "path": row.get("path"),
            "archive": row.get("archive"),
            "sha256": row.get("sha256"),
            "expected_sha256": expected_sha256,
            "identity_sha256_match": (
                str(row.get("sha256") or "").lower() == expected_sha256
            ),
            "decoded_sha256": row.get("decoded_sha256"),
            "raw": row.get("raw"),
            "raw_sha256": raw_sha256,
            "raw_identity_sha256_match": (
                raw_sha256 == manifest_decoded_sha256
                if manifest_decoded_sha256
                else None
            ),
        })

    return decoded, list(dict.fromkeys(blockers)), sources


def _external_sampler_blockers(
    submesh: Mapping[str, Any],
    *,
    environment_cube_ready: bool,
    external_2d_ready: set[int] | None = None,
) -> list[str]:
    blockers: list[str] = []
    ready_2d = external_2d_ready or set()
    for row in submesh.get("external_samplers") or []:
        if not isinstance(row, Mapping):
            blockers.append("external-sampler:invalid-row")
            continue
        register = row.get("d3d9_sampler_register", row.get("slot"))
        sampler_type = str(row.get("sampler_type") or "")
        try:
            register_int = int(register)
        except (TypeError, ValueError):
            register_int = -1
        if sampler_type == "sampler2D" and register_int in ready_2d:
            continue
        if (
            sampler_type == "samplerCube"
            and register_int == 3
            and environment_cube_ready
        ):
            continue
        blockers.append(
            "external-sampler:runtime-resource-unresolved:"
            f"s{register_int}:{sampler_type or 'unknown'}"
        )
    return blockers


def build_native_scene_vulkan_set(
    scene_bundle: Mapping[str, Any],
    scene_bridge: Mapping[str, Any],
    ir_root: str | Path,
    output_dir: str | Path,
    *,
    environment_cube_dds: str | Path | None = None,
    external_sampler_snapshots: Mapping[str, Any] | None = None,
    external_sampler_cube_snapshots: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if scene_bundle.get("format") != SCENE_FORMAT:
        raise ValueError("scene bundle must be SHIFT.NativeSceneBundle/1")
    if scene_bridge.get("format") != BRIDGE_FORMAT:
        raise ValueError(
            "scene bridge must be SHIFT.SGBRenderBindingBridge/1"
        )

    root = Path(ir_root)
    rows = _manifest_rows(root)
    render_binding = scene_bridge.get("render_binding") or {}
    commands = [
        row for row in (render_binding.get("render_commands") or [])
        if isinstance(row, Mapping)
    ]
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[str] = []
    native_blockers: list[str] = []
    snapshot_contract = validate_external_sampler_snapshot_contract(
        external_sampler_snapshots
    )
    cube_snapshot_contract = (
        validate_external_sampler_cube_snapshot_contract(
            external_sampler_cube_snapshots
        )
    )
    if snapshot_contract.get("ready") is not True:
        blockers.extend(
            str(reason)
            for reason in snapshot_contract.get("blocking_reasons") or []
        )
    if cube_snapshot_contract.get("ready") is not True:
        blockers.extend(
            str(reason)
            for reason in (
                cube_snapshot_contract.get("blocking_reasons") or []
            )
        )
    if (
        environment_cube_dds is not None
        and int(cube_snapshot_contract.get("snapshot_count") or 0) > 0
    ):
        blockers.append(
            "environment-cube:global-dds-conflicts-with-scene-snapshots"
        )
    if scene_bundle.get("ready") is not True:
        blockers.append("native-scene-bundle:not-ready")
    if scene_bridge.get("ready") is not True:
        blockers.append("scene-bridge:not-ready")
    if render_binding.get("format") != "SHIFT.RenderBinding/1":
        blockers.append("render-binding:invalid-format")

    environment_cube = None
    if environment_cube_dds is not None:
        try:
            environment_cube = decode_dds(
                Path(environment_cube_dds).read_bytes()
            )
        except (OSError, ValueError, TypeError) as exc:
            blockers.append(
                "environment-cube:decode-failed:"
                + type(exc).__name__
            )
        else:
            if environment_cube.get("format") != CUBE_FORMAT:
                blockers.append("environment-cube:not-cubemap")
                environment_cube = None

    child_rows: list[dict[str, Any]] = []
    draw_rows = sorted(
        [
            row for row in (scene_bundle.get("draws") or [])
            if isinstance(row, Mapping)
        ],
        key=lambda row: int(row.get("draw_order", -1)),
    )

    for expected_order, draw in enumerate(draw_rows):
        child_blockers: list[str] = []
        try:
            draw_order = int(draw.get("draw_order"))
            command_index = int(draw.get("command_index"))
            submesh_index = int(draw.get("submesh_index"))
        except (TypeError, ValueError):
            child_rows.append({
                "draw_order": draw.get("draw_order"),
                "status": "blocked",
                "ready": False,
                "blocking_reasons": ["scene-draw:index-invalid"],
            })
            blockers.append("scene-draw:index-invalid")
            continue
        if draw_order != expected_order:
            child_blockers.append("scene-draw:order-not-contiguous")
        if command_index < 0 or command_index >= len(commands):
            child_blockers.append("scene-draw:command-index-out-of-range")
            command = None
            submesh = None
        else:
            command = commands[command_index]
            submeshes = command.get("submeshes") or []
            if submesh_index < 0 or submesh_index >= len(submeshes):
                child_blockers.append(
                    "scene-draw:submesh-index-out-of-range"
                )
                submesh = None
            else:
                submesh = submeshes[submesh_index]
                if not isinstance(submesh, Mapping):
                    child_blockers.append("scene-draw:submesh-invalid")
                    submesh = None

        if command is not None and submesh is not None:
            child_blockers.extend(
                _verify_scene_draw(draw, command, submesh)
            )

        resource = draw.get("resource") or {}
        resource_row = None
        if not child_blockers:
            resource_row, error = _exact_row(
                rows,
                path=resource.get("path"),
                archive=resource.get("archive"),
                sha256=resource.get("sha256"),
            )
            if resource_row is None:
                child_blockers.append(
                    "imb-resource:" + (error or "not-found")
                )

        neutral = None
        if resource_row is not None:
            raw = _raw_path(root, resource_row)
            if raw is None:
                child_blockers.append("imb-resource:raw-payload-missing")
            else:
                try:
                    neutral = build_imb_neutral_geometry(
                        raw.read_bytes()
                    )
                except (OSError, ValueError, TypeError) as exc:
                    child_blockers.append(
                        "imb-resource:neutral-decode-failed:"
                        + type(exc).__name__
                    )
                else:
                    if neutral.get("ready") is not True:
                        child_blockers.extend(
                            "imb-resource:" + str(reason)
                            for reason in (
                                neutral.get("blocking_reasons") or []
                            )
                        )
                    if not _primitive_matches(neutral, draw):
                        child_blockers.append(
                            "imb-resource:primitive-range-mismatch"
                        )

        texture_map: dict[int, dict[str, Any]] = {}
        texture_sources: list[dict[str, Any]] = []
        if (
            command is not None
            and submesh is not None
            and resource_row is not None
            and not child_blockers
        ):
            texture_map, texture_blockers, texture_sources = (
                _texture_map_for_submesh(
                    root=root,
                    rows=rows,
                    render_binding=render_binding,
                    submesh=submesh,
                    prefer_archive=resource_row.get("archive"),
                )
            )
            child_blockers.extend(texture_blockers)

        external_textures: dict[int, dict[str, Any]] = {}
        external_texture_sources: list[dict[str, Any]] = []
        external_cube = None
        external_cube_source = None
        if submesh is not None and not child_blockers:
            (
                external_textures,
                snapshot_blockers,
                external_texture_sources,
            ) = resolve_draw_external_sampler2d_snapshots(
                snapshot_contract,
                draw,
                submesh,
            )
            child_blockers.extend(snapshot_blockers)
            (
                external_cube,
                cube_snapshot_blockers,
                external_cube_source,
            ) = resolve_draw_external_sampler_cube_snapshot(
                cube_snapshot_contract,
                draw,
                submesh,
            )
            child_blockers.extend(cube_snapshot_blockers)

        selected_environment_cube = (
            external_cube
            if external_cube is not None
            else environment_cube
        )
        external_blockers: list[str] = []
        if submesh is not None:
            external_blockers = _external_sampler_blockers(
                submesh,
                environment_cube_ready=(
                    selected_environment_cube is not None
                ),
                external_2d_ready=set(external_textures),
            )
            native_blockers.extend(
                f"draw-{draw_order}:{reason}"
                for reason in external_blockers
            )

        child_dir = out / f"draw_{draw_order:04d}"
        child_report = None
        if (
            command is not None
            and submesh is not None
            and neutral is not None
            and not child_blockers
        ):
            try:
                child_report = build_vulkan_draw_bundle(
                    command,
                    neutral,
                    child_dir,
                    textures=(
                        texture_map
                        if submesh.get("textures")
                        else None
                    ),
                    environment_cube=selected_environment_cube,
                    external_textures=(
                        external_textures
                        if external_textures
                        else None
                    ),
                    submesh_index=submesh_index,
                    require_runtime_provenance=True,
                )
            except (OSError, ValueError, TypeError) as exc:
                child_blockers.append(
                    "vulkan-draw-bundle:build-failed:"
                    + type(exc).__name__
                )
            else:
                if child_report.get("ready") is not True:
                    child_blockers.extend(
                        str(reason)
                        for reason in (
                            child_report.get("blocking_reasons") or []
                        )
                    )

        if child_report is not None:
            transform = child_report.get("scene_transform") or {}
            if transform.get("blocking_for_scene_native_submission") is True:
                native_blockers.append(
                    f"draw-{draw_order}:scene-world-transform-not-executed"
                )

        child_ready = child_report is not None and not child_blockers
        if not child_ready:
            blockers.extend(
                f"draw-{draw_order}:{reason}"
                for reason in child_blockers
            )

        manifest_path = child_dir / "bundle_manifest.json"
        child_rows.append({
            "draw_order": draw_order,
            "command_index": command_index,
            "submesh_index": submesh_index,
            "binding_index": draw.get("binding_index"),
            "status": "ready" if child_ready else "blocked",
            "ready": child_ready,
            "blocking_reasons": list(dict.fromkeys(child_blockers)),
            "scene_draw_identity_sha256": (
                (draw.get("hashes") or {}).get("draw_identity_sha256")
            ),
            "resource": dict(resource) if isinstance(resource, Mapping) else {},
            "texture_sources": texture_sources,
            "external_texture_sources": external_texture_sources,
            "external_cube_source": external_cube_source,
            "external_runtime_blocking_reasons": external_blockers,
            "bundle": (
                None
                if child_report is None
                else {
                    "format": child_report.get("format"),
                    "manifest_path": str(
                        manifest_path.relative_to(out)
                    ),
                    "manifest_sha256": (
                        _sha_file(manifest_path)
                        if manifest_path.is_file()
                        else None
                    ),
                    "report_manifest_sha256": child_report.get(
                        "manifest_sha256"
                    ),
                    "geometry_sha256": (
                        (child_report.get("artifacts") or {})
                        .get("geometry", {})
                        .get("sha256")
                    ),
                    "world_transform": (
                        (child_report.get("artifacts") or {})
                        .get("world_transform")
                    ),
                    "world_transform_serialized": (
                        (child_report.get("boundary") or {})
                        .get("scene_world_transform_serialized")
                        is True
                    ),
                    "runtime_provenance_gate_ready": (
                        (child_report.get("runtime_provenance_gate") or {})
                        .get("ready")
                        is True
                    ),
                }
            ),
        })

    blockers = list(dict.fromkeys(blockers))
    native_blockers = list(dict.fromkeys(native_blockers))
    ready_children = sum(row.get("ready") is True for row in child_rows)
    ready = (
        bool(child_rows)
        and ready_children == len(child_rows)
        and not blockers
    )
    native_scene_submission_ready = (
        ready and not native_blockers
    )

    report = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "draw_count": len(child_rows),
        "ready_draw_count": ready_children,
        "draws": child_rows,
        "native_scene_submission": {
            "ready": native_scene_submission_ready,
            "blocking_reasons": native_blockers,
            "world_transform_execution": (
                "required-before-native-scene-submit"
            ),
            "external_runtime_resources": (
                "must-be-explicitly-bound"
            ),
        },
        "source": {
            "native_scene_bundle_format": scene_bundle.get("format"),
            "native_scene_bundle_ready": scene_bundle.get("ready") is True,
            "scene_bridge_format": scene_bridge.get("format"),
            "scene_bridge_ready": scene_bridge.get("ready") is True,
            "ir_root": str(root),
            "external_sampler_snapshot_format": (
                EXTERNAL_SNAPSHOT_FORMAT
                if external_sampler_snapshots is not None
                else None
            ),
            "external_sampler_snapshot_count": int(
                snapshot_contract.get("snapshot_count") or 0
            ),
            "external_sampler_cube_snapshot_format": (
                EXTERNAL_CUBE_SNAPSHOT_FORMAT
                if external_sampler_cube_snapshots is not None
                else None
            ),
            "external_sampler_cube_snapshot_count": int(
                cube_snapshot_contract.get("snapshot_count") or 0
            ),
        },
        "boundary": {
            "draw_order_preserved": True,
            "bundle_paths_relative_to_set_root": True,
            "exact_imb_resource_revalidated": True,
            "exact_primitive_range_revalidated": True,
            "scene_hashes_revalidated": True,
            "material_2d_dds_resolved_from_ir": True,
            "material_2d_dds_render_resource_sha256_revalidated": True,
            "material_2d_dds_explicit_decoded_sha256_revalidated": True,
            "material_2d_dds_raw_payload_sha256_revalidated_when_explicit": True,
            "world_transform_serialized": True,
            "world_transform_executed": False,
            "explicit_external_sampler2d_snapshots_admitted": True,
            "explicit_external_samplercube_s3_snapshots_admitted": True,
            "external_samplercube_register_policy": "s3-only",
            "unresolved_external_samplers_promoted": False,
            "next_stage": (
                "prepare the ordered neutral children through the native "
                "SPIR-V/interface/provenance gates before native_runtime"
            ),
        },
    }
    manifest = out / "bundle_set_manifest.json"
    manifest.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    report["manifest_sha256"] = _sha_file(manifest)

    paths_file = out / "bundle_set.paths"
    paths_file.write_text(
        "".join(
            Path(str(row["bundle"]["manifest_path"])).parent.as_posix()
            + "\n"
            for row in child_rows
            if row.get("ready") is True
            and isinstance(row.get("bundle"), Mapping)
        ),
        encoding="utf-8",
    )
    report["paths_file"] = str(paths_file)
    report["paths_sha256"] = _sha_file(paths_file)
    return report


def validate_files(
    native_scene_bundle_path: str | Path,
    scene_bridge_path: str | Path,
    ir_root: str | Path,
    output_dir: str | Path,
    *,
    environment_cube_dds: str | Path | None = None,
    external_sampler_snapshots_path: str | Path | None = None,
    external_sampler_cube_snapshots_path: str | Path | None = None,
) -> dict[str, Any]:
    scene_bundle = _load(native_scene_bundle_path)
    scene_bridge = _load(scene_bridge_path)
    if not isinstance(scene_bundle, Mapping):
        raise ValueError("native scene bundle JSON must be an object")
    if not isinstance(scene_bridge, Mapping):
        raise ValueError("scene bridge JSON must be an object")
    external_sampler_snapshots = (
        _load(external_sampler_snapshots_path)
        if external_sampler_snapshots_path is not None
        else None
    )
    if (
        external_sampler_snapshots is not None
        and not isinstance(external_sampler_snapshots, Mapping)
    ):
        raise ValueError(
            "external sampler snapshots JSON must be an object"
        )
    external_sampler_cube_snapshots = (
        _load(external_sampler_cube_snapshots_path)
        if external_sampler_cube_snapshots_path is not None
        else None
    )
    if (
        external_sampler_cube_snapshots is not None
        and not isinstance(external_sampler_cube_snapshots, Mapping)
    ):
        raise ValueError(
            "external sampler cube snapshots JSON must be an object"
        )
    return build_native_scene_vulkan_set(
        scene_bundle,
        scene_bridge,
        ir_root,
        output_dir,
        environment_cube_dds=environment_cube_dds,
        external_sampler_snapshots=external_sampler_snapshots,
        external_sampler_cube_snapshots=(
            external_sampler_cube_snapshots
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_scene_bundle")
    parser.add_argument("scene_bridge")
    parser.add_argument("ir_root")
    parser.add_argument("output_dir")
    parser.add_argument("--environment-cube-dds")
    parser.add_argument("--external-sampler-snapshots")
    parser.add_argument("--external-sampler-cube-snapshots")
    args = parser.parse_args(argv)
    report = validate_files(
        args.native_scene_bundle,
        args.scene_bridge,
        args.ir_root,
        args.output_dir,
        environment_cube_dds=args.environment_cube_dds,
        external_sampler_snapshots_path=(
            args.external_sampler_snapshots
        ),
        external_sampler_cube_snapshots_path=(
            args.external_sampler_cube_snapshots
        ),
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "draw_count": report["draw_count"],
        "ready_draw_count": report["ready_draw_count"],
        "native_scene_submission": report["native_scene_submission"],
        "blocking_reasons": report["blocking_reasons"],
        "manifest_sha256": report.get("manifest_sha256"),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
