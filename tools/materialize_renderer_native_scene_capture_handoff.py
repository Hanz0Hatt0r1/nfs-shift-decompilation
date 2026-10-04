#!/usr/bin/env python3
"""Complete the Phase 640 native-scene handoff from existing capture snapshots.

This wrapper never performs a new runtime attribution. It first executes the
existing Phase 640 handoff. Only when that handoff reached the Phase 580/585
renderer-owned-resource boundary does it reuse existing Phase 591 and Phase
590/592 builders against the same Phase 630 capture pipeline, then retries the
existing Phase 580/585 gates with the resulting exact snapshot contracts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.is_dir():
    paths = [SRC]
    paths.extend(sorted(
        (path for path in SRC.rglob("*") if path.is_dir()),
        key=lambda path: (len(path.parts), str(path)),
    ))
    for path in reversed(paths):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)

from materialize_renderer_native_scene_handoff import (
    FORMAT,
    materialize_renderer_native_scene_handoff,
)
from native_scene_external_sampler_capture import (
    build_scene_external_sampler_capture_adapter,
)
from native_scene_instance_transform_match import (
    build_scene_instance_transform_match,
)
from native_scene_vulkan_prepare import prepare_native_scene_vulkan_set
from native_scene_vulkan_set import build_native_scene_vulkan_set

INSTANCE_FORMAT = "SHIFT.NativeSceneInstanceTransformMatch/1"
CAPTURE_ADAPTER_FORMAT = "SHIFT.NativeSceneExternalSamplerCaptureAdapter/1"
SNAPSHOT_FORMAT = "SHIFT.NativeSceneExternalSamplerSnapshots/1"
CUBE_SNAPSHOT_FORMAT = "SHIFT.NativeSceneExternalSamplerCubeSnapshots/1"
VULKAN_SET_FORMAT = "SHIFT.NativeSceneVulkanSet/1"
VULKAN_PREPARE_FORMAT = "SHIFT.NativeSceneVulkanSetPrepare/1"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object expected: {path}")
    return value


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _existing_file(raw: Any) -> Path | None:
    text = str(raw or "").strip()
    if not text:
        return None
    path = Path(text).expanduser()
    return path.resolve() if path.is_file() else None


def _retryable_blockers(base: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    early: list[str] = []
    renderer_resource: list[str] = []
    for raw in base.get("blocking_reasons") or []:
        reason = str(raw)
        if reason.startswith("phase580:") or reason.startswith("phase585:"):
            renderer_resource.append(reason)
        else:
            early.append(reason)
    return early, renderer_resource


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _capture_observations_by_binding(
    capture: Mapping[str, Any],
) -> dict[int, list[Mapping[str, Any]]]:
    by_binding: dict[int, list[Mapping[str, Any]]] = {}
    for resource in capture.get("resource_results") or []:
        if not isinstance(resource, Mapping):
            continue
        for observation in resource.get("attributed_texture_observations") or []:
            if not isinstance(observation, Mapping):
                continue
            binding_index = _safe_int(observation.get("binding_index"))
            if binding_index is None:
                continue
            by_binding.setdefault(binding_index, []).append(observation)
    return by_binding


def _snapshot_runtime_evidence_required(
    capture: Mapping[str, Any],
    capture_adapter: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Describe only snapshot bytes proven missing at an admitted sampler stage.

    Phase 590 intentionally filters its candidate rows to fully captured PPM
    snapshots. A zero candidate count alone therefore cannot distinguish an
    absent SetTexture observation from an observed texture object whose content
    simply was not snapshotted. This diagnostic reuses the compact Phase 573
    draw-local observations and emits a capture requirement only when the exact
    sampler stage and expected D3D9 resource type were already observed.
    """
    observations_by_binding = _capture_observations_by_binding(capture)
    requirements: list[dict[str, Any]] = []

    for field, expected_type, required_path_count in (
        ("rows", "texture2d", 1),
        ("cube_rows", "cube_texture", 6),
    ):
        for raw_row in capture_adapter.get(field) or []:
            if not isinstance(raw_row, Mapping):
                continue
            if raw_row.get("snapshot_ready") is True:
                continue
            if _safe_int(raw_row.get("candidate_observation_count")) != 0:
                continue

            binding_index = _safe_int(raw_row.get("binding_index"))
            register = _safe_int(raw_row.get("register"))
            if binding_index is None or register is None:
                continue

            stage_binding_count = 0
            typed_creation_count = 0
            valid_snapshot_count = 0
            snapshot_status_counts: dict[str, int] = {}
            snapshot_path_counts: list[int] = []
            frames: set[int] = set()
            draw_indices: set[int] = set()

            for observation in observations_by_binding.get(binding_index, []):
                if observation.get("status") != "observed":
                    continue
                for binding in observation.get("active_texture_bindings") or []:
                    if not isinstance(binding, Mapping):
                        continue
                    if _safe_int(binding.get("stage")) != register:
                        continue
                    stage_binding_count += 1
                    creation = binding.get("resource_creation")
                    if (
                        binding.get("resource_creation_status") != "observed"
                        or not isinstance(creation, Mapping)
                        or str(creation.get("resource_type") or "")
                        != expected_type
                    ):
                        continue
                    typed_creation_count += 1
                    status = str(binding.get("snapshot_status") or "missing")
                    snapshot_status_counts[status] = (
                        snapshot_status_counts.get(status, 0) + 1
                    )
                    paths = [
                        path
                        for path in (binding.get("snapshot_paths") or [])
                        if isinstance(path, str) and path
                    ]
                    snapshot_path_counts.append(len(paths))
                    if status == "captured" and len(paths) == required_path_count:
                        valid_snapshot_count += 1
                    frame = _safe_int(observation.get("frame"))
                    draw_index = _safe_int(observation.get("draw_index"))
                    if frame is not None:
                        frames.add(frame)
                    if draw_index is not None:
                        draw_indices.add(draw_index)

            if typed_creation_count == 0 or valid_snapshot_count > 0:
                continue

            captured_but_incomplete = (
                snapshot_status_counts.get("captured", 0) > 0
                and any(count != required_path_count for count in snapshot_path_counts)
            )
            reason = (
                "snapshot-content-incomplete"
                if captured_but_incomplete
                else "snapshot-content-not-captured"
            )
            requirements.append({
                "binding_index": binding_index,
                "draw_order": raw_row.get("draw_order"),
                "register": register,
                "sampler": raw_row.get("sampler"),
                "sampler_type": raw_row.get("sampler_type"),
                "reason": reason,
                "expected_d3d9_resource_type": expected_type,
                "required_snapshot_path_count": required_path_count,
                "stage_binding_observation_count": stage_binding_count,
                "typed_resource_creation_observation_count": typed_creation_count,
                "valid_snapshot_observation_count": valid_snapshot_count,
                "snapshot_status_counts": dict(sorted(snapshot_status_counts.items())),
                "snapshot_path_counts": sorted(snapshot_path_counts),
                "capture_frames": sorted(frames),
                "capture_draw_indices": sorted(draw_indices),
                "requested_texture_stage": register,
                "required_observation": (
                    "exact draw-local SetTexture snapshot content for the "
                    "already observed typed D3D9 resource"
                ),
            })

    requirements.sort(
        key=lambda row: (
            int(row["binding_index"]),
            int(row["register"]),
            str(row.get("sampler_type") or ""),
            _safe_int(row.get("draw_order")) or -1,
        )
    )
    return requirements


def _blocked_completion(
    base: Mapping[str, Any],
    *,
    blockers: list[str],
    capture_root: Path,
    instance_match: Mapping[str, Any] | None = None,
    capture_adapter: Mapping[str, Any] | None = None,
    runtime_evidence_required: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence_required = [
        dict(row) for row in (runtime_evidence_required or [])
    ]
    result = dict(base)
    result["status"] = "blocked"
    result["ready"] = False
    result["scene_set_ready"] = False
    result["blocking_reasons"] = list(dict.fromkeys(blockers))
    boundary = dict(result.get("boundary") or {})
    boundary.update({
        "phase641_existing_capture_completion_attempted": True,
        "phase591_register_semantics_assigned": False,
        "phase590_snapshot_identity_invented": False,
        "manual_scene_instance_selection": False,
        "new_capture_required": False,
        "capture_observation_required": bool(evidence_required),
        "capture_observation_requirement_count": len(evidence_required),
        "capture_observation_requirement_is_exact_stage_type_only": True,
    })
    result["boundary"] = boundary
    result["existing_capture_completion"] = {
        "capture_root": str(capture_root),
        "instance_transform_match": (
            dict(instance_match) if isinstance(instance_match, Mapping) else None
        ),
        "external_sampler_capture": (
            dict(capture_adapter) if isinstance(capture_adapter, Mapping) else None
        ),
        "runtime_evidence_required": evidence_required,
        "retry_performed": False,
    }
    return result


def materialize_renderer_native_scene_capture_handoff(
    *,
    runtime_bootstrap: str | Path,
    renderer_source_bootstrap: str | Path,
    output_dir: str | Path,
    capture_root: str | Path | None,
    environment_cube_dds: str | Path | None = None,
    external_sampler_snapshots: str | Path | None = None,
    external_sampler_cube_snapshots: str | Path | None = None,
    validator: str | None = None,
) -> dict[str, Any]:
    """Run Phase 640, then exhaust Phase 591/590 before leaving sampler blockers."""
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    handoff_path = out / "renderer_native_scene_handoff.json"

    base = materialize_renderer_native_scene_handoff(
        runtime_bootstrap=runtime_bootstrap,
        renderer_source_bootstrap=renderer_source_bootstrap,
        output_dir=out,
        environment_cube_dds=environment_cube_dds,
        external_sampler_snapshots=external_sampler_snapshots,
        external_sampler_cube_snapshots=external_sampler_cube_snapshots,
        validator=validator,
    )
    if base.get("format") != FORMAT:
        raise ValueError(f"base handoff must be {FORMAT}")

    boundary = dict(base.get("boundary") or {})
    boundary["phase641_existing_capture_completion_available"] = True
    base = dict(base)
    base["boundary"] = boundary

    if base.get("ready") is True:
        boundary["phase641_existing_capture_completion_attempted"] = False
        _write(handoff_path, base)
        return base

    # Explicitly supplied runtime resources remain authoritative. Do not replace
    # them with capture-derived resources or mix two identity sources.
    if (
        environment_cube_dds is not None
        or external_sampler_snapshots is not None
        or external_sampler_cube_snapshots is not None
    ):
        boundary["phase641_existing_capture_completion_attempted"] = False
        boundary["explicit_renderer_resource_inputs_authoritative"] = True
        _write(handoff_path, base)
        return base

    early_blockers, retryable = _retryable_blockers(base)
    if early_blockers or not retryable:
        boundary["phase641_existing_capture_completion_attempted"] = False
        boundary["phase641_retry_requires_phase580_or_phase585_boundary"] = True
        _write(handoff_path, base)
        return base

    if capture_root is None:
        boundary["phase641_existing_capture_completion_attempted"] = False
        boundary["phase641_capture_root_required_for_snapshot_materialization"] = True
        _write(handoff_path, base)
        return base
    root = Path(capture_root).expanduser().resolve()

    artifacts = base.get("artifacts") or {}
    inputs = base.get("inputs") or {}
    if not isinstance(artifacts, Mapping):
        artifacts = {}
    if not isinstance(inputs, Mapping):
        inputs = {}
    scene_bundle_path = _existing_file(artifacts.get("native_scene_bundle"))
    bridge_path = _existing_file(artifacts.get("runtime_scene_bridge"))
    capture_path = _existing_file(inputs.get("capture_pipeline"))
    ir_root_text = str(inputs.get("ir_root") or "").strip()
    ir_root = Path(ir_root_text).expanduser().resolve() if ir_root_text else None

    missing: list[str] = []
    if scene_bundle_path is None:
        missing.append("phase641:native-scene-bundle-artifact-missing")
    if bridge_path is None:
        missing.append("phase641:runtime-scene-bridge-artifact-missing")
    if capture_path is None:
        missing.append("phase641:capture-pipeline-artifact-missing")
    if ir_root is None or not (ir_root / "manifest.json").is_file():
        missing.append("phase641:scene-ir-manifest-missing")
    if not root.is_dir():
        missing.append("phase641:capture-root-not-directory")
    if missing:
        result = _blocked_completion(base, blockers=missing, capture_root=root)
        _write(handoff_path, result)
        return result

    assert scene_bundle_path is not None
    assert bridge_path is not None
    assert capture_path is not None
    assert ir_root is not None
    scene_bundle = _load(scene_bundle_path)
    bridge = _load(bridge_path)
    capture = _load(capture_path)

    try:
        instance_match = build_scene_instance_transform_match(
            scene_bundle,
            capture,
        )
    except Exception as exc:
        result = _blocked_completion(
            base,
            blockers=[f"phase591:failed:{type(exc).__name__}:{exc}"],
            capture_root=root,
        )
        _write(handoff_path, result)
        return result
    instance_path = out / "native_scene_instance_transform_match.json"
    _write(instance_path, instance_match)
    if instance_match.get("format") != INSTANCE_FORMAT:
        result = _blocked_completion(
            base,
            blockers=["phase591:format-mismatch"],
            capture_root=root,
            instance_match=instance_match,
        )
        _write(handoff_path, result)
        return result

    try:
        capture_adapter = build_scene_external_sampler_capture_adapter(
            scene_bundle,
            bridge,
            capture,
            capture_root=root,
            instance_transform_match=instance_match,
        )
    except Exception as exc:
        result = _blocked_completion(
            base,
            blockers=[f"phase590:failed:{type(exc).__name__}:{exc}"],
            capture_root=root,
            instance_match=instance_match,
        )
        _write(handoff_path, result)
        return result
    capture_adapter_path = out / "native_scene_external_sampler_capture.json"
    _write(capture_adapter_path, capture_adapter)

    if (
        capture_adapter.get("format") != CAPTURE_ADAPTER_FORMAT
        or capture_adapter.get("ready") is not True
    ):
        blockers = [
            f"phase590:{reason}"
            for reason in capture_adapter.get("blocking_reasons") or ["not-ready"]
        ]
        # Phase 591 diagnostics are useful only when the capture adapter could
        # not resolve a repeated scene binding. They are never promoted into a
        # blocker on their own for unrelated repeated bindings.
        if any("scene-draw-ambiguous" in reason for reason in blockers):
            blockers.extend(
                f"phase591:{reason}"
                for reason in instance_match.get("blocking_reasons") or []
            )
        runtime_evidence_required = _snapshot_runtime_evidence_required(
            capture,
            capture_adapter,
        )
        blockers.extend(
            "phase590:runtime-evidence-required:"
            f"binding-{row['binding_index']}:s{row['register']}:"
            f"{row['sampler_type']}:{row['reason']}"
            for row in runtime_evidence_required
        )
        result = _blocked_completion(
            base,
            blockers=blockers,
            capture_root=root,
            instance_match=instance_match,
            capture_adapter=capture_adapter,
            runtime_evidence_required=runtime_evidence_required,
        )
        _write(handoff_path, result)
        return result

    snapshot_contract = capture_adapter.get("snapshot_contract")
    cube_snapshot_contract = capture_adapter.get("cube_snapshot_contract")
    if not isinstance(snapshot_contract, Mapping):
        snapshot_contract = None
    if not isinstance(cube_snapshot_contract, Mapping):
        cube_snapshot_contract = None

    snapshot_path = out / "native_scene_external_sampler_snapshots.json"
    cube_snapshot_path = out / "native_scene_external_sampler_cube_snapshots.json"
    if snapshot_contract is not None:
        if snapshot_contract.get("format") != SNAPSHOT_FORMAT:
            result = _blocked_completion(
                base,
                blockers=["phase590:snapshot-contract-format-mismatch"],
                capture_root=root,
                instance_match=instance_match,
                capture_adapter=capture_adapter,
            )
            _write(handoff_path, result)
            return result
        _write(snapshot_path, snapshot_contract)
    if cube_snapshot_contract is not None:
        if cube_snapshot_contract.get("format") != CUBE_SNAPSHOT_FORMAT:
            result = _blocked_completion(
                base,
                blockers=["phase592:cube-snapshot-contract-format-mismatch"],
                capture_root=root,
                instance_match=instance_match,
                capture_adapter=capture_adapter,
            )
            _write(handoff_path, result)
            return result
        _write(cube_snapshot_path, cube_snapshot_contract)

    retry_dir = out / "native-scene-vulkan-existing-capture"
    try:
        vulkan_set = build_native_scene_vulkan_set(
            scene_bundle,
            bridge,
            ir_root,
            retry_dir,
            external_sampler_snapshots=snapshot_contract,
            external_sampler_cube_snapshots=cube_snapshot_contract,
        )
    except Exception as exc:
        result = _blocked_completion(
            base,
            blockers=[f"phase580-retry:failed:{type(exc).__name__}:{exc}"],
            capture_root=root,
            instance_match=instance_match,
            capture_adapter=capture_adapter,
        )
        _write(handoff_path, result)
        return result
    if vulkan_set.get("format") != VULKAN_SET_FORMAT or vulkan_set.get("ready") is not True:
        result = _blocked_completion(
            base,
            blockers=[
                f"phase580-retry:{reason}"
                for reason in vulkan_set.get("blocking_reasons") or ["not-ready"]
            ],
            capture_root=root,
            instance_match=instance_match,
            capture_adapter=capture_adapter,
        )
        _write(handoff_path, result)
        return result

    try:
        prepare = prepare_native_scene_vulkan_set(
            retry_dir,
            validator=validator,
        )
    except Exception as exc:
        result = _blocked_completion(
            base,
            blockers=[f"phase585-retry:failed:{type(exc).__name__}:{exc}"],
            capture_root=root,
            instance_match=instance_match,
            capture_adapter=capture_adapter,
        )
        _write(handoff_path, result)
        return result
    if prepare.get("format") != VULKAN_PREPARE_FORMAT or prepare.get("ready") is not True:
        result = _blocked_completion(
            base,
            blockers=[
                f"phase585-retry:{reason}"
                for reason in prepare.get("blocking_reasons") or ["not-ready"]
            ],
            capture_root=root,
            instance_match=instance_match,
            capture_adapter=capture_adapter,
        )
        _write(handoff_path, result)
        return result

    result = dict(base)
    result["status"] = "ready"
    result["ready"] = True
    result["scene_set_ready"] = True
    result["blocking_reasons"] = []
    result_artifacts = dict(result.get("artifacts") or {})
    result_artifacts.update({
        "scene_instance_transform_match": str(instance_path),
        "external_sampler_capture": str(capture_adapter_path),
        "external_sampler_snapshots": (
            str(snapshot_path) if snapshot_path.is_file() else None
        ),
        "external_sampler_cube_snapshots": (
            str(cube_snapshot_path) if cube_snapshot_path.is_file() else None
        ),
        "scene_set_dir": str(retry_dir),
        "scene_set_manifest": str(retry_dir / "bundle_set_manifest.json"),
        "scene_set_prepare": str(retry_dir / "bundle_set_prepare.json"),
    })
    result["artifacts"] = result_artifacts
    boundary = dict(result.get("boundary") or {})
    boundary.update({
        "phase641_existing_capture_completion_attempted": True,
        "phase641_existing_capture_completion_ready": True,
        "phase591_register_semantics_assigned": False,
        "phase590_snapshot_identity_invented": False,
        "manual_scene_instance_selection": False,
        "new_capture_required": False,
        "capture_observation_required": False,
        "capture_observation_requirement_count": 0,
    })
    result["boundary"] = boundary
    result["existing_capture_completion"] = {
        "capture_root": str(root),
        "instance_transform_match": dict(instance_match),
        "external_sampler_capture": dict(capture_adapter),
        "runtime_evidence_required": [],
        "retry_performed": True,
        "phase580_retry": {
            "format": vulkan_set.get("format"),
            "ready": vulkan_set.get("ready") is True,
            "native_scene_submission": dict(
                vulkan_set.get("native_scene_submission") or {}
            ),
        },
        "phase585_retry": {
            "format": prepare.get("format"),
            "ready": prepare.get("ready") is True,
            "blocking_reasons": list(prepare.get("blocking_reasons") or []),
        },
    }
    _write(handoff_path, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-bootstrap", required=True)
    parser.add_argument("--renderer-source-bootstrap", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--capture-root")
    parser.add_argument("--environment-cube-dds")
    parser.add_argument("--external-sampler-snapshots")
    parser.add_argument("--external-sampler-cube-snapshots")
    parser.add_argument("--validator")
    args = parser.parse_args(argv)
    report = materialize_renderer_native_scene_capture_handoff(
        runtime_bootstrap=args.runtime_bootstrap,
        renderer_source_bootstrap=args.renderer_source_bootstrap,
        output_dir=args.output_dir,
        capture_root=args.capture_root,
        environment_cube_dds=args.environment_cube_dds,
        external_sampler_snapshots=args.external_sampler_snapshots,
        external_sampler_cube_snapshots=args.external_sampler_cube_snapshots,
        validator=args.validator,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "scene_set_ready": report["scene_set_ready"],
        "blocking_reasons": report["blocking_reasons"],
        "artifacts": report["artifacts"],
        "existing_capture_completion": report.get("existing_capture_completion"),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
