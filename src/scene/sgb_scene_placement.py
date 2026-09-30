"""Build neutral render-facing placement records from SGB placement joins.

This contract preserves source-backed object identity and spatial query geometry.
It does not synthesize world transforms. FLAT +0x20..+0x34 is accepted as
source-consumed six-float spatial bounds only after the Phase 548 consumer join.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.SGBScenePlacement/1"
JOIN_FORMAT = "SHIFT.SGBPlacementJoin/1"


def _vec3(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    try:
        return [float(v) for v in value]
    except (TypeError, ValueError):
        return None


def _aabb(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    minimum = _vec3(value.get("min_xyz"))
    maximum = _vec3(value.get("max_xyz"))
    if minimum is None or maximum is None:
        return None
    return {
        "min_xyz": minimum,
        "max_xyz": maximum,
        "ordered_axes": all(
            minimum[axis] <= maximum[axis]
            for axis in range(3)
        ),
    }


def _object_summary(value: Any) -> dict[str, Any]:
    row = value if isinstance(value, Mapping) else {}
    return {
        "source_record_index": row.get("index"),
        "source_record_offset": row.get("offset"),
        "name": row.get("name"),
        "resource": row.get("resource"),
        "object_kind": row.get("object_kind"),
        "object_decoded": row.get("object_decoded") is True,
    }


def _flat_summ_placements(
    mode: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    placements: list[dict[str, Any]] = []
    blockers: list[str] = []

    for ordinal, link in enumerate(mode.get("links") or []):
        if not isinstance(link, Mapping):
            blockers.append(
                f"scene-placement:flat-summ:{ordinal}:link-invalid"
            )
            continue
        flat = link.get("flat") or {}
        object_row = _object_summary(link.get("summ"))
        node_aabb = _aabb(flat.get("node_aabbox"))

        masks = flat.get("filter_masks")
        sphere = flat.get("bounding_sphere")
        if not isinstance(masks, Mapping):
            blockers.append(
                f"scene-placement:flat-summ:{ordinal}:filter-masks-missing"
            )
        if not isinstance(sphere, Mapping):
            blockers.append(
                f"scene-placement:flat-summ:{ordinal}:bounding-sphere-missing"
            )
        if node_aabb is None:
            blockers.append(
                f"scene-placement:flat-summ:{ordinal}:node-aabb-missing"
            )

        try:
            runtime_index = int(link.get("runtime_index"))
        except (TypeError, ValueError):
            blockers.append(
                f"scene-placement:flat-summ:{ordinal}:runtime-index-invalid"
            )
            runtime_index = None

        bounds = _aabb(flat.get("spatial_bounds"))
        if bounds is None:
            blockers.append(
                f"scene-placement:flat-summ:{ordinal}:spatial-bounds-missing"
            )

        placements.append({
            "placement_index": ordinal,
            "mode": "flat-summ",
            "identity": {
                "runtime_index": runtime_index,
                "summ_source_order": runtime_index,
                "join": "FLAT leaf +0x3c == SUMM wrapper source order",
            },
            "object": object_row,
            "spatial": {
                "scope": "flat-leaf",
                "node_aabbox": node_aabb,
                "filter_masks": (
                    dict(masks) if isinstance(masks, Mapping) else None
                ),
                "bounding_sphere": (
                    dict(sphere) if isinstance(sphere, Mapping) else None
                ),
                "spatial_bounds": bounds,
                "proven_geometry": [
                    "node_aabbox",
                    "filter_masks",
                    "bounding_sphere",
                    "spatial_bounds",
                ],
            },
            "render_binding_handoff": {
                "resource_ref": object_row.get("resource"),
                "object_kind": object_row.get("object_kind"),
                "world_transform_status": "not-emitted",
                "spatial_culling_ready": (
                    node_aabb is not None
                    and isinstance(masks, Mapping)
                    and isinstance(sphere, Mapping)
                    and bounds is not None
                ),
                "draw_admission": False,
            },
            "ready": (
                runtime_index is not None
                and object_row["object_decoded"]
                and node_aabb is not None
                and isinstance(masks, Mapping)
                and isinstance(sphere, Mapping)
                and bounds is not None
            ),
        })

    return placements, blockers


def _part_node_placements(
    mode: Mapping[str, Any],
    *,
    start_index: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    placements: list[dict[str, Any]] = []
    blockers: list[str] = []

    for local_index, link in enumerate(mode.get("links") or []):
        ordinal = start_index + local_index
        if not isinstance(link, Mapping):
            blockers.append(
                f"scene-placement:part-node:{local_index}:link-invalid"
            )
            continue
        object_row = _object_summary(link.get("node"))
        spatial = link.get("spatial") or {}
        partition_aabb = _aabb(
            spatial.get("partition_aabbox")
            if isinstance(spatial, Mapping) else None
        )
        if partition_aabb is None:
            blockers.append(
                f"scene-placement:part-node:{local_index}:partition-aabb-missing"
            )

        try:
            source_id = int(link.get("source_child_object_id"))
            node_index = int(link.get("node_registry_index"))
        except (TypeError, ValueError):
            source_id = None
            node_index = None
            blockers.append(
                f"scene-placement:part-node:{local_index}:identity-invalid"
            )

        placements.append({
            "placement_index": ordinal,
            "mode": "part-node",
            "identity": {
                "partition_id": link.get("partition_id"),
                "part_record_index": link.get("part_record_index"),
                "child_slot": link.get("child_slot"),
                "source_child_object_id": source_id,
                "node_registry_index": node_index,
                "join": "PART child source_id - 1 == NODE wrapper registry index",
            },
            "object": object_row,
            "spatial": {
                "scope": "partition",
                "partition_aabbox": partition_aabb,
                "filter_masks": None,
                "bounding_sphere": None,
                "bounds_candidate": None,
                "proven_geometry": ["partition_aabbox"],
            },
            "render_binding_handoff": {
                "resource_ref": object_row.get("resource"),
                "object_kind": object_row.get("object_kind"),
                "world_transform_status": "not-emitted",
                "spatial_culling_ready": partition_aabb is not None,
                "draw_admission": False,
            },
            "ready": (
                source_id is not None
                and node_index is not None
                and object_row["object_decoded"]
                and partition_aabb is not None
            ),
        })

    return placements, blockers


def build_sgb_scene_placement(
    placement_join: Mapping[str, Any],
) -> dict[str, Any]:
    if placement_join.get("format") != JOIN_FORMAT:
        raise ValueError("input must be SHIFT.SGBPlacementJoin/1")

    blockers = list(placement_join.get("blocking_reasons") or [])
    if placement_join.get("ready") is not True:
        blockers.append("scene-placement:placement-join-not-ready")

    placements: list[dict[str, Any]] = []

    flat_summ = placement_join.get("flat_summ") or {}
    if isinstance(flat_summ, Mapping) and flat_summ.get("present"):
        rows, reasons = _flat_summ_placements(flat_summ)
        placements.extend(rows)
        blockers.extend(reasons)

    part_node = placement_join.get("part_node") or {}
    if isinstance(part_node, Mapping) and part_node.get("present"):
        rows, reasons = _part_node_placements(
            part_node,
            start_index=len(placements),
        )
        placements.extend(rows)
        blockers.extend(reasons)

    if not placements:
        blockers.append("scene-placement:no-placements")

    blocked_records = [
        row["placement_index"]
        for row in placements
        if not row.get("ready")
    ]
    if blocked_records:
        blockers.append(
            "scene-placement:blocked-records:"
            + ",".join(str(value) for value in blocked_records)
        )

    blockers = list(dict.fromkeys(blockers))
    ready = bool(placements) and not blockers
    mode_counts: dict[str, int] = {}
    for row in placements:
        mode = str(row.get("mode"))
        mode_counts[mode] = mode_counts.get(mode, 0) + 1

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "placement_count": len(placements),
        "mode_counts": mode_counts,
        "placements": placements,
        "render_binding_boundary": {
            "object_identity_ready": ready,
            "spatial_query_geometry_ready": ready,
            "world_transform_emitted": False,
            "draw_admission": False,
            "required_before_draw_admission": [
                "source-backed object/resource-to-render-node mapping",
                "source-backed world transform or explicit identity transform",
            ],
            "leaf_spatial_bounds_source_proven": True,
        },
        "evidence": {
            "identity_join": "SHIFT.SGBPlacementJoin/1",
            "flat_query_geometry": (
                "Phase 546-548 / FUN_006aef20/FUN_006aefe0 + "
                "query vfunc +0x2c"
            ),
            "part_partition_geometry": "FUN_006a4d10/FUN_0068a360",
        },
    }


def validate_file(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("placement join input must be a JSON object")
    return build_sgb_scene_placement(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build neutral render-facing SGB scene placement"
    )
    parser.add_argument("placement_join")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_file(args.placement_join)
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "placement_count": report["placement_count"],
        "mode_counts": report["mode_counts"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
