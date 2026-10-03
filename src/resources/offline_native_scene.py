"""Collapse source-backed SGB scene preparation into one fail-closed offline stage.

The builder consumes a decoded SGB contract (or a raw SGB through the file
wrapper), runs the existing source-backed placement/object/render-binding chain,
and stops before runtime draw admission. Before the legacy render bridge is
allowed to run, every admitted scene resource and its semantic dependency
closure must resolve through the exact-path OfflineExactIRResourceClosure gate.
Static RenderBinding packets are never promoted to NativeSceneBundle draw proof.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from offline_exact_ir_closure import (
    FORMAT as EXACT_IR_CLOSURE_FORMAT,
    build_exact_ir_resource_closure,
)
from sgb_runtime import parse_sgb_runtime
from sgb_placement_join import build_sgb_placement_join
from sgb_scene_placement import build_sgb_scene_placement
from sgb_object_render_handoff import build_sgb_object_render_handoff_set
from sgb_render_binding_admission import build_sgb_render_binding_admission
from sgb_render_binding_bridge import build_sgb_render_binding_bridge

FORMAT = "SHIFT.OfflineNativeSceneBuild/1"
RUNTIME_DRAW_BLOCKER = "runtime:runtime-proven-draw-admission-required"


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage_blockers(name: str, report: Mapping[str, Any]) -> list[str]:
    if report.get("ready") is True:
        return []
    reasons = list(report.get("blocking_reasons") or report.get("blockers") or [])
    if not reasons:
        reasons = ["not-ready"]
    return [f"{name}:{reason}" for reason in reasons]


def _admitted_resource_references(admission: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    for row in admission.get("bindings") or []:
        if not isinstance(row, Mapping):
            continue
        gate = row.get("scene_admission") or {}
        if not isinstance(gate, Mapping):
            gate = {}
        if (
            row.get("ready") is not True
            or gate.get("admitted_to_generic_render_binding") is not True
        ):
            continue
        object_row = row.get("object") or {}
        if not isinstance(object_row, Mapping):
            continue
        ref = object_row.get("resource_reference")
        if ref:
            value = str(ref)
            if value not in refs:
                refs.append(value)
    return refs


def _blocked_exact_closure(reason: str) -> dict[str, Any]:
    return {
        "format": EXACT_IR_CLOSURE_FORMAT,
        "version": 1,
        "status": "blocked",
        "ready": False,
        "blocking_reasons": [reason],
        "root_reference_count": 0,
        "resolved_resource_count": 0,
        "edges": [],
        "resources": [],
        "boundary": {
            "basename_fallback": False,
            "first_duplicate_wins": False,
            "exact_normalized_path_required": True,
            "preflight_executed": False,
        },
    }


def _blocked_bridge(reason: str) -> dict[str, Any]:
    return {
        "format": "SHIFT.SGBRenderBindingBridge/1",
        "version": 1,
        "status": "blocked",
        "ready": False,
        "blocking_reasons": [reason],
        "scene_admitted_instance_count": 0,
        "direct_render_instance_count": 0,
        "resource_adapter_blocked_count": 0,
        "resolved_instance_count": 0,
        "unresolved_instance_count": 0,
        "resource_adapter_blocked": [],
        "skipped_bindings": [],
        "render_binding": None,
        "runtime_shader_join": {},
        "boundary": {
            "legacy_renderer_invoked": False,
            "draw_admission": False,
        },
    }


def build_native_scene(
    sgb_runtime: Mapping[str, Any],
    ir_root: str | Path,
    *,
    root_consensus: Mapping[str, Any] | None = None,
    runtime_shader_admission: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build static scene resource bindings without claiming runtime draw proof."""
    placement_join = build_sgb_placement_join(sgb_runtime)
    scene_placement = build_sgb_scene_placement(placement_join)
    object_handoffs = build_sgb_object_render_handoff_set(
        sgb_runtime,
        root_consensus=root_consensus,
    )
    admission = build_sgb_render_binding_admission(scene_placement, object_handoffs)

    admitted_refs = _admitted_resource_references(admission)
    if admission.get("ready") is True:
        try:
            exact_ir_closure = build_exact_ir_resource_closure(ir_root, admitted_refs)
        except (OSError, ValueError) as exc:
            exact_ir_closure = _blocked_exact_closure(
                f"exact-ir-preflight-error:{type(exc).__name__}:{exc}"
            )
    else:
        exact_ir_closure = _blocked_exact_closure(
            "upstream-render-binding-admission-not-ready"
        )

    if exact_ir_closure.get("ready") is True:
        bridge = build_sgb_render_binding_bridge(
            admission,
            ir_root,
            runtime_shader_admission=runtime_shader_admission,
        )
    else:
        bridge = _blocked_bridge("exact-ir-closure-not-ready")

    stages = {
        "sgb_runtime": sgb_runtime,
        "placement_join": placement_join,
        "scene_placement": scene_placement,
        "object_render_handoffs": object_handoffs,
        "render_binding_admission": admission,
        "exact_ir_closure": exact_ir_closure,
        "render_binding_bridge": bridge,
    }
    blockers: list[str] = []
    for name, report in stages.items():
        if isinstance(report, Mapping):
            blockers.extend(_stage_blockers(name, report))
        else:
            blockers.append(f"{name}:invalid-report")
    blockers = list(dict.fromkeys(blockers))
    static_resource_ready = not blockers

    status = (
        "static-resource-ready-runtime-draw-blocked"
        if static_resource_ready
        else "static-resource-blocked"
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "static_resource_ready": static_resource_ready,
        "native_scene_runtime_ready": False,
        "blocking_reasons": (
            [RUNTIME_DRAW_BLOCKER]
            if static_resource_ready
            else blockers + [RUNTIME_DRAW_BLOCKER]
        ),
        "stages": stages,
        "summary": {
            "placement_count": scene_placement.get("placement_count"),
            "object_handoff_count": object_handoffs.get("object_count"),
            "admitted_binding_count": admission.get("admitted_binding_count"),
            "admitted_resource_reference_count": len(admitted_refs),
            "exact_ir_closure_ready": exact_ir_closure.get("ready") is True,
            "exact_ir_resolved_resource_count": exact_ir_closure.get(
                "resolved_resource_count"
            ),
            "resolved_instance_count": bridge.get("resolved_instance_count"),
            "runtime_shader_admission_supplied": runtime_shader_admission is not None,
            "runtime_root_consensus_supplied": root_consensus is not None,
        },
        "boundary": {
            "raw_sgb_to_static_render_binding_automated": True,
            "source_backed_scene_contracts_only": True,
            "exact_ir_closure_required_before_legacy_renderer": True,
            "legacy_basename_resolution_is_admission_proof": False,
            "legacy_first_duplicate_is_admission_proof": False,
            "runtime_shader_admission_optional_but_not_draw_proof": True,
            "runtime_proven_draw_required_for_native_scene_bundle": True,
            "static_render_binding_promoted_to_runtime_draw": False,
            "shader_permutation_invented": False,
            "world_transform_invented": False,
            "missing_resource_synthesis": False,
            "provenance_gate_bypass": False,
        },
    }


def build_native_scene_files(
    sgb_path: str | Path,
    ir_root: str | Path,
    output_dir: str | Path,
    *,
    root_consensus_path: str | Path | None = None,
    runtime_shader_admission_path: str | Path | None = None,
) -> dict[str, Any]:
    """Decode raw SGB, run all static scene stages, and persist their contracts."""
    runtime = parse_sgb_runtime(Path(sgb_path).read_bytes(), strict=False)
    root_consensus = _load(root_consensus_path) if root_consensus_path is not None else None
    runtime_shader_admission = (
        _load(runtime_shader_admission_path)
        if runtime_shader_admission_path is not None
        else None
    )
    report = build_native_scene(
        runtime,
        ir_root,
        root_consensus=root_consensus,
        runtime_shader_admission=runtime_shader_admission,
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    filenames = {
        "sgb_runtime": "sgb_runtime.json",
        "placement_join": "sgb_placement_join.json",
        "scene_placement": "sgb_scene_placement.json",
        "object_render_handoffs": "sgb_object_render_handoffs.json",
        "render_binding_admission": "sgb_render_binding_admission.json",
        "exact_ir_closure": "exact_ir_closure.json",
        "render_binding_bridge": "sgb_render_binding_bridge.json",
    }
    artifacts: dict[str, dict[str, Any]] = {}
    for name, filename in filenames.items():
        path = out / filename
        path.write_text(
            json.dumps(report["stages"][name], ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        artifacts[name] = {"path": str(path), "sha256": _sha256(path)}

    persisted = dict(report)
    persisted["artifacts"] = artifacts
    build_path = out / "native_scene_build.json"
    build_path.write_text(
        json.dumps(persisted, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return persisted
