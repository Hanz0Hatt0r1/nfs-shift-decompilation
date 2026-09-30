"""Join source-backed SGB placement and OBJECT render handoff contracts.

This is the scene-side admission boundary before the generic
SHIFT.RenderBinding/1 resource pipeline.  It never fabricates mesh/material
packets: it joins a proven placement wrapper to every OBJECT render handoff
owned by that wrapper and admits only rows that have spatial culling geometry,
a resource reference and a numeric world matrix.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.SGBRenderBindingAdmission/1"
PLACEMENT_FORMAT = "SHIFT.SGBScenePlacement/1"
HANDOFF_FORMAT = "SHIFT.SGBObjectRenderHandoffSet/1"


def _placement_wrapper_key(
    placement: Mapping[str, Any],
) -> tuple[str, Any] | None:
    mode = placement.get("mode")
    if mode == "flat-summ":
        chunk = "SUMM"
    elif mode == "part-node":
        chunk = "NODE"
    else:
        return None
    object_row = placement.get("object") or {}
    if not isinstance(object_row, Mapping):
        return None
    return chunk, object_row.get("source_record_index")


def _handoff_wrapper_key(
    row: Mapping[str, Any],
) -> tuple[str, Any] | None:
    wrapper = row.get("wrapper") or {}
    if not isinstance(wrapper, Mapping):
        return None
    chunk = wrapper.get("chunk")
    index = wrapper.get("source_record_index")
    if chunk not in {"NODE", "SUMM"}:
        return None
    return str(chunk), index


def _matrix16(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 16:
        return None
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError):
        return None


def build_sgb_render_binding_admission(
    scene_placement: Mapping[str, Any],
    object_handoffs: Mapping[str, Any],
) -> dict[str, Any]:
    if scene_placement.get("format") != PLACEMENT_FORMAT:
        raise ValueError("placement input must be SHIFT.SGBScenePlacement/1")
    if object_handoffs.get("format") != HANDOFF_FORMAT:
        raise ValueError(
            "handoff input must be SHIFT.SGBObjectRenderHandoffSet/1"
        )

    blockers: list[str] = []
    placements = [
        row
        for row in (scene_placement.get("placements") or [])
        if isinstance(row, Mapping)
    ]
    handoff_rows = [
        row
        for row in (object_handoffs.get("objects") or [])
        if isinstance(row, Mapping)
    ]
    if not placements:
        blockers.append("sgb-render-binding:no-placements")
    if not handoff_rows:
        blockers.append("sgb-render-binding:no-object-handoffs")

    handoffs_by_key: dict[tuple[str, Any], list[dict[str, Any]]] = {}
    invalid_handoff_rows: list[int] = []
    for index, row in enumerate(handoff_rows):
        key = _handoff_wrapper_key(row)
        if key is None or key[1] is None:
            invalid_handoff_rows.append(index)
            continue
        handoffs_by_key.setdefault(key, []).append(dict(row))
    if invalid_handoff_rows:
        blockers.append(
            "sgb-render-binding:invalid-handoff-wrapper-rows:"
            + ",".join(str(index) for index in invalid_handoff_rows)
        )

    bindings: list[dict[str, Any]] = []
    matched_handoff_ids: set[int] = set()
    unmatched_placements: list[int] = []

    for placement_ordinal, placement in enumerate(placements):
        placement_index = placement.get(
            "placement_index",
            placement_ordinal,
        )
        key = _placement_wrapper_key(placement)
        matches = handoffs_by_key.get(key, []) if key is not None else []
        if not matches:
            unmatched_placements.append(int(placement_index))
            continue

        for handoff_row in matches:
            matched_handoff_ids.add(id(handoff_row))
            handoff = handoff_row.get("handoff") or {}
            if not isinstance(handoff, Mapping):
                handoff = {}
            transform = handoff.get("transform") or {}
            if not isinstance(transform, Mapping):
                transform = {}
            resource = handoff.get("resource") or {}
            if not isinstance(resource, Mapping):
                resource = {}
            placement_boundary = placement.get(
                "render_binding_handoff"
            ) or {}
            if not isinstance(placement_boundary, Mapping):
                placement_boundary = {}

            row_blockers: list[str] = []
            if placement.get("ready") is not True:
                row_blockers.append("placement-not-ready")
            if handoff.get("ready") is not True:
                row_blockers.append("object-handoff-not-ready")
            resource_ref = resource.get("reference")
            if not resource_ref:
                row_blockers.append("resource-reference-missing")
            world_matrix = _matrix16(transform.get("world_matrix"))
            if (
                transform.get("world_matrix_ready") is not True
                or world_matrix is None
            ):
                row_blockers.append("numeric-world-matrix-not-ready")
            spatial_ready = (
                placement_boundary.get("spatial_culling_ready") is True
            )
            if not spatial_ready:
                row_blockers.append("spatial-culling-not-ready")

            binding_index = len(bindings)
            row_blockers = list(dict.fromkeys(row_blockers))
            admitted = not row_blockers
            bindings.append({
                "binding_index": binding_index,
                "status": "ready" if admitted else "blocked",
                "ready": admitted,
                "blocking_reasons": row_blockers,
                "placement": {
                    "placement_index": placement_index,
                    "mode": placement.get("mode"),
                    "wrapper_chunk": key[0] if key else None,
                    "source_record_index": key[1] if key else None,
                    "identity": placement.get("identity"),
                    "spatial": placement.get("spatial"),
                },
                "object": {
                    "object_path": handoff_row.get("object_path"),
                    "wrapper": handoff_row.get("wrapper"),
                    "resource_reference": resource_ref,
                    "transform_mode": transform.get("mode"),
                    "world_matrix": world_matrix,
                },
                "scene_admission": {
                    "resource_identity_ready": bool(resource_ref),
                    "numeric_world_matrix_ready": world_matrix is not None,
                    "spatial_culling_ready": spatial_ready,
                    "admitted_to_generic_render_binding": admitted,
                    "draw_admission": False,
                },
            })

    if unmatched_placements:
        blockers.append(
            "sgb-render-binding:placements-without-object-handoff:"
            + ",".join(str(value) for value in unmatched_placements)
        )

    # The admission is placement-driven. Handoffs with no spatial placement are
    # reported but do not invalidate otherwise valid placement bindings.
    matched_keys = {
        _placement_wrapper_key(row)
        for row in placements
        if _placement_wrapper_key(row) is not None
    }
    orphan_handoffs: list[dict[str, Any]] = []
    for index, row in enumerate(handoff_rows):
        key = _handoff_wrapper_key(row)
        if key is not None and key not in matched_keys:
            orphan_handoffs.append({
                "handoff_index": index,
                "wrapper_chunk": key[0],
                "source_record_index": key[1],
                "object_path": row.get("object_path"),
            })

    for binding in bindings:
        if not binding["ready"]:
            blockers.extend(
                f"binding-{binding['binding_index']}:{reason}"
                for reason in binding["blocking_reasons"]
            )

    blockers = list(dict.fromkeys(blockers))
    admitted_count = sum(row["ready"] for row in bindings)
    ready = bool(bindings) and admitted_count == len(bindings) and not blockers
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "placement_count": len(placements),
        "object_handoff_count": len(handoff_rows),
        "binding_count": len(bindings),
        "admitted_binding_count": admitted_count,
        "blocked_binding_count": len(bindings) - admitted_count,
        "unmatched_placement_indices": unmatched_placements,
        "orphan_object_handoffs": orphan_handoffs,
        "bindings": bindings,
        "boundary": {
            "identity_join": (
                "flat-summ -> SUMM wrapper source_record_index; "
                "part-node -> NODE wrapper source_record_index"
            ),
            "one_wrapper_to_many_objects": True,
            "generic_render_binding_format": "SHIFT.RenderBinding/1",
            "generic_render_binding_packets_emitted": False,
            "draw_admission": False,
            "remaining_after_scene_admission": (
                "resolve admitted resource references through the existing "
                "MEB/BMT/FXO RenderBinding pipeline"
            ),
        },
    }


def validate_files(
    placement_path: str | Path,
    handoff_path: str | Path,
) -> dict[str, Any]:
    placement = json.loads(
        Path(placement_path).read_text(encoding="utf-8")
    )
    handoffs = json.loads(
        Path(handoff_path).read_text(encoding="utf-8")
    )
    if not isinstance(placement, Mapping):
        raise ValueError("placement JSON must be an object")
    if not isinstance(handoffs, Mapping):
        raise ValueError("handoff JSON must be an object")
    return build_sgb_render_binding_admission(placement, handoffs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Join SGB placement and OBJECT render handoff admission"
    )
    parser.add_argument("scene_placement")
    parser.add_argument("object_handoffs")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_files(
        args.scene_placement,
        args.object_handoffs,
    )
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "binding_count": report["binding_count"],
        "admitted_binding_count": report["admitted_binding_count"],
        "blocked_binding_count": report["blocked_binding_count"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
