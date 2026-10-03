#!/usr/bin/env python3
"""Materialize a runtime-proven native scene from regenerated renderer evidence.

This stage connects already-existing proof contracts only:
Phase 630 compact Phase 572 results -> Phase 574 shader admission ->
Phase 576/577 RenderCommand provenance -> Phase 578 NativeSceneBundle ->
Phase 580 NativeSceneVulkanSet -> Phase 585 native prepare.

It never promotes static uniqueness to runtime proof. The Phase 572 wrapper is
rehydrated only from exact fields already transported by Phase 630: one exact
resource path/SHA plus byte-for-byte candidate binding result objects.
"""
from __future__ import annotations

import argparse
import hashlib
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

from imb_runtime_shader_admission import build_imb_runtime_shader_admission
from native_scene_bundle import build_native_scene_bundle
from native_scene_vulkan_prepare import prepare_native_scene_vulkan_set
from native_scene_vulkan_set import build_native_scene_vulkan_set
from sgb_render_binding_bridge import build_sgb_render_binding_bridge

FORMAT = "SHIFT.RendererNativeSceneHandoff/1"
SOURCE_FORMAT = "SHIFT.SilverstoneRendererSourceBootstrapProductionRun/1"
SELF_FORMAT = "SHIFT.SilverstoneRendererSelfBootstrapProductionRun/1"
RAW_FORMAT = "SHIFT.SilverstoneRendererRawCaptureBootstrap/1"
TARGET_FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"
CAPTURE_FORMAT = "SHIFT.IMBRuntimeCapturePipeline/1"
MATCH_FORMAT = "SHIFT.IMBRuntimeShaderVariantMatch/1"
ADMISSION_FORMAT = "SHIFT.IMBRuntimeShaderAdmission/1"
BOOTSTRAP_FORMAT = "SHIFT.OfflineRuntimeBootstrap/1"
NATIVE_SCENE_FORMAT = "SHIFT.OfflineNativeSceneBuild/1"
SCENE_ADMISSION_FORMAT = "SHIFT.SGBRenderBindingAdmission/1"
BRIDGE_FORMAT = "SHIFT.SGBRenderBindingBridge/1"
SCENE_BUNDLE_FORMAT = "SHIFT.NativeSceneBundle/1"
VULKAN_SET_FORMAT = "SHIFT.NativeSceneVulkanSet/1"
VULKAN_PREPARE_FORMAT = "SHIFT.NativeSceneVulkanSetPrepare/1"


def _load_map(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"JSON object expected: {path}")
    return value


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _valid_sha256(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _resolve_recorded_file(
    raw: Any,
    *,
    anchor: Path,
    label: str,
) -> tuple[Path | None, list[str]]:
    text = str(raw or "").strip()
    if not text:
        return None, [f"{label}:path-missing"]
    value = Path(text).expanduser()
    candidates = [value]
    if not value.is_absolute():
        candidates.append(anchor / value)
    existing: dict[str, Path] = {}
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_file():
            existing[str(resolved)] = resolved
    if len(existing) == 1:
        return next(iter(existing.values())), []
    if not existing:
        return None, [f"{label}:file-missing:{text}"]
    return None, [
        f"{label}:path-ambiguous:" + ",".join(sorted(existing))
    ]


def _resolve_hashed_artifact(
    row: Any,
    *,
    anchor: Path,
    label: str,
) -> tuple[Path | None, list[str]]:
    if not isinstance(row, Mapping):
        return None, [f"{label}:artifact-record-missing"]
    path, blockers = _resolve_recorded_file(
        row.get("path"), anchor=anchor, label=label
    )
    if path is None or blockers:
        return None, blockers
    expected = _valid_sha256(row.get("sha256"))
    if expected is None:
        return None, [f"{label}:sha256-missing-or-invalid"]
    actual = _sha256(path)
    if actual != expected:
        return None, [
            f"{label}:sha256-mismatch:expected-{expected}:actual-{actual}"
        ]
    return path, []


def _resolve_renderer_inputs(
    source_path: Path,
) -> tuple[Path | None, Path | None, list[str]]:
    blockers: list[str] = []
    try:
        source = _load_map(source_path)
    except Exception as exc:
        return None, None, [
            f"renderer-source:unreadable:{type(exc).__name__}:{exc}"
        ]
    if source.get("format") != SOURCE_FORMAT:
        blockers.append("renderer-source:format-mismatch")
    if source.get("ready") is not True:
        blockers.append("renderer-source:not-ready")

    shader = source.get("shader_targets") or {}
    if not isinstance(shader, Mapping):
        shader = {}
    target_path, reasons = _resolve_recorded_file(
        shader.get("path"),
        anchor=source_path.parent,
        label="renderer-source:shader-targets",
    )
    blockers.extend(reasons)

    self_row = source.get("self_bootstrap") or {}
    if not isinstance(self_row, Mapping):
        self_row = {}
    self_path, reasons = _resolve_recorded_file(
        self_row.get("manifest"),
        anchor=source_path.parent,
        label="renderer-source:self-bootstrap",
    )
    blockers.extend(reasons)
    raw_path: Path | None = None
    capture_path: Path | None = None
    if self_path is not None:
        try:
            self_report = _load_map(self_path)
        except Exception as exc:
            blockers.append(
                f"self-bootstrap:unreadable:{type(exc).__name__}:{exc}"
            )
        else:
            if self_report.get("format") != SELF_FORMAT:
                blockers.append("self-bootstrap:format-mismatch")
            raw = self_report.get("raw_bootstrap") or {}
            if not isinstance(raw, Mapping):
                raw = {}
            raw_path, reasons = _resolve_recorded_file(
                raw.get("manifest"),
                anchor=self_path.parent,
                label="self-bootstrap:raw-bootstrap",
            )
            blockers.extend(reasons)
    if raw_path is not None:
        try:
            raw_report = _load_map(raw_path)
        except Exception as exc:
            blockers.append(
                f"raw-bootstrap:unreadable:{type(exc).__name__}:{exc}"
            )
        else:
            if raw_report.get("format") != RAW_FORMAT:
                blockers.append("raw-bootstrap:format-mismatch")
            outputs = raw_report.get("outputs") or {}
            if not isinstance(outputs, Mapping):
                outputs = {}
            capture_path, reasons = _resolve_recorded_file(
                outputs.get("capture_pipeline"),
                anchor=raw_path.parent,
                label="raw-bootstrap:capture-pipeline",
            )
            blockers.extend(reasons)
    return target_path, capture_path, list(dict.fromkeys(blockers))


def _resolve_static_scene_inputs(
    bootstrap_path: Path,
) -> tuple[Path | None, Path | None, list[str]]:
    blockers: list[str] = []
    try:
        bootstrap = _load_map(bootstrap_path)
    except Exception as exc:
        return None, None, [
            f"runtime-bootstrap:unreadable:{type(exc).__name__}:{exc}"
        ]
    if bootstrap.get("format") != BOOTSTRAP_FORMAT:
        blockers.append("runtime-bootstrap:format-mismatch")
    if bootstrap.get("offline_build_ready") is not True:
        blockers.append("runtime-bootstrap:offline-build-not-ready")
    artifacts = bootstrap.get("artifacts") or {}
    if not isinstance(artifacts, Mapping):
        artifacts = {}
    native_path, reasons = _resolve_recorded_file(
        artifacts.get("native_scene"),
        anchor=bootstrap_path.parent,
        label="runtime-bootstrap:native-scene",
    )
    blockers.extend(reasons)
    scene_ir_path, reasons = _resolve_recorded_file(
        artifacts.get("scene_ir"),
        anchor=bootstrap_path.parent,
        label="runtime-bootstrap:scene-ir",
    )
    blockers.extend(reasons)

    scene_admission_path: Path | None = None
    if native_path is not None:
        try:
            native = _load_map(native_path)
        except Exception as exc:
            blockers.append(
                f"native-scene:unreadable:{type(exc).__name__}:{exc}"
            )
        else:
            if native.get("format") != NATIVE_SCENE_FORMAT:
                blockers.append("native-scene:format-mismatch")
            if native.get("static_resource_ready") is not True:
                blockers.append("native-scene:static-resource-not-ready")
            native_artifacts = native.get("artifacts") or {}
            if not isinstance(native_artifacts, Mapping):
                native_artifacts = {}
            scene_admission_path, reasons = _resolve_hashed_artifact(
                native_artifacts.get("render_binding_admission"),
                anchor=native_path.parent,
                label="native-scene:render-binding-admission",
            )
            blockers.extend(reasons)

    ir_root: Path | None = None
    if scene_ir_path is not None:
        candidate = scene_ir_path.parent
        if not (candidate / "manifest.json").is_file():
            blockers.append(
                f"runtime-bootstrap:scene-ir:manifest-missing:{candidate / 'manifest.json'}"
            )
        else:
            ir_root = candidate
    return scene_admission_path, ir_root, list(dict.fromkeys(blockers))


def _rehydrate_phase572_matches(
    capture: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    blockers: list[str] = []
    reports: list[dict[str, Any]] = []
    if capture.get("format") != CAPTURE_FORMAT:
        return [], ["capture-pipeline:format-mismatch"]
    if capture.get("pipeline_ready") is not True:
        blockers.append("capture-pipeline:not-ready")

    for resource_index, resource in enumerate(capture.get("resource_results") or []):
        if not isinstance(resource, Mapping):
            blockers.append(f"capture-pipeline:resource-{resource_index}:invalid")
            continue
        resource_path = str(resource.get("resource_path") or "")
        resource_sha = _valid_sha256(resource.get("resource_sha256"))
        match = resource.get("variant_match") or {}
        if not isinstance(match, Mapping):
            match = {}
        results = match.get("candidate_binding_results")
        if not isinstance(results, list):
            blockers.append(
                f"capture-pipeline:resource-{resource_index}:candidate-results-missing"
            )
            continue
        if not results:
            continue
        if match.get("format") != MATCH_FORMAT:
            blockers.append(
                f"capture-pipeline:resource-{resource_index}:match-format-mismatch"
            )
            continue
        if not resource_path or resource_sha is None:
            blockers.append(
                f"capture-pipeline:resource-{resource_index}:resource-identity-invalid"
            )
            continue
        candidate_indices = resource.get("candidate_binding_indices") or []
        try:
            allowed = {int(value) for value in candidate_indices}
        except (TypeError, ValueError):
            blockers.append(
                f"capture-pipeline:resource-{resource_index}:candidate-indices-invalid"
            )
            continue
        copied: list[dict[str, Any]] = []
        for row_index, row in enumerate(results):
            if not isinstance(row, Mapping):
                blockers.append(
                    f"capture-pipeline:resource-{resource_index}:result-{row_index}:invalid"
                )
                continue
            try:
                binding_index = int(row.get("binding_index"))
            except (TypeError, ValueError):
                blockers.append(
                    f"capture-pipeline:resource-{resource_index}:result-{row_index}:binding-index-invalid"
                )
                continue
            if binding_index not in allowed:
                blockers.append(
                    f"capture-pipeline:resource-{resource_index}:result-{row_index}:binding-index-not-in-routed-set"
                )
                continue
            copied.append(json.loads(json.dumps(row)))
        expected_count = match.get("candidate_binding_result_count")
        if expected_count is not None:
            try:
                expected = int(expected_count)
            except (TypeError, ValueError):
                blockers.append(
                    f"capture-pipeline:resource-{resource_index}:candidate-result-count-invalid"
                )
            else:
                if expected != len(results):
                    blockers.append(
                        f"capture-pipeline:resource-{resource_index}:candidate-result-count-mismatch"
                    )
        if len(copied) != len(results):
            continue
        reports.append({
            "format": MATCH_FORMAT,
            "version": 1,
            "status": match.get("status"),
            "ready": match.get("ready"),
            "blocking_reasons": list(match.get("blocking_reasons") or []),
            "target_resource": {
                "resource_path": resource_path,
                "resource_sha256": resource_sha,
            },
            "binding_results": copied,
            "boundary": {
                "rehydrated_from_phase630_compact_transport": True,
                "candidate_binding_results_copied_without_mutation": True,
                "target_resource_from_same_phase630_resource_row": True,
                "new_attribution_performed": False,
            },
        })
    if not reports:
        blockers.append("capture-pipeline:no-routed-phase572-results")
    return reports, list(dict.fromkeys(blockers))


def materialize_renderer_native_scene_handoff(
    *,
    runtime_bootstrap: str | Path,
    renderer_source_bootstrap: str | Path,
    output_dir: str | Path,
    environment_cube_dds: str | Path | None = None,
    external_sampler_snapshots: str | Path | None = None,
    external_sampler_cube_snapshots: str | Path | None = None,
    validator: str | None = None,
) -> dict[str, Any]:
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    bootstrap_path = Path(runtime_bootstrap).expanduser().resolve()
    source_path = Path(renderer_source_bootstrap).expanduser().resolve()
    admission_path = out / "imb_runtime_shader_admission.json"
    bridge_path = out / "sgb_render_binding_bridge.runtime.json"
    bundle_path = out / "native_scene_bundle.json"
    set_dir = out / "native-scene-vulkan"
    handoff_path = out / "renderer_native_scene_handoff.json"

    target_path, capture_path, renderer_blockers = _resolve_renderer_inputs(source_path)
    static_admission_path, ir_root, scene_blockers = _resolve_static_scene_inputs(
        bootstrap_path
    )
    blockers = [*renderer_blockers, *scene_blockers]

    target: Mapping[str, Any] | None = None
    capture: Mapping[str, Any] | None = None
    static_admission: Mapping[str, Any] | None = None
    if target_path is not None:
        try:
            target = _load_map(target_path)
        except Exception as exc:
            blockers.append(f"shader-targets:unreadable:{type(exc).__name__}:{exc}")
        else:
            if target.get("format") != TARGET_FORMAT:
                blockers.append("shader-targets:format-mismatch")
            if target.get("capture_ready") is not True:
                blockers.append("shader-targets:not-capture-ready")
    if capture_path is not None:
        try:
            capture = _load_map(capture_path)
        except Exception as exc:
            blockers.append(f"capture-pipeline:unreadable:{type(exc).__name__}:{exc}")
    if static_admission_path is not None:
        try:
            static_admission = _load_map(static_admission_path)
        except Exception as exc:
            blockers.append(f"scene-admission:unreadable:{type(exc).__name__}:{exc}")
        else:
            if static_admission.get("format") != SCENE_ADMISSION_FORMAT:
                blockers.append("scene-admission:format-mismatch")
            if static_admission.get("ready") is not True:
                blockers.append("scene-admission:not-ready")

    matches: list[dict[str, Any]] = []
    if isinstance(capture, Mapping):
        matches, reasons = _rehydrate_phase572_matches(capture)
        blockers.extend(reasons)

    blockers = list(dict.fromkeys(blockers))
    shader_admission: Mapping[str, Any] | None = None
    bridge: Mapping[str, Any] | None = None
    scene_bundle: Mapping[str, Any] | None = None
    vulkan_set: Mapping[str, Any] | None = None
    prepare: Mapping[str, Any] | None = None

    if not blockers and target is not None and matches:
        try:
            shader_admission = build_imb_runtime_shader_admission(target, matches)
        except Exception as exc:
            blockers.append(
                f"phase574:failed:{type(exc).__name__}:{exc}"
            )
        else:
            _write(admission_path, shader_admission)
            admitted_count = int(
                (shader_admission.get("summary") or {}).get("admitted_binding_count") or 0
            )
            if shader_admission.get("format") != ADMISSION_FORMAT:
                blockers.append("phase574:format-mismatch")
            if shader_admission.get("blocking_reasons"):
                blockers.extend(
                    f"phase574:{reason}"
                    for reason in shader_admission.get("blocking_reasons") or []
                )
            if admitted_count <= 0:
                blockers.append("phase574:no-admitted-bindings")

    if (
        not blockers
        and shader_admission is not None
        and static_admission is not None
        and ir_root is not None
    ):
        try:
            bridge = build_sgb_render_binding_bridge(
                static_admission,
                ir_root,
                runtime_shader_admission=shader_admission,
            )
        except Exception as exc:
            blockers.append(f"phase576:failed:{type(exc).__name__}:{exc}")
        else:
            _write(bridge_path, bridge)
            if bridge.get("format") != BRIDGE_FORMAT or bridge.get("ready") is not True:
                blockers.extend(
                    f"phase576:{reason}"
                    for reason in bridge.get("blocking_reasons") or ["not-ready"]
                )

    if not blockers and bridge is not None:
        try:
            scene_bundle = build_native_scene_bundle(bridge)
        except Exception as exc:
            blockers.append(f"phase578:failed:{type(exc).__name__}:{exc}")
        else:
            _write(bundle_path, scene_bundle)
            if (
                scene_bundle.get("format") != SCENE_BUNDLE_FORMAT
                or scene_bundle.get("ready") is not True
            ):
                blockers.extend(
                    f"phase578:{reason}"
                    for reason in scene_bundle.get("blocking_reasons") or ["not-ready"]
                )

    snapshots = None
    cube_snapshots = None
    if external_sampler_snapshots is not None:
        snapshots = _load_map(Path(external_sampler_snapshots).expanduser())
    if external_sampler_cube_snapshots is not None:
        cube_snapshots = _load_map(Path(external_sampler_cube_snapshots).expanduser())

    if not blockers and scene_bundle is not None and bridge is not None and ir_root is not None:
        try:
            vulkan_set = build_native_scene_vulkan_set(
                scene_bundle,
                bridge,
                ir_root,
                set_dir,
                environment_cube_dds=environment_cube_dds,
                external_sampler_snapshots=snapshots,
                external_sampler_cube_snapshots=cube_snapshots,
            )
        except Exception as exc:
            blockers.append(f"phase580:failed:{type(exc).__name__}:{exc}")
        else:
            if vulkan_set.get("format") != VULKAN_SET_FORMAT or vulkan_set.get("ready") is not True:
                blockers.extend(
                    f"phase580:{reason}"
                    for reason in vulkan_set.get("blocking_reasons") or ["not-ready"]
                )

    if not blockers and vulkan_set is not None:
        try:
            prepare = prepare_native_scene_vulkan_set(
                set_dir,
                validator=validator,
            )
        except Exception as exc:
            blockers.append(f"phase585:failed:{type(exc).__name__}:{exc}")
        else:
            if prepare.get("format") != VULKAN_PREPARE_FORMAT or prepare.get("ready") is not True:
                blockers.extend(
                    f"phase585:{reason}"
                    for reason in prepare.get("blocking_reasons") or ["not-ready"]
                )

    blockers = list(dict.fromkeys(str(reason) for reason in blockers))
    scene_set_ready = (
        isinstance(vulkan_set, Mapping)
        and vulkan_set.get("ready") is True
        and isinstance(prepare, Mapping)
        and prepare.get("ready") is True
        and not blockers
    )
    report = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if scene_set_ready else "blocked",
        "ready": scene_set_ready,
        "scene_set_ready": scene_set_ready,
        "blocking_reasons": blockers,
        "inputs": {
            "runtime_bootstrap": str(bootstrap_path),
            "runtime_bootstrap_sha256": _sha256(bootstrap_path) if bootstrap_path.is_file() else None,
            "renderer_source_bootstrap": str(source_path),
            "renderer_source_bootstrap_sha256": _sha256(source_path) if source_path.is_file() else None,
            "runtime_shader_targets": str(target_path) if target_path is not None else None,
            "runtime_shader_targets_sha256": _sha256(target_path) if target_path is not None else None,
            "capture_pipeline": str(capture_path) if capture_path is not None else None,
            "capture_pipeline_sha256": _sha256(capture_path) if capture_path is not None else None,
            "static_render_binding_admission": str(static_admission_path) if static_admission_path is not None else None,
            "static_render_binding_admission_sha256": _sha256(static_admission_path) if static_admission_path is not None else None,
            "ir_root": str(ir_root) if ir_root is not None else None,
        },
        "summary": {
            "rehydrated_phase572_match_count": len(matches),
            "phase574_status": shader_admission.get("status") if isinstance(shader_admission, Mapping) else None,
            "phase574_admitted_binding_count": (
                (shader_admission.get("summary") or {}).get("admitted_binding_count")
                if isinstance(shader_admission, Mapping)
                else None
            ),
            "runtime_bridge_ready": bridge.get("ready") is True if isinstance(bridge, Mapping) else False,
            "native_scene_bundle_ready": scene_bundle.get("ready") is True if isinstance(scene_bundle, Mapping) else False,
            "native_scene_bundle_draw_count": scene_bundle.get("draw_count") if isinstance(scene_bundle, Mapping) else None,
            "native_scene_vulkan_set_ready": vulkan_set.get("ready") is True if isinstance(vulkan_set, Mapping) else False,
            "native_scene_prepare_ready": prepare.get("ready") is True if isinstance(prepare, Mapping) else False,
        },
        "artifacts": {
            "runtime_shader_admission": str(admission_path) if admission_path.is_file() else None,
            "runtime_scene_bridge": str(bridge_path) if bridge_path.is_file() else None,
            "native_scene_bundle": str(bundle_path) if bundle_path.is_file() else None,
            "scene_set_dir": str(set_dir) if (set_dir / "bundle_set_manifest.json").is_file() else None,
            "scene_set_manifest": str(set_dir / "bundle_set_manifest.json") if (set_dir / "bundle_set_manifest.json").is_file() else None,
            "scene_set_prepare": str(set_dir / "bundle_set_prepare.json") if (set_dir / "bundle_set_prepare.json").is_file() else None,
        },
        "diagnostics": {
            "phase574_rejected_bindings": (
                list(shader_admission.get("rejected_bindings") or [])
                if isinstance(shader_admission, Mapping)
                else []
            ),
            "native_scene_bundle_coverage": (
                dict(scene_bundle.get("coverage") or {})
                if isinstance(scene_bundle, Mapping)
                else None
            ),
            "native_scene_submission": (
                dict(vulkan_set.get("native_scene_submission") or {})
                if isinstance(vulkan_set, Mapping)
                else None
            ),
        },
        "boundary": {
            "phase572_candidate_rows_recomputed": False,
            "phase572_candidate_rows_copied_without_mutation": True,
            "phase630_resource_identity_is_phase572_target_identity": True,
            "partial_phase574_admission_can_seed_only_proven_draw_subset": True,
            "unproven_draw_promoted": False,
            "static_unique_shader_promoted": False,
            "runtime_shader_admission_is_render_admission": False,
            "scene_set_ready_requires_phase585_prepare": True,
            "renderer_owned_sampler_invented": False,
            "duplicate_resource_fallback": False,
            "candidate_ranking_is_proof": False,
            "original_game_execution_required": False,
            "new_capture_required": False,
        },
    }
    _write(handoff_path, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-bootstrap", required=True)
    parser.add_argument("--renderer-source-bootstrap", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--environment-cube-dds")
    parser.add_argument("--external-sampler-snapshots")
    parser.add_argument("--external-sampler-cube-snapshots")
    parser.add_argument("--validator")
    args = parser.parse_args(argv)
    report = materialize_renderer_native_scene_handoff(
        runtime_bootstrap=args.runtime_bootstrap,
        renderer_source_bootstrap=args.renderer_source_bootstrap,
        output_dir=args.output_dir,
        environment_cube_dds=args.environment_cube_dds,
        external_sampler_snapshots=args.external_sampler_snapshots,
        external_sampler_cube_snapshots=args.external_sampler_cube_snapshots,
        validator=args.validator,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "scene_set_ready": report["scene_set_ready"],
        "summary": report["summary"],
        "blocking_reasons": report["blocking_reasons"],
        "artifacts": report["artifacts"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
