"""Convert attributed D3D9 texture captures into exact Phase 589 scene snapshots.

Phase 590 consumes only draw-local texture observations that already support a
strong Phase 572 shader attribution. It then joins those observations to one
unique NativeSceneBundle draw and one exact external sampler2D declaration
before converting a captured PPM into SHIFT.ReferenceTexture/1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping

from native_scene_external_sampler_snapshots import (
    FORMAT as SNAPSHOT_FORMAT,
    PROVENANCE_FORMAT,
    reference_texture_sha256,
)
from runtime_texture_reference import ppm_to_reference_texture

FORMAT = "SHIFT.NativeSceneExternalSamplerCaptureAdapter/1"
SCENE_FORMAT = "SHIFT.NativeSceneBundle/1"
BRIDGE_FORMAT = "SHIFT.SGBRenderBindingBridge/1"
PIPELINE_FORMAT = "SHIFT.IMBRuntimeCapturePipeline/1"


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


def _resolve_snapshot_path(
    raw_path: str,
    capture_root: Path,
) -> tuple[Path | None, str, list[str]]:
    blockers: list[str] = []
    direct = Path(raw_path)
    if direct.is_absolute() and direct.is_file():
        return direct, "absolute-existing", []

    normalized = raw_path.replace("\\", "/")
    normalized_path = Path(normalized)
    if not normalized_path.is_absolute():
        joined = (capture_root / normalized_path).resolve()
        try:
            joined.relative_to(capture_root.resolve())
        except ValueError:
            blockers.append("snapshot-path-escapes-capture-root")
        else:
            if joined.is_file():
                return joined, "capture-root-relative", []

    # Native capture paths are often Windows-absolute. When a capture directory
    # is copied to Linux, remap only by a unique basename below an explicitly
    # supplied capture root. Ambiguity stays fail-closed.
    name = PureWindowsPath(raw_path).name
    if not name:
        return None, "unresolved", blockers + ["snapshot-path-name-missing"]
    hits = sorted(
        (path for path in capture_root.rglob(name) if path.is_file()),
        key=lambda path: path.as_posix(),
    )
    if len(hits) == 1:
        return hits[0], "capture-root-unique-basename", blockers
    if not hits:
        blockers.append("snapshot-path-not-found")
    else:
        blockers.append("snapshot-path-basename-ambiguous")
    return None, "unresolved", blockers


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
) -> dict[str, Any]:
    if scene_bundle.get("format") != SCENE_FORMAT:
        raise ValueError("scene input must be SHIFT.NativeSceneBundle/1")
    if scene_bridge.get("format") != BRIDGE_FORMAT:
        raise ValueError(
            "bridge input must be SHIFT.SGBRenderBindingBridge/1"
        )
    if capture_pipeline.get("format") != PIPELINE_FORMAT:
        raise ValueError(
            "capture input must be SHIFT.IMBRuntimeCapturePipeline/1"
        )

    root = Path(capture_root)
    blockers: list[str] = []
    if scene_bundle.get("ready") is not True:
        blockers.append("scene-external-capture:scene-bundle-not-ready")
    if scene_bridge.get("ready") is not True:
        blockers.append("scene-external-capture:scene-bridge-not-ready")
    if capture_pipeline.get("pipeline_ready") is not True:
        blockers.append("scene-external-capture:capture-pipeline-not-ready")
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
    rows: list[dict[str, Any]] = []

    for binding_index in sorted(scene_by_binding):
        draws = scene_by_binding[binding_index]
        external_decl_sets = []
        for draw in draws:
            declarations, declaration_blockers = (
                _external_sampler2d_declarations(scene_bridge, draw)
            )
            blockers.extend(
                f"scene-external-capture:binding-{binding_index}:{reason}"
                for reason in declaration_blockers
            )
            external_decl_sets.append(declarations)

        needs_external = any(external_decl_sets)
        if not needs_external:
            continue
        if len(draws) != 1:
            blockers.append(
                f"scene-external-capture:binding-{binding_index}:"
                f"scene-draw-ambiguous:{len(draws)}"
            )
            continue

        draw = draws[0]
        declarations = external_decl_sets[0]
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

    blockers = list(dict.fromkeys(blockers))
    required_count = len(rows)
    ready = (
        not blockers
        and all(row["snapshot_ready"] for row in rows)
    )
    status = (
        "ready"
        if ready and required_count
        else "not-needed"
        if ready
        else "blocked"
    )
    contract = (
        {
            "format": SNAPSHOT_FORMAT,
            "version": 1,
            "snapshots": snapshots,
        }
        if ready
        else None
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": ready,
        "blocking_reasons": blockers,
        "required_external_sampler2d_count": required_count,
        "snapshot_count": len(snapshots),
        "rows": rows,
        "snapshot_contract": contract,
        "boundary": {
            "requires_unique_scene_draw_per_binding": True,
            "requires_phase573_strong_attribution": True,
            "requires_draw_local_texture_snapshot": True,
            "requires_observed_texture2d_creation": True,
            "requires_exactly_one_ppm_snapshot_path": True,
            "material_textures_promoted": False,
            "sampler_cube_promoted": False,
            "manual_scene_identity_guessing": False,
        },
    }


def validate_files(
    scene_bundle_path: str | Path,
    scene_bridge_path: str | Path,
    capture_pipeline_path: str | Path,
    *,
    capture_root: str | Path,
) -> dict[str, Any]:
    return build_scene_external_sampler_capture_adapter(
        _load(scene_bundle_path),
        _load(scene_bridge_path),
        _load(capture_pipeline_path),
        capture_root=capture_root,
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
        help="directory containing PPM texture snapshots from native capture",
    )
    parser.add_argument(
        "--snapshot-output",
        help=(
            "write ready SHIFT.NativeSceneExternalSamplerSnapshots/1 "
            "to this path"
        ),
    )
    args = parser.parse_args(argv)

    report = validate_files(
        args.scene_bundle,
        args.scene_bridge,
        args.capture_pipeline,
        capture_root=args.capture_root,
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

    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "required_external_sampler2d_count": report[
            "required_external_sampler2d_count"
        ],
        "snapshot_count": report["snapshot_count"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
