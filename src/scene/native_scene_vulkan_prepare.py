"""Prepare SHIFT.NativeSceneVulkanSet/1 for a future native_runtime scene-set loader."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from vulkan_draw_bundle_prepare import prepare_vulkan_draw_bundle

FORMAT = "SHIFT.NativeSceneVulkanSetPrepare/1"
SET_FORMAT = "SHIFT.NativeSceneVulkanSet/1"
TRANSFORM_BLOCKER_SUFFIX = ":scene-world-transform-not-executed"


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


def prepare_native_scene_vulkan_set(
    bundle_set_dir: str | Path,
    *,
    validator: str | None = None,
    output: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(bundle_set_dir)
    manifest_path = root / "bundle_set_manifest.json"
    paths_path = root / "bundle_set.paths"
    output_path = (
        Path(output)
        if output is not None
        else root / "bundle_set_prepare.json"
    )

    blockers: list[str] = []
    manifest: dict[str, Any] | None = None
    if not manifest_path.is_file():
        blockers.append("native-scene-prepare:manifest-missing")
    else:
        try:
            manifest = _load(manifest_path)
        except (OSError, ValueError, TypeError) as error:
            blockers.append(
                "native-scene-prepare:manifest-invalid:"
                + type(error).__name__
            )

    if manifest is not None:
        if manifest.get("format") != SET_FORMAT:
            blockers.append("native-scene-prepare:invalid-format")
        if manifest.get("ready") is not True:
            blockers.extend(
                f"native-scene-prepare:set:{reason}"
                for reason in manifest.get("blocking_reasons")
                or ["not-ready"]
            )

    draw_rows: list[dict[str, Any]] = []
    if manifest is not None:
        raw_draws = manifest.get("draws") or []
        if not isinstance(raw_draws, list) or not raw_draws:
            blockers.append("native-scene-prepare:draws-missing")
        else:
            draw_rows = [
                dict(row)
                for row in raw_draws
                if isinstance(row, Mapping)
            ]
            if len(draw_rows) != len(raw_draws):
                blockers.append("native-scene-prepare:draw-row-invalid")
            expected = int(manifest.get("draw_count") or 0)
            ready_count = int(manifest.get("ready_draw_count") or 0)
            if expected != len(draw_rows):
                blockers.append("native-scene-prepare:draw-count-mismatch")
            if ready_count != len(draw_rows):
                blockers.append("native-scene-prepare:ready-draw-count-mismatch")
            for index, row in enumerate(draw_rows):
                try:
                    draw_order = int(row.get("draw_order"))
                except (TypeError, ValueError):
                    blockers.append(
                        f"native-scene-prepare:draw-order-invalid:{index}"
                    )
                    continue
                if draw_order != index:
                    blockers.append(
                        f"native-scene-prepare:draw-order-not-contiguous:{index}"
                    )
                if row.get("ready") is not True:
                    blockers.append(
                        f"native-scene-prepare:source-draw-not-ready:{index}"
                    )
                bundle = row.get("bundle")
                if not isinstance(bundle, Mapping):
                    blockers.append(
                        f"native-scene-prepare:source-bundle-missing:{index}"
                    )

    native_submission = (
        manifest.get("native_scene_submission") if manifest is not None else {}
    ) or {}
    inherited_native_blockers = [
        str(reason)
        for reason in native_submission.get("blocking_reasons") or []
    ]
    non_transform_native_blockers = [
        reason
        for reason in inherited_native_blockers
        if not reason.endswith(TRANSFORM_BLOCKER_SUFFIX)
    ]
    blockers.extend(
        f"native-scene-prepare:native:{reason}"
        for reason in non_transform_native_blockers
    )

    paths: list[str] = []
    if not paths_path.is_file():
        blockers.append("native-scene-prepare:draw-order-missing")
    else:
        paths = [
            line.strip()
            for line in paths_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(paths) != len(draw_rows):
            blockers.append("native-scene-prepare:draw-order-count-mismatch")

    for index, relative in enumerate(paths):
        if not _safe_relative(relative):
            blockers.append(
                f"native-scene-prepare:unsafe-bundle-path:{index}"
            )
            continue
        if index >= len(draw_rows):
            continue
        bundle = draw_rows[index].get("bundle") or {}
        expected_manifest = str(bundle.get("manifest_path") or "")
        expected_relative = (
            Path(expected_manifest).parent.as_posix()
            if expected_manifest
            else ""
        )
        if relative != expected_relative:
            blockers.append(
                f"native-scene-prepare:draw-order-path-mismatch:{index}"
            )

    prepared_draws: list[dict[str, Any]] = []
    if not blockers:
        for index, relative in enumerate(paths):
            draw = draw_rows[index]
            bundle = draw.get("bundle") or {}
            child = root / relative
            child_manifest = child / "bundle_manifest.json"
            child_blockers: list[str] = []

            if not child_manifest.is_file():
                child_blockers.append("child-manifest-missing")
            else:
                expected_sha = str(
                    bundle.get("manifest_sha256") or ""
                ).lower()
                actual_sha = _sha256(child_manifest)
                if len(expected_sha) != 64 or actual_sha != expected_sha:
                    child_blockers.append("child-manifest-sha256-mismatch")

            child_result: dict[str, Any] | None = None
            if not child_blockers:
                child_result = prepare_vulkan_draw_bundle(
                    child,
                    validator=validator,
                )
                if child_result.get("ready") is not True:
                    child_blockers.extend(
                        str(reason)
                        for reason in child_result.get("blocking_reasons")
                        or ["child-not-ready"]
                    )

            transform = (
                child_result.get("world_transform")
                if child_result is not None
                else None
            )
            if (
                not isinstance(transform, Mapping)
                or transform.get("ready") is not True
                or transform.get("format")
                != "SHIFT.VulkanWorldTransformPacket/1"
            ):
                child_blockers.append("world-transform-not-prepared")

            child_ready = not child_blockers
            if not child_ready:
                blockers.extend(
                    f"native-scene-prepare:draw-{index}:{reason}"
                    for reason in child_blockers
                )

            prepare_path = child / "vulkan_draw_prepare.json"
            prepared_draws.append({
                "draw_order": index,
                "binding_index": draw.get("binding_index"),
                "scene_draw_identity_sha256": draw.get(
                    "scene_draw_identity_sha256"
                ),
                "bundle_path": relative,
                "ready": child_ready,
                "blocking_reasons": list(dict.fromkeys(child_blockers)),
                "manifest_sha256": (
                    _sha256(child_manifest)
                    if child_manifest.is_file()
                    else None
                ),
                "prepare": (
                    {
                        "path": str(prepare_path.relative_to(root)),
                        "sha256": _sha256(prepare_path),
                        "format": (
                            child_result.get("format")
                            if child_result is not None
                            else None
                        ),
                    }
                    if prepare_path.is_file()
                    else None
                ),
                "world_transform": (
                    dict(transform)
                    if isinstance(transform, Mapping)
                    else None
                ),
            })

    blockers = list(dict.fromkeys(blockers))
    ready = (
        bool(draw_rows)
        and len(prepared_draws) == len(draw_rows)
        and all(row.get("ready") is True for row in prepared_draws)
        and not blockers
    )
    result = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "source": {
            "format": manifest.get("format") if manifest is not None else None,
            "manifest_path": str(manifest_path),
            "manifest_sha256": (
                _sha256(manifest_path)
                if manifest_path.is_file()
                else None
            ),
            "draw_order_path": str(paths_path),
            "draw_order_sha256": (
                _sha256(paths_path) if paths_path.is_file() else None
            ),
        },
        "draw_count": len(draw_rows),
        "prepared_draw_count": len(prepared_draws),
        "draws": prepared_draws,
        "resolved_native_blockers": (
            [
                reason
                for reason in inherited_native_blockers
                if reason.endswith(TRANSFORM_BLOCKER_SUFFIX)
            ]
            if ready
            else []
        ),
        "remaining_native_blockers": non_transform_native_blockers,
        "boundary": {
            "ordered_neutral_children_prepared": ready,
            "semantic_affine_svwt_execution_available": True,
            "native_runtime_scene_set_loader_available": True,
            "executes_scene": False,
            "relabels_scene_as_bmw": False,
            "next_stage": (
                "native_runtime --scene-set consumes this prepared contract; "
                "authentic runtime-proven scene evidence remains upstream"
            ),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle_set_dir")
    parser.add_argument("--validator")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    result = prepare_native_scene_vulkan_set(
        args.bundle_set_dir,
        validator=args.validator,
        output=args.output,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
