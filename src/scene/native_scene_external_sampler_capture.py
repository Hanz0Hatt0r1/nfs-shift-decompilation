"""Convert attributed D3D9 texture captures into exact scene snapshots.

Phase 590 consumes draw-local texture observations that already support a
strong Phase 572 shader attribution and produces exact external sampler2D
snapshots. Phase 592 extends the same exact scene-identity join to the proven
samplerCube s3 boundary by requiring six named captured cube-face PPMs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping

from native_scene_external_sampler_cube_snapshots import (
    FORMAT as CUBE_SNAPSHOT_FORMAT,
    reference_cube_sha256,
    validate_external_sampler_cube_snapshot_contract,
)
from native_scene_external_sampler_snapshots import (
    FORMAT as SNAPSHOT_FORMAT,
    PROVENANCE_FORMAT,
    reference_texture_sha256,
    validate_external_sampler_snapshot_contract,
)
from runtime_texture_reference import (
    ppm_to_reference_texture,
    ppms_to_reference_cube,
)
from texture_reference import CUBE_FACES

FORMAT = "SHIFT.NativeSceneExternalSamplerCaptureAdapter/1"
SCENE_FORMAT = "SHIFT.NativeSceneBundle/1"
BRIDGE_FORMAT = "SHIFT.SGBRenderBindingBridge/1"
PIPELINE_FORMAT = "SHIFT.IMBRuntimeCapturePipeline/1"
INSTANCE_MATCH_FORMAT = "SHIFT.NativeSceneInstanceTransformMatch/1"


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_int(value: Any) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result


def _external_sampler2d_declarations(
    bridge: Mapping[str, Any],
    scene_draw: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    blockers: list[str] = []
    render_binding = bridge.get("render_binding")
    if not isinstance(render_binding, Mapping):
        return [], ["scene-external-capture:render-binding-missing"]
    commands = render_binding.get("render_commands")
    if not isinstance(commands, list):
        return [], ["scene-external-capture:render-commands-missing"]

    command_index = _safe_int(scene_draw.get("command_index"))
    submesh_index = _safe_int(scene_draw.get("submesh_index"))
    if command_index is None or not 0 <= command_index < len(commands):
        return [], ["scene-external-capture:command-index-invalid"]
    command = commands[command_index]
    if not isinstance(command, Mapping):
        return [], ["scene-external-capture:render-command-invalid"]
    submeshes = command.get("submeshes")
    if (
        not isinstance(submeshes, list)
        or submesh_index is None
        or not 0 <= submesh_index < len(submeshes)
    ):
        return [], ["scene-external-capture:submesh-index-invalid"]
    submesh = submeshes[submesh_index]
    if not isinstance(submesh, Mapping):
        return [], ["scene-external-capture:submesh-invalid"]

    result: list[dict[str, Any]] = []
    seen: set[int] = set()
    for raw in submesh.get("external_samplers") or []:
        if not isinstance(raw, Mapping):
            continue
        sampler_type = str(raw.get("sampler_type") or "")
        if sampler_type != "sampler2D":
            continue
        register = _safe_int(
            raw.get("d3d9_sampler_register", raw.get("slot"))
        )
        if register is None or not 0 <= register <= 15:
            blockers.append(
                "scene-external-capture:external-register-invalid"
            )
            continue
        if register in seen:
            blockers.append(
                f"scene-external-capture:duplicate-external-register:s{register}"
            )
            continue
        seen.add(register)
        result.append({
            "register": register,
            "sampler": raw.get("sampler") or raw.get("name"),
            "sampler_type": sampler_type,
        })
    return result, blockers


def _external_sampler_cube_declarations(
    bridge: Mapping[str, Any],
    scene_draw: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    blockers: list[str] = []
    render_binding = bridge.get("render_binding")
    if not isinstance(render_binding, Mapping):
        return [], ["scene-external-capture:render-binding-missing"]
    commands = render_binding.get("render_commands")
    if not isinstance(commands, list):
        return [], ["scene-external-capture:render-commands-missing"]

    command_index = _safe_int(scene_draw.get("command_index"))
    submesh_index = _safe_int(scene_draw.get("submesh_index"))
    if command_index is None or not 0 <= command_index < len(commands):
        return [], ["scene-external-capture:command-index-invalid"]
    command = commands[command_index]
    if not isinstance(command, Mapping):
        return [], ["scene-external-capture:render-command-invalid"]
    submeshes = command.get("submeshes")
    if (
        not isinstance(submeshes, list)
        or submesh_index is None
        or not 0 <= submesh_index < len(submeshes)
    ):
        return [], ["scene-external-capture:submesh-index-invalid"]
    submesh = submeshes[submesh_index]
    if not isinstance(submesh, Mapping):
        return [], ["scene-external-capture:submesh-invalid"]

    result: list[dict[str, Any]] = []
    for raw in submesh.get("external_samplers") or []:
        if not isinstance(raw, Mapping):
            continue
        if str(raw.get("sampler_type") or "") != "samplerCube":
            continue
        register = _safe_int(
            raw.get("d3d9_sampler_register", raw.get("slot"))
        )
        if register != 3:
            blockers.append(
                "scene-external-capture:external-cube-register-not-proven-s3"
            )
            continue
        result.append({
            "register": 3,
            "sampler": raw.get("sampler") or raw.get("name"),
            "sampler_type": "samplerCube",
        })
    if len(result) > 1:
        blockers.append(
            "scene-external-capture:duplicate-external-cube-s3"
        )
    return result, blockers


def _cube_face_name(raw_path: str) -> str | None:
    stem = PureWindowsPath(raw_path).stem.lower()
    for face in CUBE_FACES:
        if stem.endswith("_face_" + face):
            return face
    return None


def _matching_cube_rows(
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for observation in observations:
        if observation.get("status") != "observed":
            continue
        for binding in observation.get("active_texture_bindings") or []:
            if not isinstance(binding, Mapping):
                continue
            if _safe_int(binding.get("stage")) != 3:
                continue
            creation = binding.get("resource_creation")
            if (
                binding.get("resource_creation_status") != "observed"
                or not isinstance(creation, Mapping)
                or creation.get("resource_type") != "cube_texture"
            ):
                continue
            paths = [
                str(path)
                for path in (binding.get("snapshot_paths") or [])
                if isinstance(path, str) and path
            ]
            face_paths: dict[str, str] = {}
            invalid = False
            for path in paths:
                face = _cube_face_name(path)
                if face is None or face in face_paths:
                    invalid = True
                    break
                face_paths[face] = path
            if (
                binding.get("snapshot_status") != "captured"
                or invalid
                or len(paths) != len(CUBE_FACES)
                or set(face_paths) != set(CUBE_FACES)
            ):
                continue
            rows.append({
                "frame": observation.get("frame"),
                "draw_index": observation.get("draw_index"),
                "stage": 3,
                "texture_ptr": binding.get("texture_ptr"),
                "resource_creation": dict(creation),
                "snapshot_paths": face_paths,
            })
    return rows


def _cube_source_sha256(face_sources: Mapping[str, Mapping[str, Any]]) -> str:
    payload = {
        face: str(face_sources[face]["source_sha256"])
        for face in CUBE_FACES
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _pipeline_texture_observations(
    pipeline: Mapping[str, Any],
) -> dict[int, list[dict[str, Any]]]:
    by_binding: dict[int, list[dict[str, Any]]] = {}
    for resource in pipeline.get("resource_results") or []:
        if not isinstance(resource, Mapping):
            continue
        for row in resource.get("attributed_texture_observations") or []:
            if not isinstance(row, Mapping):
                continue
            binding_index = _safe_int(row.get("binding_index"))
            if binding_index is None:
                continue
            by_binding.setdefault(binding_index, []).append(dict(row))
    return by_binding


def _instance_match_index(
    value: Mapping[str, Any] | None,
) -> tuple[dict[int, Mapping[str, Any]], list[str]]:
    if value is None:
        return {}, []
    blockers: list[str] = []
    if value.get("format") != INSTANCE_MATCH_FORMAT:
        blockers.append(
            "scene-external-capture:instance-match-invalid-format"
        )
        return {}, blockers
    if value.get("version") != 1:
        blockers.append(
            "scene-external-capture:instance-match-version-invalid"
        )
    result: dict[int, Mapping[str, Any]] = {}
    for row in value.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        binding_index = _safe_int(row.get("binding_index"))
        if binding_index is None or row.get("ready") is not True:
            continue
        if binding_index in result:
            blockers.append(
                "scene-external-capture:instance-match-duplicate-binding:"
                + str(binding_index)
            )
            continue
        result[binding_index] = row
    return result, list(dict.fromkeys(blockers))


def _resolve_snapshot_path(
    raw_path: str,
    capture_root: Path,
) -> tuple[Path | None, str, list[str]]:
    """Resolve a captured PPM without basename search or archive-order fallback.

    The native launcher owns one exact portable layout: the JSONL is written to
    <OutputDir>/shift_d3d9_capture.jsonl and texture snapshots to
    <OutputDir>/textures/.  Therefore a copied Windows-absolute snapshot path may
    be relocated only when its immediate source parent is exactly ``textures``;
    the target is deterministically ``capture_root/textures/<filename>``.  No
    recursive basename lookup is permitted.
    """
    blockers: list[str] = []
    direct = Path(raw_path)
    if direct.is_absolute() and direct.is_file():
        return direct.resolve(), "absolute-existing", []

    windows_path = PureWindowsPath(raw_path)
    windows_absolute = windows_path.is_absolute()
    normalized = raw_path.replace("\\", "/")
    normalized_path = Path(normalized)
    posix_absolute = normalized_path.is_absolute()

    # Relative paths are already portable provenance.  Resolve the exact path
    # below the explicitly supplied launcher output root and reject traversal.
    if not windows_absolute and not posix_absolute:
        joined = (capture_root / normalized_path).resolve()
        try:
            joined.relative_to(capture_root.resolve())
        except ValueError:
            blockers.append("snapshot-path-escapes-capture-root")
        else:
            if joined.is_file():
                return joined, "capture-root-relative", []
            blockers.append("snapshot-path-not-found")
        return None, "unresolved", blockers

    # Cross-platform relocation is allowed only by the exact producer layout
    # established by tools/run_shift_capture.ps1.  This is a root relocation,
    # not a basename lookup: a non-launcher source parent is never searched.
    source_name = windows_path.name if windows_absolute else normalized_path.name
    source_parent = (
        windows_path.parent.name if windows_absolute else normalized_path.parent.name
    )
    if not source_name:
        return None, "unresolved", ["snapshot-path-name-missing"]
    if str(source_parent).casefold() != "textures":
        return None, "unresolved", ["snapshot-path-no-exact-relocation"]

    relocated = (capture_root / "textures" / source_name).resolve()
    try:
        relocated.relative_to(capture_root.resolve())
    except ValueError:
        return None, "unresolved", ["snapshot-path-escapes-capture-root"]
    if relocated.is_file():
        return relocated, "capture-launcher-textures-relative", []
    return None, "unresolved", ["snapshot-path-launcher-layout-not-found"]


def _matching_texture_rows(
    observations: list[dict[str, Any]],
    register: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for observation in observations:
        if observation.get("status") != "observed":
            continue
        for binding in observation.get("active_texture_bindings") or []:
            if not isinstance(binding, Mapping):
                continue
            if _safe_int(binding.get("stage")) != register:
                continue
            creation = binding.get("resource_creation")
            if (
                binding.get("resource_creation_status") != "observed"
                or not isinstance(creation, Mapping)
                or creation.get("resource_type") != "texture2d"
            ):
                continue
            paths = [
                str(path)
                for path in (binding.get("snapshot_paths") or [])
                if isinstance(path, str) and path
            ]
            if (
                binding.get("snapshot_status") != "captured"
                or len(paths) != 1
            ):
                continue
            rows.append({
                "frame": observation.get("frame"),
                "draw_index": observation.get("draw_index"),
                "stage": register,
                "texture_ptr": binding.get("texture_ptr"),
                "resource_creation": dict(creation),
                "snapshot_path": paths[0],
            })
    return rows


def build_scene_external_sampler_capture_adapter(
    scene_bundle: Mapping[str, Any],
    scene_bridge: Mapping[str, Any],
    capture_pipeline: Mapping[str, Any],
    *,
    capture_root: str | Path,
    instance_transform_match: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if scene_bundle.get("format") != SCENE_FORMAT:
        raise ValueError("scene input must be SHIFT.NativeSceneBundle/1")
    if scene_bridge.get("format") != BRIDGE_FORMAT:
        raise ValueError(
            f"bridge input must be {BRIDGE_FORMAT}"
        )
    if capture_pipeline.get("format") != PIPELINE_FORMAT:
        raise ValueError(
            f"capture input must be {PIPELINE_FORMAT}"
        )

    root = Path(capture_root)
    blockers: list[str] = []
    instance_match_by_binding, instance_match_blockers = (
        _instance_match_index(instance_transform_match)
    )
    blockers.extend(instance_match_blockers)
    if scene_bundle.get("ready") is not True:
        blockers.append("scene-external-capture:scene-bundle-not-ready")
    if scene_bridge.get("ready") is not True:
        blockers.append("scene-external-capture:scene-bridge-not-ready")
    if capture_pipeline.get("pipeline_ready") is not True:
        blockers.append("scene-external-capture:capture-pipeline-not-ready")
    pipeline_boundary = capture_pipeline.get("boundary")
    if (
        not isinstance(pipeline_boundary, Mapping)
        or pipeline_boundary.get(
            "attributed_texture_observation_contract"
        )
        != "selected-strong-variant-draw-textures-v1"
    ):
        blockers.append(
            "scene-external-capture:texture-observation-contract-missing"
        )
    if not root.is_dir():
        blockers.append("scene-external-capture:capture-root-not-directory")

    scene_by_binding: dict[int, list[Mapping[str, Any]]] = {}
    for draw in scene_bundle.get("draws") or []:
        if not isinstance(draw, Mapping):
            continue
        binding_index = _safe_int(draw.get("binding_index"))
        if binding_index is None:
            continue
        scene_by_binding.setdefault(binding_index, []).append(draw)

    texture_by_binding = _pipeline_texture_observations(capture_pipeline)
    snapshots: list[dict[str, Any]] = []
    cube_snapshots: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    cube_rows: list[dict[str, Any]] = []
    required_count = 0
    required_cube_count = 0

    for binding_index in sorted(scene_by_binding):
        draws = scene_by_binding[binding_index]
        external_decl_sets = []
        cube_decl_sets = []
        for draw in draws:
            declarations, declaration_blockers = (
                _external_sampler2d_declarations(scene_bridge, draw)
            )
            cube_declarations, cube_declaration_blockers = (
                _external_sampler_cube_declarations(scene_bridge, draw)
            )
            blockers.extend(
                f"scene-external-capture:binding-{binding_index}:{reason}"
                for reason in (
                    declaration_blockers + cube_declaration_blockers
                )
            )
            external_decl_sets.append(declarations)
            cube_decl_sets.append(cube_declarations)

        needs_external = any(external_decl_sets) or any(cube_decl_sets)
        if not needs_external:
            continue

        selected_instance_match = None
        if len(draws) == 1:
            draw = draws[0]
            declarations = external_decl_sets[0]
            cube_declarations = cube_decl_sets[0]
            required_count += len(declarations)
            required_cube_count += len(cube_declarations)
        else:
            match = instance_match_by_binding.get(binding_index)
            selected_order = (
                _safe_int(match.get("selected_draw_order"))
                if isinstance(match, Mapping)
                else None
            )
            matching_indices = [
                index
                for index, candidate in enumerate(draws)
                if _safe_int(candidate.get("draw_order")) == selected_order
            ]
            if len(matching_indices) != 1:
                required_count += sum(
                    len(declarations)
                    for declarations in external_decl_sets
                )
                required_cube_count += sum(
                    len(declarations)
                    for declarations in cube_decl_sets
                )
                blockers.append(
                    f"scene-external-capture:binding-{binding_index}:"
                    f"scene-draw-ambiguous:{len(draws)}"
                )
                continue
            selected_index = matching_indices[0]
            draw = draws[selected_index]
            draw_identity = (
                (draw.get("hashes") or {}).get(
                    "draw_identity_sha256"
                )
                if isinstance(draw.get("hashes"), Mapping)
                else None
            )
            expected_draw_identity = match.get(
                "selected_draw_identity_sha256"
            )
            if (
                not isinstance(expected_draw_identity, str)
                or draw_identity != expected_draw_identity
            ):
                required_count += sum(
                    len(declarations)
                    for declarations in external_decl_sets
                )
                required_cube_count += sum(
                    len(declarations)
                    for declarations in cube_decl_sets
                )
                blockers.append(
                    f"scene-external-capture:binding-{binding_index}:"
                    "instance-match-draw-identity-mismatch"
                )
                continue
            declarations = external_decl_sets[selected_index]
            cube_declarations = cube_decl_sets[selected_index]
            required_count += len(declarations)
            required_cube_count += len(cube_declarations)
            selected_instance_match = dict(match)

        observations = texture_by_binding.get(binding_index, [])
        for declaration in declarations:
            register = int(declaration["register"])
            candidates = _matching_texture_rows(
                observations,
                register,
            )
            row_blockers: list[str] = []
            if len(candidates) != 1:
                row_blockers.append(
                    f"capture-observation-count:{len(candidates)}"
                )
            snapshot_row = None
            if len(candidates) == 1 and root.is_dir():
                candidate = candidates[0]
                resolved, resolution, path_blockers = _resolve_snapshot_path(
                    candidate["snapshot_path"],
                    root,
                )
                row_blockers.extend(path_blockers)
                if resolved is not None and not path_blockers:
                    try:
                        texture = ppm_to_reference_texture(resolved)
                    except Exception as error:
                        row_blockers.append(
                            "snapshot-ppm-decode-failed:"
                            + type(error).__name__
                        )
                    else:
                        texture.pop("source_path", None)
                        source_sha = _sha256_bytes(resolved)
                        texture_sha = reference_texture_sha256(texture)
                        resource = draw.get("resource")
                        if not isinstance(resource, Mapping):
                            row_blockers.append(
                                "scene-resource-identity-missing"
                            )
                        else:
                            snapshot_row = {
                                "draw_identity_sha256": (
                                    (draw.get("hashes") or {}).get(
                                        "draw_identity_sha256"
                                    )
                                ),
                                "resource": {
                                    "archive": resource.get("archive"),
                                    "path": resource.get("path"),
                                    "sha256": resource.get("sha256"),
                                },
                                "primitive_index": draw.get(
                                    "primitive_index"
                                ),
                                "d3d9_sampler_register": register,
                                "sampler_type": "sampler2D",
                                "texture": texture,
                                "texture_sha256": texture_sha,
                                "provenance": {
                                    "format": PROVENANCE_FORMAT,
                                    "source_kind": "D3D9_CAPTURE_PPM",
                                    "source_sha256": source_sha,
                                    "capture_frame": candidate.get("frame"),
                                    "capture_draw_index": candidate.get(
                                        "draw_index"
                                    ),
                                    "texture_ptr": candidate.get(
                                        "texture_ptr"
                                    ),
                                    "snapshot_path": candidate.get(
                                        "snapshot_path"
                                    ),
                                    "resolved_snapshot_path": str(
                                        resolved
                                    ),
                                    "path_resolution": resolution,
                                    "resource_creation": candidate.get(
                                        "resource_creation"
                                    ),
                                    "scene_instance_transform_match": (
                                        {
                                            "format": INSTANCE_MATCH_FORMAT,
                                            "binding_index": binding_index,
                                            "selected_draw_order": (
                                                selected_instance_match.get(
                                                    "selected_draw_order"
                                                )
                                            ),
                                            "selected_draw_identity_sha256": (
                                                selected_instance_match.get(
                                                    "selected_draw_identity_sha256"
                                                )
                                            ),
                                            "runtime_observation_count": (
                                                selected_instance_match.get(
                                                    "runtime_observation_count"
                                                )
                                            ),
                                        }
                                        if selected_instance_match is not None
                                        else None
                                    ),
                                },
                            }

            if row_blockers:
                blockers.extend(
                    f"scene-external-capture:binding-{binding_index}:s"
                    f"{register}:{reason}"
                    for reason in row_blockers
                )
            elif snapshot_row is not None:
                snapshots.append(snapshot_row)

            rows.append({
                "binding_index": binding_index,
                "draw_order": draw.get("draw_order"),
                "register": register,
                "sampler": declaration.get("sampler"),
                "sampler_type": "sampler2D",
                "candidate_observation_count": len(candidates),
                "snapshot_ready": (
                    snapshot_row is not None and not row_blockers
                ),
                "blocking_reasons": row_blockers,
            })

        for declaration in cube_declarations:
            candidates = _matching_cube_rows(observations)
            row_blockers: list[str] = []
            if len(candidates) != 1:
                row_blockers.append(
                    f"cube-capture-observation-count:{len(candidates)}"
                )
            cube_snapshot_row = None
            if len(candidates) == 1 and root.is_dir():
                candidate = candidates[0]
                resolved_faces: dict[str, Path] = {}
                face_sources: dict[str, dict[str, Any]] = {}
                for face in CUBE_FACES:
                    raw_path = candidate["snapshot_paths"][face]
                    resolved, resolution, path_blockers = (
                        _resolve_snapshot_path(raw_path, root)
                    )
                    row_blockers.extend(
                        f"face-{face}:{reason}"
                        for reason in path_blockers
                    )
                    if resolved is None or path_blockers:
                        continue
                    resolved_faces[face] = resolved
                    face_sources[face] = {
                        "snapshot_path": raw_path,
                        "resolved_snapshot_path": str(resolved),
                        "path_resolution": resolution,
                        "source_sha256": _sha256_bytes(resolved),
                    }

                if (
                    not row_blockers
                    and set(resolved_faces) == set(CUBE_FACES)
                ):
                    try:
                        cube = ppms_to_reference_cube(resolved_faces)
                    except Exception as error:
                        row_blockers.append(
                            "snapshot-cube-ppm-decode-failed:"
                            + type(error).__name__
                        )
                    else:
                        for face in CUBE_FACES:
                            face_row = cube["faces"][face]
                            if isinstance(face_row, dict):
                                face_row.pop("source_path", None)
                        cube_sha = reference_cube_sha256(cube)
                        resource = draw.get("resource")
                        if not isinstance(resource, Mapping):
                            row_blockers.append(
                                "scene-resource-identity-missing"
                            )
                        else:
                            cube_snapshot_row = {
                                "draw_identity_sha256": (
                                    (draw.get("hashes") or {}).get(
                                        "draw_identity_sha256"
                                    )
                                ),
                                "resource": {
                                    "archive": resource.get("archive"),
                                    "path": resource.get("path"),
                                    "sha256": resource.get("sha256"),
                                },
                                "primitive_index": draw.get(
                                    "primitive_index"
                                ),
                                "d3d9_sampler_register": 3,
                                "sampler_type": "samplerCube",
                                "cube": cube,
                                "cube_sha256": cube_sha,
                                "provenance": {
                                    "format": PROVENANCE_FORMAT,
                                    "source_kind": "D3D9_CAPTURE_PPM_CUBE",
                                    "source_sha256": _cube_source_sha256(
                                        face_sources
                                    ),
                                    "capture_frame": candidate.get("frame"),
                                    "capture_draw_index": candidate.get(
                                        "draw_index"
                                    ),
                                    "texture_ptr": candidate.get(
                                        "texture_ptr"
                                    ),
                                    "resource_creation": candidate.get(
                                        "resource_creation"
                                    ),
                                    "face_sources": face_sources,
                                    "scene_instance_transform_match": (
                                        {
                                            "format": INSTANCE_MATCH_FORMAT,
                                            "binding_index": binding_index,
                                            "selected_draw_order": (
                                                selected_instance_match.get(
                                                    "selected_draw_order"
                                                )
                                            ),
                                            "selected_draw_identity_sha256": (
                                                selected_instance_match.get(
                                                    "selected_draw_identity_sha256"
                                                )
                                            ),
                                        }
                                        if selected_instance_match is not None
                                        else None
                                    ),
                                },
                            }

            if row_blockers:
                blockers.extend(
                    f"scene-external-capture:binding-{binding_index}:"
                    f"s3:{reason}"
                    for reason in row_blockers
                )
            elif cube_snapshot_row is not None:
                cube_snapshots.append(cube_snapshot_row)

            cube_rows.append({
                "binding_index": binding_index,
                "draw_order": draw.get("draw_order"),
                "register": 3,
                "sampler": declaration.get("sampler"),
                "sampler_type": "samplerCube",
                "candidate_observation_count": len(candidates),
                "snapshot_ready": (
                    cube_snapshot_row is not None and not row_blockers
                ),
                "blocking_reasons": row_blockers,
            })

    blockers = list(dict.fromkeys(blockers))
    provisional_contract = {
        "format": SNAPSHOT_FORMAT,
        "version": 1,
        "snapshots": snapshots,
    }
    cube_provisional_contract = {
        "format": CUBE_SNAPSHOT_FORMAT,
        "version": 1,
        "snapshots": cube_snapshots,
    }
    contract_validation = None
    cube_contract_validation = None
    if not blockers:
        contract_validation = (
            validate_external_sampler_snapshot_contract(
                provisional_contract
            )
        )
        blockers.extend(
            "scene-external-capture:phase589:" + str(reason)
            for reason in (
                contract_validation.get("blocking_reasons") or []
            )
        )
        blockers = list(dict.fromkeys(blockers))
        if not blockers:
            cube_contract_validation = (
                validate_external_sampler_cube_snapshot_contract(
                    cube_provisional_contract
                )
            )
            blockers.extend(
                "scene-external-capture:phase592:" + str(reason)
                for reason in (
                    cube_contract_validation.get("blocking_reasons") or []
                )
            )
            blockers = list(dict.fromkeys(blockers))

    ready = (
        not blockers
        and all(row["snapshot_ready"] for row in rows)
        and all(row["snapshot_ready"] for row in cube_rows)
        and len(snapshots) == required_count
        and len(cube_snapshots) == required_cube_count
    )
    status = (
        "ready"
        if ready and (required_count or required_cube_count)
        else "not-needed"
        if ready
        else "blocked"
    )
    contract = provisional_contract if ready else None
    cube_contract = cube_provisional_contract if ready else None
    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": ready,
        "blocking_reasons": blockers,
        "required_external_sampler2d_count": required_count,
        "required_external_samplercube_count": required_cube_count,
        "snapshot_count": len(snapshots),
        "cube_snapshot_count": len(cube_snapshots),
        "rows": rows,
        "cube_rows": cube_rows,
        "snapshot_contract": contract,
        "cube_snapshot_contract": cube_contract,
        "phase589_validation": (
            {
                "format": contract_validation.get("format"),
                "ready": contract_validation.get("ready") is True,
                "snapshot_count": contract_validation.get(
                    "snapshot_count"
                ),
                "blocking_reasons": list(
                    contract_validation.get("blocking_reasons")
                    or []
                ),
            }
            if isinstance(contract_validation, Mapping)
            else None
        ),
        "phase592_validation": (
            {
                "format": cube_contract_validation.get("format"),
                "ready": cube_contract_validation.get("ready") is True,
                "snapshot_count": cube_contract_validation.get(
                    "snapshot_count"
                ),
                "blocking_reasons": list(
                    cube_contract_validation.get("blocking_reasons")
                    or []
                ),
            }
            if isinstance(cube_contract_validation, Mapping)
            else None
        ),
        "boundary": {
            "requires_unique_scene_draw_per_binding": (
                instance_transform_match is None
            ),
            "repeated_instance_transform_match_supported": True,
            "instance_transform_match_format": INSTANCE_MATCH_FORMAT,
            "requires_phase573_strong_attribution": True,
            "requires_draw_local_texture_snapshot": True,
            "texture_snapshot_time": (
                "SetTexture-time content carried into the selected draw "
                "snapshot; post-bind mutations are not excluded"
            ),
            "requires_observed_texture2d_creation": True,
            "requires_observed_cube_texture_creation": True,
            "requires_exactly_one_ppm_snapshot_path": True,
            "requires_exactly_six_named_cube_face_paths": True,
            "capture_snapshot_basename_fallback_allowed": False,
            "capture_snapshot_archive_order_fallback_allowed": False,
            "cross_platform_snapshot_relocation": (
                "exact tools/run_shift_capture.ps1 <OutputDir>/textures layout"
            ),
            "material_textures_promoted": False,
            "sampler_cube_promoted": True,
            "sampler_cube_register_policy": "s3-only",
            "manual_scene_identity_guessing": False,
        },
    }


def validate_files(
    scene_bundle_path: str | Path,
    scene_bridge_path: str | Path,
    capture_pipeline_path: str | Path,
    *,
    capture_root: str | Path,
    instance_transform_match_path: str | Path | None = None,
) -> dict[str, Any]:
    instance_match = (
        _load(instance_transform_match_path)
        if instance_transform_match_path is not None
        else None
    )
    return build_scene_external_sampler_capture_adapter(
        _load(scene_bundle_path),
        _load(scene_bridge_path),
        _load(capture_pipeline_path),
        capture_root=capture_root,
        instance_transform_match=instance_match,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene_bundle")
    parser.add_argument("scene_bridge")
    parser.add_argument("capture_pipeline")
    parser.add_argument("output")
    parser.add_argument(
        "--capture-root",
        required=True,
        help=(
            "native capture output directory; exact relative snapshot paths "
            "and the launcher-owned textures/ directory are admissible"
        ),
    )
    parser.add_argument(
        "--instance-transform-match",
        help=(
            "optional SHIFT.NativeSceneInstanceTransformMatch/1 used "
            "to resolve repeated scene bindings"
        ),
    )
    parser.add_argument(
        "--snapshot-output",
        help=(
            "write ready SHIFT.NativeSceneExternalSamplerSnapshots/1 "
            "to this path"
        ),
    )
    parser.add_argument(
        "--cube-snapshot-output",
        help=(
            "write ready SHIFT.NativeSceneExternalSamplerCubeSnapshots/1 "
            "to this path"
        ),
    )
    args = parser.parse_args(argv)

    report = validate_files(
        args.scene_bundle,
        args.scene_bridge,
        args.capture_pipeline,
        capture_root=args.capture_root,
        instance_transform_match_path=args.instance_transform_match,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    if args.snapshot_output and report.get("snapshot_contract") is not None:
        snapshot_output = Path(args.snapshot_output)
        snapshot_output.parent.mkdir(parents=True, exist_ok=True)
        snapshot_output.write_text(
            json.dumps(
                report["snapshot_contract"],
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    if (
        args.cube_snapshot_output
        and report.get("cube_snapshot_contract") is not None
    ):
        cube_output = Path(args.cube_snapshot_output)
        cube_output.parent.mkdir(parents=True, exist_ok=True)
        cube_output.write_text(
            json.dumps(
                report["cube_snapshot_contract"],
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "required_external_sampler2d_count": report[
            "required_external_sampler2d_count"
        ],
        "snapshot_count": report["snapshot_count"],
        "cube_snapshot_count": report["cube_snapshot_count"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
