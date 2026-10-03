#!/usr/bin/env python3
"""Regenerate the optional Phase 595 OBJECT candidate join from proven artifacts.

This helper resolves the source-backed scene artifacts already persisted by
SHIFT.OfflineRuntimeBootstrap/1, verifies the native-scene artifact hashes, and
feeds the regenerated Phase 630 capture pipeline into the existing Phase 595
builder. It never promotes a candidate to render admission or portable OBJECT
identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / "src" / "scene"
if str(SCENE) not in sys.path:
    sys.path.insert(0, str(SCENE))

from sgb_runtime_object_candidate_join import validate_files

FORMAT = "SHIFT.SilverstoneRendererObjectCandidateRegeneration/1"
RUNTIME_BOOTSTRAP_FORMAT = "SHIFT.OfflineRuntimeBootstrap/1"
NATIVE_SCENE_FORMAT = "SHIFT.OfflineNativeSceneBuild/1"


def _load_json_map(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"JSON object expected: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_recorded_path(
    value: Any,
    *,
    anchor: Path,
    label: str,
) -> tuple[Path | None, list[str]]:
    text = str(value or "").strip()
    if not text:
        return None, [f"{label}:path-missing"]
    raw = Path(text).expanduser()
    candidates = [raw]
    if not raw.is_absolute():
        candidates.append(anchor / raw)

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
        f"{label}:relative-path-ambiguous:" + ",".join(sorted(existing))
    ]


def _resolve_native_scene_artifact(
    artifacts: Mapping[str, Any],
    key: str,
    *,
    anchor: Path,
) -> tuple[Path | None, list[str]]:
    row = artifacts.get(key)
    if not isinstance(row, Mapping):
        return None, [f"native-scene:{key}:artifact-record-missing"]
    path, blockers = _resolve_recorded_path(
        row.get("path"),
        anchor=anchor,
        label=f"native-scene:{key}",
    )
    if blockers or path is None:
        return None, blockers
    expected = str(row.get("sha256") or "").strip().lower()
    if len(expected) != 64:
        return None, [f"native-scene:{key}:sha256-missing-or-invalid"]
    actual = _sha256(path)
    if actual != expected:
        return None, [
            f"native-scene:{key}:sha256-mismatch:expected-{expected}:actual-{actual}"
        ]
    return path, []


def regenerate_object_candidate_join(
    *,
    runtime_bootstrap: str | Path,
    capture_pipeline: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Regenerate Phase 595 from exact persisted scene + capture artifacts."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "renderer_object_candidate_regeneration.json"
    join_path = out / "sgb_runtime_object_candidate_join.json"

    blockers: list[str] = []
    bootstrap_path = Path(runtime_bootstrap).expanduser()
    capture_path = Path(capture_pipeline).expanduser()
    bootstrap: Mapping[str, Any] | None = None
    native_scene: Mapping[str, Any] | None = None
    scene_placement_path: Path | None = None
    object_handoffs_path: Path | None = None
    ir_root: Path | None = None

    try:
        bootstrap = _load_json_map(bootstrap_path)
    except Exception as exc:
        blockers.append(
            f"runtime-bootstrap:unreadable:{type(exc).__name__}:{exc}"
        )
    if isinstance(bootstrap, Mapping):
        if bootstrap.get("format") != RUNTIME_BOOTSTRAP_FORMAT:
            blockers.append(
                "runtime-bootstrap:format-mismatch:"
                f"{bootstrap.get('format')!r}:expected-{RUNTIME_BOOTSTRAP_FORMAT}"
            )
        if bootstrap.get("offline_build_ready") is not True:
            blockers.append("runtime-bootstrap:offline-build-not-ready")

        artifacts = bootstrap.get("artifacts")
        if not isinstance(artifacts, Mapping):
            blockers.append("runtime-bootstrap:artifacts-missing")
        else:
            native_scene_path, reasons = _resolve_recorded_path(
                artifacts.get("native_scene"),
                anchor=bootstrap_path.parent,
                label="runtime-bootstrap:native-scene",
            )
            blockers.extend(reasons)
            scene_ir_report, reasons = _resolve_recorded_path(
                artifacts.get("scene_ir"),
                anchor=bootstrap_path.parent,
                label="runtime-bootstrap:scene-ir",
            )
            blockers.extend(reasons)
            if scene_ir_report is not None:
                candidate_ir_root = scene_ir_report.parent
                if not (candidate_ir_root / "manifest.json").is_file():
                    blockers.append(
                        "runtime-bootstrap:scene-ir:manifest-json-missing:"
                        f"{candidate_ir_root / 'manifest.json'}"
                    )
                else:
                    ir_root = candidate_ir_root

            if native_scene_path is not None:
                try:
                    native_scene = _load_json_map(native_scene_path)
                except Exception as exc:
                    blockers.append(
                        "native-scene:unreadable:"
                        f"{type(exc).__name__}:{exc}"
                    )
                if isinstance(native_scene, Mapping):
                    if native_scene.get("format") != NATIVE_SCENE_FORMAT:
                        blockers.append(
                            "native-scene:format-mismatch:"
                            f"{native_scene.get('format')!r}:expected-{NATIVE_SCENE_FORMAT}"
                        )
                    if native_scene.get("static_resource_ready") is not True:
                        blockers.append("native-scene:static-resource-not-ready")
                    native_artifacts = native_scene.get("artifacts")
                    if not isinstance(native_artifacts, Mapping):
                        blockers.append("native-scene:artifacts-missing")
                    else:
                        scene_placement_path, reasons = _resolve_native_scene_artifact(
                            native_artifacts,
                            "scene_placement",
                            anchor=native_scene_path.parent,
                        )
                        blockers.extend(reasons)
                        object_handoffs_path, reasons = _resolve_native_scene_artifact(
                            native_artifacts,
                            "object_render_handoffs",
                            anchor=native_scene_path.parent,
                        )
                        blockers.extend(reasons)

    if not capture_path.is_file():
        blockers.append(f"capture-pipeline:file-missing:{capture_path}")

    blockers = list(dict.fromkeys(blockers))
    source_ready = not blockers
    join: Mapping[str, Any] | None = None
    if source_ready:
        assert scene_placement_path is not None
        assert object_handoffs_path is not None
        assert ir_root is not None
        try:
            join = validate_files(
                scene_placement_path,
                object_handoffs_path,
                capture_path,
                ir_root,
            )
        except Exception as exc:
            blockers.append(
                f"object-candidate-join:failed:{type(exc).__name__}:{exc}"
            )
            source_ready = False
        else:
            if not isinstance(join, Mapping):
                blockers.append("object-candidate-join:invalid-report")
                source_ready = False
                join = None

    join_ready = isinstance(join, Mapping) and join.get("ready") is True
    if isinstance(join, Mapping):
        join_path.write_text(
            json.dumps(dict(join), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        if not join_ready:
            blockers.extend(
                f"object-candidate-join:{reason}"
                for reason in (join.get("blocking_reasons") or ["not-ready"])
            )
    elif join_path.exists():
        join_path.unlink()

    blockers = list(dict.fromkeys(str(value) for value in blockers))
    if not source_ready:
        status = "blocked"
    elif join_ready:
        status = "ready"
    else:
        status = "optional-unresolved"

    report = {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "source_ready": source_ready,
        "ready": join_ready,
        "runtime_bootstrap": str(bootstrap_path),
        "capture_pipeline": str(capture_path),
        "resolved_inputs": {
            "scene_placement": (
                str(scene_placement_path) if scene_placement_path is not None else None
            ),
            "object_render_handoffs": (
                str(object_handoffs_path) if object_handoffs_path is not None else None
            ),
            "ir_root": str(ir_root) if ir_root is not None else None,
        },
        "outputs": {
            "object_candidate_join": str(join_path) if isinstance(join, Mapping) else None,
        },
        "join": {
            "format": join.get("format") if isinstance(join, Mapping) else None,
            "status": join.get("status") if isinstance(join, Mapping) else None,
            "identity_complete": (
                join.get("identity_complete") if isinstance(join, Mapping) else None
            ),
            "runtime_resource_count": (
                join.get("runtime_resource_count") if isinstance(join, Mapping) else None
            ),
            "matched_runtime_resource_count": (
                join.get("matched_runtime_resource_count")
                if isinstance(join, Mapping)
                else None
            ),
        },
        "blocking_reasons": blockers,
        "boundary": {
            "existing_phase595_builder_reused": True,
            "native_scene_artifact_sha256_required": True,
            "runtime_capture_pipeline_reused_exactly": True,
            "unique_candidate_is_portable_resource_identity": False,
            "unique_candidate_is_runtime_object_identity": False,
            "unique_candidate_is_render_admission": False,
            "candidate_ranking_is_proof": False,
            "missing_resource_substitution": False,
        },
    }
    manifest_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-bootstrap", required=True)
    parser.add_argument("--capture-pipeline", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    report = regenerate_object_candidate_join(
        runtime_bootstrap=args.runtime_bootstrap,
        capture_pipeline=args.capture_pipeline,
        output_dir=args.output_dir,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "source_ready": report["source_ready"],
        "ready": report["ready"],
        "outputs": report["outputs"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["source_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
