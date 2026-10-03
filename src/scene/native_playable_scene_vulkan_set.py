"""Compose Silverstone track + canonical BMW body into one neutral scene set.

Phase 643 removes the native-runtime geometry-source exclusivity blocker without
changing the runtime ABI.  Track children are copied from an already prepared
SHIFT.NativeSceneVulkanSet/1.  BMW children are rebuilt as genuine
SHIFT.VulkanDrawBundle/1 objects from the canonical BMW material slice using the
neutral bundle builder; existing SHIFT.BMWVulkanBundle/1 manifests are never
relabelled.

The vehicle draw keeps its source RenderCommand world matrix.  No persistent
BODY pose, Phase 698 selector output, or guessed chassis transform is applied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterable, Mapping

from bmw_material_vulkan_adapter import (
    _extract_exact_material_dds,
    _find_mesh,
    _find_render_command,
    _normalize_set_submesh_indices,
    _sanitize_dds_bridge_provenance,
)
from bmw_vulkan_bundle import TARGET_MEB
from native_scene_vulkan_prepare import prepare_native_scene_vulkan_set
from vulkan_dds_bridge import bridge_bmw_dds_resources
from vulkan_draw_bundle import build_vulkan_draw_bundle

FORMAT = "SHIFT.NativePlayableSceneVulkanSet/1"
SET_FORMAT = "SHIFT.NativeSceneVulkanSet/1"
PREPARE_FORMAT = "SHIFT.NativeSceneVulkanSetPrepare/1"
BMW_SLICE_FORMATS = {
    "SHIFT.BMWMaterialSlice/1",
    "SHIFT.BMWMaterialSliceSet/1",
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _safe_relative(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def _merge_dds_bridge_into_neutral_bundle(
    bundle: dict[str, Any],
    dds_bridge: Mapping[str, Any],
    bundle_dir: Path,
) -> dict[str, Any]:
    merged = json.loads(json.dumps(bundle))
    blockers = [str(reason) for reason in merged.get("blocking_reasons") or []]
    blockers.extend(str(reason) for reason in dds_bridge.get("blocking_reasons") or [])

    artifacts = dict(merged.get("artifacts") or {})
    packets = dds_bridge.get("packets") or {}
    tex_packet = packets.get("textures")
    cube_packet = packets.get("environment_cube")
    if isinstance(tex_packet, Mapping):
        packet_path = bundle_dir / str(tex_packet.get("path") or "")
        artifacts["textures"] = {
            "path": tex_packet.get("path"),
            "sha256": _sha(packet_path) if packet_path.is_file() else None,
            "ready": dds_bridge.get("ready") is True,
            "texture_count": len(dds_bridge.get("material_2d_registers") or []),
        }
    if isinstance(cube_packet, Mapping):
        packet_path = bundle_dir / str(cube_packet.get("path") or "")
        artifacts["environment_cube"] = {
            "path": cube_packet.get("path"),
            "sha256": _sha(packet_path) if packet_path.is_file() else None,
            "ready": dds_bridge.get("ready") is True,
            "register": 3,
        }
    artifacts["dds_bridge"] = {
        "format": dds_bridge.get("format"),
        "ready": dds_bridge.get("ready") is True,
        "provenance": dds_bridge.get("provenance"),
    }
    merged["artifacts"] = artifacts
    merged["dds_bridge"] = dict(dds_bridge)

    remaining: list[str] = []
    for reason in blockers:
        if reason == "vulkan-draw-bundle:material-textures-not-supplied" and tex_packet:
            continue
        if reason == "vulkan-draw-bundle:environment-cube-not-supplied" and cube_packet:
            continue
        remaining.append(reason)
    merged["blocking_reasons"] = list(dict.fromkeys(remaining))
    merged["ready"] = not merged["blocking_reasons"]
    merged["status"] = "ready" if merged["ready"] else "partial"
    _write(bundle_dir / "bundle_manifest.json", merged)
    merged["manifest_sha256"] = _sha(bundle_dir / "bundle_manifest.json")
    return merged


def _track_rows(track_root: Path, out: Path) -> tuple[list[dict[str, Any]], list[str]]:
    blockers: list[str] = []
    manifest_path = track_root / "bundle_set_manifest.json"
    prepare_path = track_root / "bundle_set_prepare.json"
    paths_path = track_root / "bundle_set.paths"
    if not manifest_path.is_file() or not prepare_path.is_file() or not paths_path.is_file():
        return [], ["playable-scene:track-set-artifact-missing"]
    manifest = _load(manifest_path)
    prepare = _load(prepare_path)
    if manifest.get("format") != SET_FORMAT or manifest.get("ready") is not True:
        blockers.append("playable-scene:track-set-not-ready")
    if prepare.get("format") != PREPARE_FORMAT or prepare.get("ready") is not True:
        blockers.append("playable-scene:track-prepare-not-ready")
    draws = manifest.get("draws") or []
    paths = [line.strip() for line in paths_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not isinstance(draws, list) or len(draws) != len(paths) or not draws:
        blockers.append("playable-scene:track-draw-order-invalid")
    if blockers:
        return [], blockers

    rows: list[dict[str, Any]] = []
    for index, (raw_draw, relative) in enumerate(zip(draws, paths)):
        if not isinstance(raw_draw, Mapping) or not _safe_relative(relative):
            blockers.append(f"playable-scene:track-draw-{index}:invalid")
            continue
        source_child = track_root / relative
        source_manifest = source_child / "bundle_manifest.json"
        if not source_manifest.is_file():
            blockers.append(f"playable-scene:track-draw-{index}:manifest-missing")
            continue
        bundle = raw_draw.get("bundle") or {}
        expected = str(bundle.get("manifest_sha256") or "").lower()
        if len(expected) != 64 or _sha(source_manifest) != expected:
            blockers.append(f"playable-scene:track-draw-{index}:manifest-sha256-mismatch")
            continue
        target_relative = f"draw_{len(rows):04d}"
        target_child = out / target_relative
        shutil.copytree(source_child, target_child)
        copied_manifest = target_child / "bundle_manifest.json"
        rows.append({
            "draw_order": len(rows),
            "command_index": raw_draw.get("command_index"),
            "submesh_index": raw_draw.get("submesh_index"),
            "binding_index": raw_draw.get("binding_index"),
            "source_group": "track",
            "status": "ready",
            "ready": True,
            "blocking_reasons": [],
            "scene_draw_identity_sha256": raw_draw.get("scene_draw_identity_sha256"),
            "resource": raw_draw.get("resource"),
            "bundle": {
                "format": "SHIFT.VulkanDrawBundle/1",
                "manifest_path": f"{target_relative}/bundle_manifest.json",
                "manifest_sha256": _sha(copied_manifest),
            },
        })
    return rows, blockers


def _vehicle_rows(
    material_slice_path: Path,
    out: Path,
    *,
    source_bffs: Iterable[str | Path],
    environment_cube_dds: str | Path | None,
    start_order: int,
) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    payload = _load(material_slice_path)
    blockers: list[str] = []
    if payload.get("format") not in BMW_SLICE_FORMATS:
        return [], ["playable-scene:vehicle-material-slice-format-invalid"], {}
    if payload.get("ready") is not True:
        blockers.extend(
            "playable-scene:vehicle-material-slice:" + str(reason)
            for reason in payload.get("blocking_reasons") or ["not-ready"]
        )
        return [], blockers, {}

    command = _find_render_command(payload)
    mesh = _find_mesh(payload, command)
    mesh_ref = (command.get("mesh") or {}).get("ref")
    if mesh_ref != TARGET_MEB:
        return [], ["playable-scene:vehicle-mesh-is-not-canonical-bmw-body"], {}
    world_matrix = command.get("world_matrix")
    if not isinstance(world_matrix, list) or len(world_matrix) not in {4, 16}:
        return [], ["playable-scene:vehicle-world-matrix-source-missing"], {}

    indices = _normalize_set_submesh_indices(command, None)
    binding = {"format": "SHIFT.RenderBinding/1", "render_commands": [command]}
    source_bff_list = [Path(path) for path in source_bffs]
    rows: list[dict[str, Any]] = []

    for submesh_index in indices:
        child_order = start_order + len(rows)
        child_relative = f"draw_{child_order:04d}"
        child = out / child_relative
        child.mkdir(parents=True, exist_ok=True)
        dds_map: dict[str, str] = {}
        dds_provenance: list[dict[str, Any]] = []
        dds_blockers: list[str] = []
        with TemporaryDirectory(prefix="shift_playable_bmw_dds_") as temp_dir:
            if source_bff_list:
                dds_map, dds_provenance, dds_blockers = _extract_exact_material_dds(
                    payload,
                    command,
                    source_bff_list,
                    Path(temp_dir),
                    submesh_index=submesh_index,
                )
            try:
                child_report = build_vulkan_draw_bundle(
                    binding,
                    mesh,
                    child,
                    command_index=0,
                    submesh_index=submesh_index,
                    require_runtime_provenance=False,
                )
            except (OSError, TypeError, ValueError) as exc:
                blockers.append(
                    f"playable-scene:vehicle-draw-{submesh_index}:build-failed:{type(exc).__name__}"
                )
                continue

            dds_bridge = None
            if dds_blockers:
                blockers.extend(
                    f"playable-scene:vehicle-draw-{submesh_index}:{reason}"
                    for reason in dds_blockers
                )
            elif dds_map or environment_cube_dds is not None:
                try:
                    dds_bridge = bridge_bmw_dds_resources(
                        command,
                        dds_map,
                        child,
                        environment_cube_dds=environment_cube_dds,
                    )
                    dds_bridge = _sanitize_dds_bridge_provenance(
                        dds_bridge,
                        child,
                        texture_provenance=dds_provenance,
                    )
                    child_report = _merge_dds_bridge_into_neutral_bundle(
                        child_report,
                        dds_bridge,
                        child,
                    )
                except (OSError, TypeError, ValueError) as exc:
                    blockers.append(
                        f"playable-scene:vehicle-draw-{submesh_index}:dds-bridge-failed:{type(exc).__name__}"
                    )

        child_reasons = [str(reason) for reason in child_report.get("blocking_reasons") or []]
        transform = (child_report.get("artifacts") or {}).get("world_transform")
        if not isinstance(transform, Mapping) or transform.get("ready") is not True:
            child_reasons.append("playable-scene:vehicle-world-transform-packet-missing")
        if child_report.get("ready") is not True or child_reasons:
            blockers.extend(
                f"playable-scene:vehicle-draw-{submesh_index}:{reason}"
                for reason in child_reasons or ["not-ready"]
            )
            continue

        manifest_path = child / "bundle_manifest.json"
        source_identity = {
            "mesh_ref": mesh_ref,
            "mesh_sha256": ((command.get("mesh") or {}).get("resolved") or {}).get("resource_sha256"),
            "submesh_index": submesh_index,
            "material_slice_sha256": _sha(material_slice_path),
        }
        rows.append({
            "draw_order": child_order,
            "command_index": 0,
            "submesh_index": submesh_index,
            "binding_index": None,
            "source_group": "vehicle",
            "status": "ready",
            "ready": True,
            "blocking_reasons": [],
            "scene_draw_identity_sha256": _json_sha(source_identity),
            "resource": {
                "kind": "BMW-canonical-body",
                "path": mesh_ref,
                "sha256": source_identity["mesh_sha256"],
            },
            "vehicle_source_identity": source_identity,
            "bundle": {
                "format": child_report.get("format"),
                "manifest_path": f"{child_relative}/bundle_manifest.json",
                "manifest_sha256": _sha(manifest_path),
                "world_transform": transform,
            },
        })

    source = {
        "material_slice_path": str(material_slice_path),
        "material_slice_sha256": _sha(material_slice_path),
        "material_slice_format": payload.get("format"),
        "mesh_ref": mesh_ref,
        "mesh_sha256": ((command.get("mesh") or {}).get("resolved") or {}).get("resource_sha256"),
        "selected_submesh_indices": indices,
        "source_bffs": [path.name for path in source_bff_list],
    }
    return rows, list(dict.fromkeys(blockers)), source


def build_native_playable_scene_vulkan_set(
    track_scene_set: str | Path,
    vehicle_material_slice: str | Path,
    output_dir: str | Path,
    *,
    source_bffs: Iterable[str | Path] = (),
    environment_cube_dds: str | Path | None = None,
    validator: str | None = None,
) -> dict[str, Any]:
    track_root = Path(track_scene_set).resolve()
    vehicle_path = Path(vehicle_material_slice).resolve()
    out = Path(output_dir).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    track_rows, track_blockers = _track_rows(track_root, out)
    vehicle_rows, vehicle_blockers, vehicle_source = _vehicle_rows(
        vehicle_path,
        out,
        source_bffs=source_bffs,
        environment_cube_dds=environment_cube_dds,
        start_order=len(track_rows),
    )
    rows = [*track_rows, *vehicle_rows]
    blockers = list(dict.fromkeys([*track_blockers, *vehicle_blockers]))
    if not track_rows:
        blockers.append("playable-scene:track-draws-missing")
    if not vehicle_rows:
        blockers.append("playable-scene:vehicle-draws-missing")

    for order, row in enumerate(rows):
        row["draw_order"] = order
    paths = [Path(str((row.get("bundle") or {}).get("manifest_path"))).parent.as_posix() for row in rows]
    (out / "bundle_set.paths").write_text(
        "".join(path + "\n" for path in paths),
        encoding="utf-8",
    )

    ready = bool(track_rows and vehicle_rows) and not blockers
    manifest = {
        "format": SET_FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "draw_count": len(rows),
        "ready_draw_count": sum(row.get("ready") is True for row in rows),
        "draws": rows,
        "native_scene_submission": {
            "ready": ready,
            "blocking_reasons": [],
            "world_transform_execution": "required-before-native-scene-submit",
            "external_runtime_resources": "must-be-explicitly-bound",
        },
        "source": {
            "composition_format": FORMAT,
            "track_scene_set": str(track_root),
            "track_manifest_sha256": _sha(track_root / "bundle_set_manifest.json") if (track_root / "bundle_set_manifest.json").is_file() else None,
            "vehicle": vehicle_source,
        },
        "boundary": {
            "track_and_vehicle_share_one_native_scene_set": ready,
            "track_children_rebuilt": False,
            "bmw_manifests_relabelled_as_neutral": False,
            "vehicle_children_rebuilt_with_neutral_builder": True,
            "vehicle_resource_identity_preserved": True,
            "vehicle_source_world_transform_preserved": True,
            "persistent_BODY_pose_consumed": False,
            "phase698_vehicle_BODY_selection_consumed": False,
            "dynamic_vehicle_world_transform_claimed": False,
        },
    }
    _write(out / "bundle_set_manifest.json", manifest)

    prepare = prepare_native_scene_vulkan_set(out, validator=validator)
    if prepare.get("ready") is not True:
        blockers.extend(
            "playable-scene:prepare:" + str(reason)
            for reason in prepare.get("blocking_reasons") or ["not-ready"]
        )
    blockers = list(dict.fromkeys(blockers))
    final_ready = ready and prepare.get("ready") is True and not blockers
    wrapper = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if final_ready else "blocked",
        "ready": final_ready,
        "blocking_reasons": blockers,
        "track_draw_count": len(track_rows),
        "vehicle_draw_count": len(vehicle_rows),
        "draw_count": len(rows),
        "scene_set": {
            "format": SET_FORMAT,
            "path": str(out),
            "manifest_sha256": _sha(out / "bundle_set_manifest.json"),
            "ready": manifest.get("ready") is True,
        },
        "prepare": {
            "format": prepare.get("format"),
            "ready": prepare.get("ready") is True,
            "path": str(out / "bundle_set_prepare.json"),
            "sha256": _sha(out / "bundle_set_prepare.json") if (out / "bundle_set_prepare.json").is_file() else None,
        },
        "vehicle_source": vehicle_source,
        "boundary": dict(manifest["boundary"]),
    }
    _write(out / "playable_scene_composition.json", wrapper)
    return wrapper


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track_scene_set")
    parser.add_argument("vehicle_material_slice")
    parser.add_argument("output_dir")
    parser.add_argument("--source-bff", action="append", default=[])
    parser.add_argument("--environment-cube-dds")
    parser.add_argument("--validator")
    args = parser.parse_args(argv)
    result = build_native_playable_scene_vulkan_set(
        args.track_scene_set,
        args.vehicle_material_slice,
        args.output_dir,
        source_bffs=args.source_bff,
        environment_cube_dds=args.environment_cube_dds,
        validator=args.validator,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
