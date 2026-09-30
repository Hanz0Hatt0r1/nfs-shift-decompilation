"""Build SHIFT.NativeSceneBundle/1 from runtime-proven SGB/IMB RenderCommands.

The native runtime already consumes SHIFT.BMWVulkanBundleSet/1 as its ordered
atomic-bundle ABI. This adapter reuses that compatibility ABI, but admission is
driven by the renderer-neutral SHIFT.RuntimeProvenDraw/1 contract introduced in
Phase 577.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from bmw_vulkan_bundle import build_bmw_vulkan_bundle
from imb_neutral_geometry import build_imb_neutral_geometry
from texture_reference import CUBE_FORMAT, FORMAT as TEXTURE_FORMAT, decode_dds
from vulkan_bundle_set_prepare import prepare_bmw_vulkan_bundle_set

FORMAT = "SHIFT.NativeSceneBundle/1"
RUNTIME_PROVEN_DRAW_FORMAT = "SHIFT.RuntimeProvenDraw/1"
BRIDGE_FORMAT = "SHIFT.SGBRenderBindingBridge/1"
RENDER_BINDING_FORMAT = "SHIFT.RenderBinding/1"
BUNDLE_SET_FORMAT = "SHIFT.BMWVulkanBundleSet/1"


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def _load_json(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    result = json.loads(Path(value).read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError(f"expected JSON object: {value}")
    return result


def _manifest_rows(ir_root: Path) -> list[dict[str, Any]]:
    value = json.loads(
        (ir_root / "manifest.json").read_text(encoding="utf-8")
    )
    if not isinstance(value, list):
        raise ValueError("IR manifest.json must contain a JSON array")
    return [
        dict(row)
        for row in value
        if isinstance(row, Mapping) and "error" not in row
    ]


def _resolve_manifest_row(
    rows: list[dict[str, Any]],
    *,
    path: Any,
    sha256: Any = None,
    archive: Any = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    wanted_path = _norm(path)
    wanted_sha = str(sha256 or "").lower()
    wanted_archive = str(archive or "")
    candidates = [
        row for row in rows
        if _norm(row.get("path")) == wanted_path
    ]
    if wanted_archive:
        exact_archive = [
            row for row in candidates
            if str(row.get("archive") or "") == wanted_archive
        ]
        if exact_archive:
            candidates = exact_archive
    if wanted_sha:
        exact_sha = [
            row for row in candidates
            if str(row.get("sha256") or "").lower() == wanted_sha
        ]
        if exact_sha:
            candidates = exact_sha

    if not candidates:
        return None, ["manifest-resource-not-found"]

    content_keys = {
        (
            str(row.get("sha256") or "").lower(),
            str(row.get("raw") or ""),
        )
        for row in candidates
    }
    if len(content_keys) > 1:
        return None, ["manifest-resource-ambiguous"]
    return sorted(
        candidates,
        key=lambda row: (
            str(row.get("archive") or "").lower(),
            str(row.get("path") or "").lower(),
        ),
    )[0], []


def _read_manifest_raw(
    ir_root: Path,
    row: Mapping[str, Any],
) -> tuple[bytes | None, list[str]]:
    raw = row.get("raw")
    if not raw:
        return None, ["manifest-raw-path-missing"]
    path = ir_root / str(raw)
    if not path.is_file():
        return None, ["manifest-raw-file-missing"]
    data = path.read_bytes()
    expected = str(row.get("sha256") or "").lower()
    digest = _sha256(data)
    if expected and digest != expected:
        return None, ["manifest-raw-sha256-mismatch"]
    return data, []


def _texture_source_map(
    render_binding: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    resources = render_binding.get("resources") or {}
    return {
        str(row.get("id")): row
        for row in (resources.get("textures") or [])
        if isinstance(row, Mapping) and row.get("id")
    }


def _decode_submesh_textures(
    command_submesh: Mapping[str, Any],
    *,
    render_binding: Mapping[str, Any],
    manifest_rows: list[dict[str, Any]],
    ir_root: Path,
) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]], list[str]]:
    by_id = _texture_source_map(render_binding)
    textures: dict[int, dict[str, Any]] = {}
    provenance: list[dict[str, Any]] = []
    blockers: list[str] = []

    for texture_index, texture in enumerate(
        command_submesh.get("textures") or []
    ):
        if not isinstance(texture, Mapping):
            blockers.append(
                f"texture-{texture_index}:binding-invalid"
            )
            continue
        if texture.get("resource") == "external":
            continue
        try:
            register = int(texture.get("d3d9_sampler_register"))
        except (TypeError, ValueError):
            blockers.append(
                f"texture-{texture_index}:sampler-register-invalid"
            )
            continue

        texture_id = str(texture.get("texture_id") or "")
        resource = by_id.get(texture_id)
        if resource is None:
            blockers.append(
                f"texture-s{register}:resource-id-not-found:{texture_id}"
            )
            continue

        row, reasons = _resolve_manifest_row(
            manifest_rows,
            path=resource.get("path"),
            sha256=resource.get("sha256"),
        )
        if row is None:
            blockers.extend(
                f"texture-s{register}:{reason}" for reason in reasons
            )
            continue
        data, reasons = _read_manifest_raw(ir_root, row)
        if data is None:
            blockers.extend(
                f"texture-s{register}:{reason}" for reason in reasons
            )
            continue
        try:
            image = decode_dds(data)
        except (TypeError, ValueError) as error:
            blockers.append(
                f"texture-s{register}:dds-decode-failed:"
                f"{type(error).__name__}"
            )
            continue
        if image.get("format") == CUBE_FORMAT:
            blockers.append(
                f"texture-s{register}:material-texture-is-cubemap"
            )
            continue
        if image.get("format") != TEXTURE_FORMAT:
            blockers.append(
                f"texture-s{register}:decoded-format-unsupported"
            )
            continue

        textures[register] = image
        provenance.append({
            "register": register,
            "texture_id": texture_id,
            "path": row.get("path"),
            "archive": row.get("archive"),
            "sha256": _sha256(data),
            "decoded_format": image.get("format"),
            "width": image.get("width"),
            "height": image.get("height"),
        })

    return textures, provenance, blockers


def _runtime_proven_draw(
    packet: Mapping[str, Any],
    packet_submesh: Mapping[str, Any],
    command: Mapping[str, Any],
    command_submesh: Mapping[str, Any],
) -> tuple[Mapping[str, Any] | None, list[str]]:
    provenance = command_submesh.get("runtime_provenance")
    if not isinstance(provenance, Mapping):
        return None, ["runtime-provenance-missing"]

    reasons: list[str] = []
    if provenance.get("format") != RUNTIME_PROVEN_DRAW_FORMAT:
        reasons.append("runtime-provenance-format-invalid")
    if provenance.get("status") != "proven":
        reasons.append("runtime-provenance-status-not-proven")

    resource = provenance.get("resource") or {}
    if not isinstance(resource, Mapping):
        resource = {}
    mesh = packet.get("mesh") or {}
    resolved = mesh.get("resolved") or {}
    expected_path = _norm(resolved.get("path") or mesh.get("ref"))
    expected_sha = str(
        resolved.get("resource_sha256")
        or resolved.get("sha256")
        or ""
    ).lower()
    expected_archive = str(resolved.get("archive") or "")

    if str(resource.get("source_kind") or "") != "IMB":
        reasons.append("runtime-provenance-source-kind-not-imb")
    if _norm(resource.get("path")) != expected_path:
        reasons.append("runtime-provenance-resource-path-mismatch")
    if str(resource.get("sha256") or "").lower() != expected_sha:
        reasons.append("runtime-provenance-resource-sha256-mismatch")
    if expected_archive and str(resource.get("archive") or "") != expected_archive:
        reasons.append("runtime-provenance-resource-archive-mismatch")

    try:
        provenance_primitive = int(provenance.get("primitive_index"))
        packet_primitive = int(packet_submesh.get("primitive_index"))
        command_primitive = int(command_submesh.get("primitive_index"))
    except (TypeError, ValueError):
        reasons.append("runtime-provenance-primitive-index-invalid")
    else:
        if not (
            provenance_primitive
            == packet_primitive
            == command_primitive
        ):
            reasons.append("runtime-provenance-primitive-index-mismatch")

    draw_range = provenance.get("draw_range") or {}
    try:
        first_index = int(command_submesh.get("first_index"))
        index_count = int(command_submesh.get("index_count"))
        provenance_first = int(draw_range.get("first_index"))
        provenance_count = int(draw_range.get("index_count"))
        provenance_primitives = int(draw_range.get("primitive_count"))
    except (TypeError, ValueError):
        reasons.append("runtime-provenance-draw-range-invalid")
    else:
        if (
            provenance_first != first_index
            or provenance_count != index_count
            or index_count <= 0
            or index_count % 3
            or provenance_primitives != index_count // 3
        ):
            reasons.append("runtime-provenance-draw-range-mismatch")

    shader_selection = provenance.get("shader_selection") or {}
    if not isinstance(shader_selection, Mapping):
        shader_selection = {}
    if shader_selection.get("selection_status") != "unique":
        reasons.append("runtime-provenance-selection-not-unique")
    if shader_selection.get("selection_source") != "runtime-admission":
        reasons.append("runtime-provenance-selection-source-invalid")
    if shader_selection.get("runtime_selection_ready") is not True:
        reasons.append("runtime-provenance-runtime-selection-not-ready")

    admission = packet_submesh.get("runtime_shader_admission")
    if not isinstance(admission, Mapping):
        reasons.append("packet-runtime-admission-missing")
    else:
        try:
            admission_binding = int(admission.get("binding_index"))
            provenance_binding = int(provenance.get("binding_index"))
        except (TypeError, ValueError):
            reasons.append("runtime-provenance-binding-index-invalid")
        else:
            if admission_binding != provenance_binding:
                reasons.append("runtime-provenance-binding-index-mismatch")
        if admission.get("shader_selection_admitted") is not True:
            reasons.append("packet-runtime-admission-not-admitted")

    packet_world = packet.get("world_matrix")
    command_world = command.get("world_matrix")
    if (
        isinstance(packet_world, (list, tuple))
        and isinstance(command_world, (list, tuple))
    ):
        try:
            if len(packet_world) != 16 or len(command_world) != 16 or any(
                abs(float(a) - float(b)) > 1e-6
                for a, b in zip(packet_world, command_world)
            ):
                reasons.append("runtime-provenance-world-matrix-mismatch")
        except (TypeError, ValueError):
            reasons.append("runtime-provenance-world-matrix-invalid")

    return (None if reasons else provenance), reasons


def _is_identity_world_matrix(value: Any) -> bool:
    if not isinstance(value, (list, tuple)) or len(value) != 16:
        return False
    expected = (
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    )
    try:
        return all(
            abs(float(left) - right) <= 1e-6
            for left, right in zip(value, expected)
        )
    except (TypeError, ValueError):
        return False


def _bundle_set_manifest(
    draws: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    paths = output_dir / "bundle_set.paths"
    paths.write_text(
        "".join(f"{row['bundle_path']}\n" for row in draws),
        encoding="utf-8",
    )
    report = {
        "format": BUNDLE_SET_FORMAT,
        "version": 1,
        "status": "ready" if draws else "blocked",
        "ready": bool(draws),
        "blocking_reasons": (
            [] if draws else ["native-scene:no-ready-draws"]
        ),
        "source": {
            "render_command_format": RENDER_BINDING_FORMAT,
            "adapter_format": FORMAT,
            "selected_submesh_indices": [
                int(row["source_submesh_index"]) for row in draws
            ],
        },
        "draw_count": len(draws),
        "draws": draws,
        "artifacts": {
            "draw_order": {
                "path": "bundle_set.paths",
                "sha256": _sha256(paths.read_bytes()),
                "entry_count": len(draws),
            },
        },
        "execution": {
            "status": "prepared",
            "contract": (
                "ordered atomic SHIFT.BMWVulkanBundle/1 draws; "
                "scene transforms remain outside the current native ABI"
            ),
        },
    }
    manifest = output_dir / "bundle_set_manifest.json"
    _write_json(manifest, report)
    report["manifest_sha256"] = _sha256(manifest.read_bytes())
    return report


def build_native_scene_bundle(
    bridge: Mapping[str, Any],
    ir_root: str | Path,
    output_dir: str | Path,
    *,
    environment_cube: Mapping[str, Any] | str | Path | None = None,
    prepare: bool = False,
    validator: str | None = None,
) -> dict[str, Any]:
    if bridge.get("format") != BRIDGE_FORMAT:
        raise ValueError(
            "input must be SHIFT.SGBRenderBindingBridge/1"
        )

    render_binding = bridge.get("render_binding")
    if not isinstance(render_binding, Mapping):
        raise ValueError("SGB bridge contains no RenderBinding")
    if render_binding.get("format") != RENDER_BINDING_FORMAT:
        raise ValueError("bridge render_binding is not SHIFT.RenderBinding/1")

    runtime_join = bridge.get("runtime_shader_join") or (
        render_binding.get("runtime_shader_join") or {}
    )
    blockers: list[str] = []
    runtime_join_ready = (
        isinstance(runtime_join, Mapping)
        and runtime_join.get("ready") is True
    )
    if not runtime_join_ready:
        blockers.extend(
            "runtime-shader-join:" + str(reason)
            for reason in (
                runtime_join.get("blocking_reasons") or []
                if isinstance(runtime_join, Mapping)
                else ["missing"]
            )
        )
        if not blockers:
            blockers.append("runtime-shader-join:not-ready")

    root = Path(ir_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest_rows = _manifest_rows(root)

    packets = [
        row for row in (render_binding.get("packets") or [])
        if isinstance(row, Mapping)
    ]
    commands = [
        row for row in (render_binding.get("render_commands") or [])
        if isinstance(row, Mapping)
    ]
    if len(packets) != len(commands):
        blockers.append("scene-bundle:packet-command-count-mismatch")

    ready_draws: list[dict[str, Any]] = []
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    world_matrices: list[Any] = []

    pair_count = min(len(packets), len(commands))
    for command_index in range(pair_count):
        packet = packets[command_index]
        command = commands[command_index]
        mesh = packet.get("mesh") or {}
        mesh_ref = str(mesh.get("ref") or "")
        resolved = mesh.get("resolved") or {}
        source_kind = str(mesh.get("source_kind") or "")
        packet_submeshes = packet.get("submeshes") or []
        command_submeshes = command.get("submeshes") or []
        world_matrix = packet.get("world_matrix")
        world_matrices.append(world_matrix)

        if source_kind != "IMB":
            for submesh_index in range(len(command_submeshes)):
                excluded.append({
                    "command_index": command_index,
                    "submesh_index": submesh_index,
                    "mesh_ref": mesh_ref,
                    "reason": "not-imb-runtime-admission-scope",
                })
            continue

        resource_row, resource_reasons = _resolve_manifest_row(
            manifest_rows,
            path=mesh_ref,
            sha256=resolved.get("resource_sha256"),
            archive=resolved.get("archive"),
        )
        neutral_mesh = None
        resource_sha = None
        if resource_row is None:
            blockers.extend(
                f"command-{command_index}:mesh:{reason}"
                for reason in resource_reasons
            )
        else:
            raw, raw_reasons = _read_manifest_raw(root, resource_row)
            if raw is None:
                blockers.extend(
                    f"command-{command_index}:mesh:{reason}"
                    for reason in raw_reasons
                )
            else:
                resource_sha = _sha256(raw)
                packet_sha = str(
                    resolved.get("resource_sha256") or ""
                ).lower()
                if packet_sha and resource_sha != packet_sha:
                    blockers.append(
                        f"command-{command_index}:mesh:"
                        "packet-resource-sha256-mismatch"
                    )
                try:
                    neutral = build_imb_neutral_geometry(raw)
                except (TypeError, ValueError) as error:
                    blockers.append(
                        f"command-{command_index}:mesh-neutral-decode:"
                        f"{type(error).__name__}"
                    )
                else:
                    if neutral.get("ready") is not True:
                        blockers.extend(
                            f"command-{command_index}:mesh-neutral:{reason}"
                            for reason in (
                                neutral.get("blocking_reasons") or []
                            )
                        )
                    else:
                        neutral_mesh = dict(neutral["mesh"])

        if len(packet_submeshes) != len(command_submeshes):
            blockers.append(
                f"command-{command_index}:submesh-count-mismatch"
            )

        for submesh_index in range(
            min(len(packet_submeshes), len(command_submeshes))
        ):
            packet_submesh = packet_submeshes[submesh_index]
            command_submesh = command_submeshes[submesh_index]
            runtime_provenance = None
            runtime_provenance_reasons: list[str] = []
            if runtime_join_ready:
                (
                    runtime_provenance,
                    runtime_provenance_reasons,
                ) = _runtime_proven_draw(
                    packet,
                    packet_submesh,
                    command,
                    command_submesh,
                )
            if not runtime_join_ready or runtime_provenance is None:
                excluded.append({
                    "command_index": command_index,
                    "submesh_index": submesh_index,
                    "mesh_ref": mesh_ref,
                    "reason": (
                        "runtime-shader-join-not-ready"
                        if not runtime_join_ready
                        else "runtime-provenance-not-proven"
                    ),
                    "blocking_reasons": runtime_provenance_reasons,
                })
                continue
            if neutral_mesh is None or resource_row is None:
                excluded.append({
                    "command_index": command_index,
                    "submesh_index": submesh_index,
                    "mesh_ref": mesh_ref,
                    "reason": "neutral-mesh-not-ready",
                })
                continue

            command_for_bundle = json.loads(json.dumps(command))
            command_for_bundle.setdefault("mesh", {})
            command_for_bundle["mesh"]["ref"] = mesh_ref
            command_for_bundle["mesh"]["resolved"] = {
                "path": resource_row.get("path"),
                "archive": resource_row.get("archive"),
                "resource_sha256": resource_sha,
            }

            textures, texture_provenance, texture_blockers = (
                _decode_submesh_textures(
                    command_submesh,
                    render_binding=render_binding,
                    manifest_rows=manifest_rows,
                    ir_root=root,
                )
            )
            child_path = (
                Path("draws")
                / f"command_{command_index:05d}_submesh_{submesh_index:03d}"
            )
            child = out / child_path
            try:
                child_report = build_bmw_vulkan_bundle(
                    command_for_bundle,
                    neutral_mesh,
                    child,
                    textures=textures if textures else None,
                    environment_cube=environment_cube,
                    submesh_index=submesh_index,
                    expected_mesh_ref=mesh_ref,
                )
            except (OSError, TypeError, ValueError) as error:
                child_report = {
                    "format": "SHIFT.BMWVulkanBundle/1",
                    "status": "blocked",
                    "ready": False,
                    "blocking_reasons": [
                        "native-scene:child-build-failed:"
                        + type(error).__name__
                    ],
                }

            child_reasons = [
                *texture_blockers,
                *[
                    str(reason)
                    for reason in (
                        child_report.get("blocking_reasons") or []
                    )
                ],
            ]
            if texture_blockers or child_report.get("ready") is not True:
                excluded.append({
                    "command_index": command_index,
                    "submesh_index": submesh_index,
                    "mesh_ref": mesh_ref,
                    "runtime_binding_index": (
                        (packet_submesh.get(
                            "runtime_shader_admission"
                        ) or {}).get("binding_index")
                    ),
                    "reason": "native-child-not-ready",
                    "blocking_reasons": list(
                        dict.fromkeys(child_reasons)
                    ),
                })
                continue

            manifest_path = child / "bundle_manifest.json"
            shader = command_submesh.get("shader") or {}
            permutation = shader.get("permutation_identity") or {}
            draw = {
                "draw_order": len(ready_draws),
                "source_command_index": command_index,
                "source_submesh_index": submesh_index,
                "first_index": int(
                    command_submesh.get("first_index", 0)
                ),
                "index_count": int(
                    command_submesh.get("index_count", 0)
                ),
                "bundle_path": str(child_path),
                "manifest_path": str(
                    child_path / "bundle_manifest.json"
                ),
                "manifest_sha256": _sha256(
                    manifest_path.read_bytes()
                ),
                "status": child_report.get("status"),
                "ready": True,
                "blocking_reasons": [],
                "shader_permutation_identity_sha256": (
                    permutation.get("identity_sha256")
                    if isinstance(permutation, Mapping)
                    else None
                ),
            }
            ready_draws.append(draw)
            included.append({
                "draw_order": draw["draw_order"],
                "command_index": command_index,
                "submesh_index": submesh_index,
                "mesh_ref": mesh_ref,
                "mesh_sha256": resource_sha,
                "archive": resource_row.get("archive"),
                "runtime_binding_index": (
                    runtime_provenance.get("binding_index")
                    if runtime_provenance is not None
                    else None
                ),
                "world_matrix": world_matrix,
                "world_matrix_identity": _is_identity_world_matrix(
                    world_matrix
                ),
                "texture_sources": texture_provenance,
                "bundle_path": str(child_path),
                "bundle_manifest_sha256": draw["manifest_sha256"],
                "shader_permutation_identity_sha256": draw[
                    "shader_permutation_identity_sha256"
                ],
            })

    bundle_set = _bundle_set_manifest(ready_draws, out)
    prepare_report = None
    if prepare and bundle_set.get("ready") is True:
        prepare_report = prepare_bmw_vulkan_bundle_set(
            out,
            validator=validator,
        )

    adapter_blockers = list(dict.fromkeys(blockers))
    if not ready_draws:
        adapter_blockers.append("scene-bundle:no-runtime-proven-ready-draws")

    status = (
        "blocked"
        if not ready_draws
        else "partial"
        if excluded or adapter_blockers
        else "ready"
    )
    bundle_set_ready = bundle_set.get("ready") is True
    native_execution_ready = (
        bundle_set_ready
        and (
            prepare_report.get("ready") is True
            if prepare_report is not None
            else False
        )
    )

    report = {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": bool(ready_draws) and not adapter_blockers,
        "bundle_set_ready": bundle_set_ready,
        "native_execution_ready": native_execution_ready,
        "blocking_reasons": adapter_blockers,
        "summary": {
            "packet_count": len(packets),
            "render_command_count": len(commands),
            "runtime_proven_draw_count": len(included),
            "excluded_draw_count": len(excluded),
            "bundle_set_draw_count": len(ready_draws),
        },
        "coverage_complete": (
            bool(included)
            and not excluded
            and len(included) == sum(
                len(packet.get("submeshes") or [])
                for packet in packets
                if str((packet.get("mesh") or {}).get("source_kind") or "")
                == "IMB"
            )
        ),
        "included_draws": included,
        "excluded_draws": excluded,
        "bundle_set": bundle_set,
        "bundle_set_prepare": prepare_report,
        "boundary": {
            "atomic_native_abi": "SHIFT.BMWVulkanBundle/1",
            "ordered_native_abi": BUNDLE_SET_FORMAT,
            "source_geometry": "source-backed SHIFT.NeutralMesh/1 from IMB",
            "runtime_shader_requirement": (
                "Phase 577 SHIFT.RuntimeProvenDraw/1 plus "
                "Phase 576 exact primitive admission cross-check"
            ),
            "unproven_draw_policy": "exclude-and-report",
            "world_matrix_provenance_preserved": True,
            "world_matrix_applied_by_native_runtime": False,
            "geometry_normalization_applied": True,
            "scene_transform_parity": False,
            "native_scene_claim": (
                "material/geometry execution checkpoint only; "
                "not world-space Silverstone parity"
            ),
        },
    }
    _write_json(out / "native_scene_bundle.json", report)
    return report


def validate_files(
    bridge_path: str | Path,
    ir_root: str | Path,
    output_dir: str | Path,
    *,
    environment_cube_path: str | Path | None = None,
    prepare: bool = False,
    validator: str | None = None,
) -> dict[str, Any]:
    bridge = _load_json(bridge_path)
    environment_cube = (
        _load_json(environment_cube_path)
        if environment_cube_path is not None
        else None
    )
    return build_native_scene_bundle(
        bridge,
        ir_root,
        output_dir,
        environment_cube=environment_cube,
        prepare=prepare,
        validator=validator,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bridge")
    parser.add_argument("ir_root")
    parser.add_argument("output_dir")
    parser.add_argument("--environment-cube")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--validator")
    args = parser.parse_args(argv)

    report = validate_files(
        args.bridge,
        args.ir_root,
        args.output_dir,
        environment_cube_path=args.environment_cube,
        prepare=args.prepare,
        validator=args.validator,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "bundle_set_ready": report["bundle_set_ready"],
        "native_execution_ready": report["native_execution_ready"],
        "summary": report["summary"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["bundle_set_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
