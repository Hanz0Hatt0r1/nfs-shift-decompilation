"""Build the strongest static native scene artifact directly from an offline corpus.

The orchestrator deliberately composes existing fail-closed stages instead of
adding new parsing or identity rules:

BFF/ZIP/directory corpus
 -> SHIFT.OfflineSceneIRMaterialization/1
 -> SHIFT.OfflineSceneRootIRJoin/1
 -> SHIFT.OfflineNativeSceneBuild/1

The final stage still stops before runtime-proven draw admission, so this module
never claims that the native scene is runtime ready.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from offline_native_scene import (
    FORMAT as NATIVE_SCENE_FORMAT,
    RUNTIME_DRAW_BLOCKER,
    build_native_scene_files,
)
from offline_scene_ir import FORMAT as SCENE_IR_FORMAT, build_scene_ir
from offline_scene_root_ir import FORMAT as SCENE_ROOT_FORMAT, build_scene_root_ir_join

FORMAT = "SHIFT.OfflineNativeSceneCorpusBuild/1"


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _blocked_root(reason: str) -> dict[str, Any]:
    return {
        "format": SCENE_ROOT_FORMAT,
        "version": 1,
        "status": "blocked",
        "ready": False,
        "blocking_reasons": [reason],
        "raw_sgb_path": None,
        "boundary": {
            "bootstrap_root_identity": "not-evaluated",
            "basename_fallback": False,
            "similar_path_fallback": False,
            "first_duplicate_wins": False,
            "missing_resource_synthesis": False,
        },
    }


def _blocked_native_scene(reason: str) -> dict[str, Any]:
    return {
        "format": NATIVE_SCENE_FORMAT,
        "version": 1,
        "status": "static-resource-blocked",
        "static_resource_ready": False,
        "native_scene_runtime_ready": False,
        "blocking_reasons": [reason, RUNTIME_DRAW_BLOCKER],
        "stages": {},
        "summary": {},
        "boundary": {
            "upstream_scene_corpus_gate_ready": False,
            "runtime_proven_draw_required_for_native_scene_bundle": True,
            "provenance_gate_bypass": False,
        },
    }


def build_native_scene_corpus_files(
    inputs: Sequence[str | Path],
    catalog_path: str | Path,
    bootstrap_path: str | Path,
    output_dir: str | Path,
    *,
    root_consensus_path: str | Path | None = None,
    runtime_shader_admission_path: str | Path | None = None,
    fail_fast: bool = False,
) -> dict[str, Any]:
    """Materialize scene IR, select the exact SGB root, then build static scene data."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ir_root = out / "ir"

    catalog = _load(catalog_path)
    bootstrap = _load(bootstrap_path)
    scene_ir = build_scene_ir(
        inputs,
        ir_root,
        fail_fast=fail_fast,
    )

    if scene_ir.get("ready") is True:
        try:
            scene_root = build_scene_root_ir_join(catalog, bootstrap, ir_root)
        except (OSError, ValueError) as exc:
            scene_root = _blocked_root(
                f"scene-root-join-error:{type(exc).__name__}:{exc}"
            )
    else:
        scene_root = _blocked_root("scene-ir-not-ready")
    _write(out / "scene_root_ir_join.json", scene_root)

    raw_sgb_path = scene_root.get("raw_sgb_path")
    if scene_root.get("ready") is True and raw_sgb_path:
        try:
            native_scene = build_native_scene_files(
                str(raw_sgb_path),
                ir_root,
                out / "native_scene",
                root_consensus_path=root_consensus_path,
                runtime_shader_admission_path=runtime_shader_admission_path,
            )
        except (OSError, ValueError) as exc:
            native_scene = _blocked_native_scene(
                f"native-scene-build-error:{type(exc).__name__}:{exc}"
            )
    else:
        native_scene = _blocked_native_scene("scene-root-ir-join-not-ready")

    blockers: list[str] = []
    if scene_ir.get("ready") is not True:
        reasons = list(scene_ir.get("blocking_reasons") or ["not-ready"])
        blockers.extend(f"scene-ir:{reason}" for reason in reasons)
    if scene_root.get("ready") is not True:
        reasons = list(scene_root.get("blocking_reasons") or ["not-ready"])
        blockers.extend(f"scene-root:{reason}" for reason in reasons)
    if native_scene.get("static_resource_ready") is not True:
        reasons = [
            str(reason)
            for reason in (native_scene.get("blocking_reasons") or ["not-ready"])
            if str(reason) != RUNTIME_DRAW_BLOCKER
        ]
        blockers.extend(f"native-scene:{reason}" for reason in reasons)
    blockers = list(dict.fromkeys(blockers))

    static_resource_ready = (
        scene_ir.get("ready") is True
        and scene_root.get("ready") is True
        and native_scene.get("static_resource_ready") is True
        and not blockers
    )
    report = {
        "format": FORMAT,
        "version": 1,
        "status": (
            "static-resource-ready-runtime-draw-blocked"
            if static_resource_ready
            else "static-resource-blocked"
        ),
        "static_resource_ready": static_resource_ready,
        "native_scene_runtime_ready": False,
        "blocking_reasons": (
            [RUNTIME_DRAW_BLOCKER]
            if static_resource_ready
            else blockers + [RUNTIME_DRAW_BLOCKER]
        ),
        "stages": {
            "scene_ir": scene_ir,
            "scene_root_ir_join": scene_root,
            "native_scene": native_scene,
        },
        "artifacts": {
            "scene_ir_root": str(ir_root),
            "scene_root_ir_join": str(out / "scene_root_ir_join.json"),
            "native_scene_root": str(out / "native_scene"),
        },
        "boundary": {
            "manual_ir_root_required": False,
            "manual_sgb_path_required": False,
            "scene_ir_identity_admission": "SHIFT.OfflineExactIRResourceClosure/1",
            "scene_root_identity": SCENE_ROOT_FORMAT,
            "runtime_proven_draw_required": True,
            "runtime_draw_evidence_synthesized": False,
            "basename_fallback_is_admission_proof": False,
            "missing_resource_synthesis": False,
            "provenance_gate_bypass": False,
        },
    }
    _write(out / "native_scene_corpus_build.json", report)
    return report
