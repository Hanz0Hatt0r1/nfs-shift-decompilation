#!/usr/bin/env python3
"""Convert a Phase 641 renderer handoff into an exact texture-snapshot capture plan.

The plan is deliberately narrow: it consumes only the explicit
``runtime_evidence_required`` frontier emitted by Phase 641 and derives the
D3D9 sampler stages whose already-observed resources are missing snapshot
content.  It never infers a binding, sampler register, resource type, or scene
identity from absence alone.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.Phase641ExternalSamplerCapturePlan/1"
HANDOFF_FORMAT = "SHIFT.RendererNativeSceneHandoff/1"


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object expected: {path}")
    return value


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_capture_plan(handoff: Mapping[str, Any]) -> dict[str, Any]:
    if handoff.get("format") != HANDOFF_FORMAT:
        raise ValueError(f"handoff must be {HANDOFF_FORMAT}")

    blockers: list[str] = []
    boundary = handoff.get("boundary")
    if not isinstance(boundary, Mapping):
        boundary = {}
    completion = handoff.get("existing_capture_completion")
    if not isinstance(completion, Mapping):
        completion = {}

    raw_requirements = completion.get("runtime_evidence_required")
    if raw_requirements is None:
        raw_requirements = []
    if not isinstance(raw_requirements, list):
        blockers.append("phase641-capture-plan:runtime-evidence-required-not-list")
        raw_requirements = []

    declared_required = boundary.get("capture_observation_required") is True
    declared_count = _safe_int(
        boundary.get("capture_observation_requirement_count")
    )
    if declared_required != bool(raw_requirements):
        blockers.append(
            "phase641-capture-plan:capture-observation-required-mismatch"
        )
    if declared_count is not None and declared_count != len(raw_requirements):
        blockers.append(
            "phase641-capture-plan:capture-observation-count-mismatch"
        )

    expected = {
        "sampler2D": ("texture2d", 1),
        "samplerCube": ("cube_texture", 6),
    }
    allowed_reasons = {
        "snapshot-content-not-captured",
        "snapshot-content-incomplete",
    }
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[int, int, str]] = set()

    for index, raw in enumerate(raw_requirements):
        prefix = f"phase641-capture-plan:requirement-{index}"
        if not isinstance(raw, Mapping):
            blockers.append(prefix + ":not-object")
            continue

        binding_index = _safe_int(raw.get("binding_index"))
        register = _safe_int(raw.get("register"))
        requested_stage = _safe_int(raw.get("requested_texture_stage"))
        sampler_type = str(raw.get("sampler_type") or "")
        reason = str(raw.get("reason") or "")
        resource_type = str(raw.get("expected_d3d9_resource_type") or "")
        path_count = _safe_int(raw.get("required_snapshot_path_count"))

        row_blocked = False
        if binding_index is None or binding_index < 0:
            blockers.append(prefix + ":binding-index-invalid")
            row_blocked = True
        if register is None or not 0 <= register <= 15:
            blockers.append(prefix + ":register-invalid")
            row_blocked = True
        if requested_stage is None or not 0 <= requested_stage <= 15:
            blockers.append(prefix + ":requested-stage-invalid")
            row_blocked = True
        if (
            register is not None
            and requested_stage is not None
            and register != requested_stage
        ):
            blockers.append(prefix + ":register-stage-mismatch")
            row_blocked = True
        if sampler_type not in expected:
            blockers.append(prefix + ":sampler-type-invalid")
            row_blocked = True
        else:
            expected_resource_type, expected_path_count = expected[sampler_type]
            if resource_type != expected_resource_type:
                blockers.append(prefix + ":resource-type-mismatch")
                row_blocked = True
            if path_count != expected_path_count:
                blockers.append(prefix + ":snapshot-path-count-mismatch")
                row_blocked = True
        if reason not in allowed_reasons:
            blockers.append(prefix + ":reason-not-actionable")
            row_blocked = True

        if row_blocked:
            continue

        assert binding_index is not None
        assert requested_stage is not None
        key = (binding_index, requested_stage, sampler_type)
        if key in seen:
            blockers.append(prefix + ":duplicate-binding-stage-type")
            continue
        seen.add(key)
        normalized.append({
            "binding_index": binding_index,
            "draw_order": raw.get("draw_order"),
            "sampler": raw.get("sampler"),
            "sampler_type": sampler_type,
            "requested_texture_stage": requested_stage,
            "reason": reason,
            "expected_d3d9_resource_type": resource_type,
            "required_snapshot_path_count": path_count,
            "capture_frames": list(raw.get("capture_frames") or []),
            "capture_draw_indices": list(raw.get("capture_draw_indices") or []),
        })

    normalized.sort(
        key=lambda row: (
            int(row["requested_texture_stage"]),
            int(row["binding_index"]),
            str(row["sampler_type"]),
        )
    )
    stages = sorted({
        int(row["requested_texture_stage"])
        for row in normalized
    })
    blockers = list(dict.fromkeys(blockers))

    ready = bool(normalized) and not blockers
    status = "ready" if ready else "not-needed" if not blockers else "blocked"
    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": ready,
        "blocking_reasons": blockers,
        "requirement_count": len(normalized),
        "texture_stage_list": stages,
        "texture_stages": ",".join(str(stage) for stage in stages),
        "requirements": normalized,
        "source": {
            "handoff_format": handoff.get("format"),
            "handoff_scene_set_ready": handoff.get("scene_set_ready") is True,
            "phase641_capture_observation_required": declared_required,
            "phase641_capture_observation_requirement_count": declared_count,
        },
        "boundary": {
            "phase641_runtime_evidence_required_authoritative": True,
            "sampler_register_inference_allowed": False,
            "resource_type_inference_allowed": False,
            "scene_identity_inference_allowed": False,
            "generic_texture_recapture_requested": False,
            "capture_scope": "exact-requested-texture-stages-only",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff")
    parser.add_argument("--output")
    parser.add_argument(
        "--print-stages",
        action="store_true",
        help="print only the comma-separated exact D3D9 texture stages",
    )
    args = parser.parse_args(argv)

    report = build_capture_plan(_load(args.handoff))
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if args.print_stages:
        if report["ready"]:
            print(report["texture_stages"])
        else:
            print(
                json.dumps({
                    "status": report["status"],
                    "blocking_reasons": report["blocking_reasons"],
                }, ensure_ascii=False),
                file=sys.stderr,
            )
    else:
        print(json.dumps({
            "format": report["format"],
            "status": report["status"],
            "ready": report["ready"],
            "requirement_count": report["requirement_count"],
            "texture_stages": report["texture_stages"],
            "blocking_reasons": report["blocking_reasons"],
        }, ensure_ascii=False, indent=2))

    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
