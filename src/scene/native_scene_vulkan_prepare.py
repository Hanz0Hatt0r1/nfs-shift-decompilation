"""Prepare SHIFT.NativeSceneVulkanSet/1 for native_runtime admission."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from vulkan_bundle_run import run_bmw_vulkan_bundle

FORMAT = "SHIFT.NativeSceneVulkanSetPrepare/1"
SET_FORMAT = "SHIFT.NativeSceneVulkanSet/1"
CHILD_FORMAT = "SHIFT.VulkanDrawBundle/1"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_relative(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def _blocked(reason: str) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "blocked",
        "ready": False,
        "blocking_reasons": [reason],
        "draw_count": 0,
        "draws": [],
    }


def prepare_native_scene_vulkan_set(
    scene_set_dir: str | Path,
    *,
    validator: str | None = None,
    output: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(scene_set_dir)
    manifest_path = root / "bundle_set_manifest.json"
    paths_path = root / "bundle_set.paths"
    output_path = (
        Path(output)
        if output is not None
        else root / "native_scene_set_prepare.json"
    )

    if not manifest_path.is_file():
        result = _blocked("native-scene-prepare:manifest-missing")
    elif not paths_path.is_file():
        result = _blocked("native-scene-prepare:draw-order-missing")
    else:
        try:
            manifest = _load(manifest_path)
        except (OSError, ValueError, TypeError) as error:
            result = _blocked(
                "native-scene-prepare:manifest-invalid:"
                + type(error).__name__
            )
        else:
            blockers: list[str] = []
            if manifest.get("format") != SET_FORMAT:
                blockers.append("native-scene-prepare:invalid-format")
            if manifest.get("ready") is not True:
                blockers.extend(
                    str(reason)
                    for reason in (
                        manifest.get("blocking_reasons")
                        or ["native-scene-prepare:set-not-ready"]
                    )
                )
            native_gate = manifest.get("native_scene_submission") or {}
            if (
                not isinstance(native_gate, Mapping)
                or native_gate.get("ready") is not True
            ):
                blockers.extend(
                    str(reason)
                    for reason in (
                        native_gate.get("blocking_reasons")
                        if isinstance(native_gate, Mapping)
                        else []
                    )
                    or ["native-scene-prepare:native-submission-not-ready"]
                )

            draw_rows = manifest.get("draws") or []
            if not isinstance(draw_rows, list) or not draw_rows:
                blockers.append("native-scene-prepare:draws-missing")
                draw_rows = []

            paths = [
                line.strip()
                for line in paths_path.read_text(
                    encoding="utf-8"
                ).splitlines()
                if line.strip()
            ]
            if len(paths) != len(draw_rows):
                blockers.append(
                    "native-scene-prepare:draw-order-count-mismatch"
                )

            for index, relative in enumerate(paths):
                if not _safe_relative(relative):
                    blockers.append(
                        f"native-scene-prepare:unsafe-bundle-path:{index}"
                    )
                    continue
                if index >= len(draw_rows):
                    continue
                row = draw_rows[index]
                if not isinstance(row, Mapping):
                    blockers.append(
                        f"native-scene-prepare:draw-invalid:{index}"
                    )
                    continue
                if row.get("ready") is not True:
                    blockers.append(
                        f"native-scene-prepare:draw-not-ready:{index}"
                    )
                    continue
                bundle = row.get("bundle") or {}
                manifest_rel = str(
                    bundle.get("manifest_path") or ""
                )
                expected = (
                    str(Path(manifest_rel).parent)
                    if manifest_rel
                    else ""
                )
                if relative != expected:
                    blockers.append(
                        "native-scene-prepare:draw-order-path-mismatch:"
                        + str(index)
                    )

            prepared: list[dict[str, Any]] = []
            if not blockers:
                for index, relative in enumerate(paths):
                    child = root / relative
                    child_manifest_path = child / "bundle_manifest.json"
                    child_blockers: list[str] = []
                    try:
                        child_manifest = _load(child_manifest_path)
                    except (OSError, ValueError, TypeError) as error:
                        child_manifest = {}
                        child_blockers.append(
                            "child-manifest-invalid:"
                            + type(error).__name__
                        )
                    if child_manifest.get("format") != CHILD_FORMAT:
                        child_blockers.append(
                            "child-manifest-not-neutral-vulkan-draw"
                        )
                    if child_manifest.get("ready") is not True:
                        child_blockers.extend(
                            str(reason)
                            for reason in (
                                child_manifest.get("blocking_reasons")
                                or ["child-manifest-not-ready"]
                            )
                        )

                    world = child / "world_transform.svwt"
                    scene_transform = (
                        child_manifest.get("scene_transform") or {}
                    )
                    world_required = (
                        isinstance(scene_transform, Mapping)
                        and scene_transform.get("world_matrix") is not None
                    )
                    if world_required and not world.is_file():
                        child_blockers.append(
                            "world-transform-packet-missing"
                        )

                    child_result: dict[str, Any] = {
                        "status": "blocked",
                        "ready": False,
                        "blocking_reasons": child_blockers,
                    }
                    if not child_blockers:
                        child_result = run_bmw_vulkan_bundle(
                            child,
                            validator=validator,
                            prepare_only=True,
                        )
                        child_blockers.extend(
                            str(reason)
                            for reason in (
                                child_result.get("blocking_reasons") or []
                            )
                        )

                    child_ready = (
                        not child_blockers
                        and child_result.get("ready") is True
                        and child_result.get("status") == "ready"
                    )
                    spirv = child / "spirv_report.json"
                    interface = child / "vulkan_interface.json"
                    if child_ready and not spirv.is_file():
                        child_ready = False
                        child_blockers.append(
                            "spirv-report-missing"
                        )
                    if child_ready and not interface.is_file():
                        child_ready = False
                        child_blockers.append(
                            "interface-report-missing"
                        )
                    if not child_ready:
                        blockers.extend(
                            f"native-scene-prepare:draw-{index}:{reason}"
                            for reason in (
                                child_blockers or ["not-ready"]
                            )
                        )

                    source_row = draw_rows[index]
                    prepared.append({
                        "draw_order": index,
                        "binding_index": source_row.get(
                            "binding_index"
                        ),
                        "bundle_path": relative,
                        "ready": child_ready,
                        "status": child_result.get("status"),
                        "blocking_reasons": list(
                            dict.fromkeys(child_blockers)
                        ),
                        "scene_draw_identity_sha256": (
                            source_row.get(
                                "scene_draw_identity_sha256"
                            )
                        ),
                        "world_transform": (
                            {
                                "path": str(world.relative_to(root)),
                                "sha256": _sha256(world),
                            }
                            if world.is_file()
                            else None
                        ),
                        "spirv_report": (
                            {
                                "path": str(spirv.relative_to(root)),
                                "sha256": _sha256(spirv),
                            }
                            if spirv.is_file()
                            else None
                        ),
                        "interface_report": (
                            {
                                "path": str(
                                    interface.relative_to(root)
                                ),
                                "sha256": _sha256(interface),
                            }
                            if interface.is_file()
                            else None
                        ),
                    })

            result = {
                "format": FORMAT,
                "version": 1,
                "status": "ready" if not blockers else "blocked",
                "ready": not blockers,
                "blocking_reasons": list(
                    dict.fromkeys(blockers)
                ),
                "source": {
                    "format": manifest.get("format"),
                    "manifest_path": str(manifest_path),
                    "manifest_sha256": _sha256(manifest_path),
                    "draw_order_path": str(paths_path),
                    "draw_order_sha256": _sha256(paths_path),
                },
                "draw_count": len(prepared),
                "draws": prepared,
                "boundary": {
                    "child_bundle_format": CHILD_FORMAT,
                    "child_spirv_interface_gates_reused": True,
                    "world_transform_execution": (
                        "native-runtime-affine-semantic-v3"
                    ),
                    "external_runtime_resources_synthesized": False,
                    "bmw_bundle_set_equivalence": False,
                },
            }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene_set_dir")
    parser.add_argument("--validator")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    result = prepare_native_scene_vulkan_set(
        args.scene_set_dir,
        validator=args.validator,
        output=args.output,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
