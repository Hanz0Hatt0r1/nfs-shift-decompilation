"""Neutral scene-placement contract for source-backed SGB spatial joins."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

FORMAT = "SHIFT.ScenePlacement/1"
PLACEMENT_JOIN_FORMAT = "SHIFT.SGBPlacementJoin/1"
RENDER_BINDING_FORMAT = "SHIFT.RenderBinding/1"


def _valid_aabb(value: Mapping[str, Any] | None) -> bool:
    if not isinstance(value, Mapping):
        return False
    lo = value.get("min_xyz")
    hi = value.get("max_xyz")
    if not isinstance(lo, list) or not isinstance(hi, list):
        return False
    if len(lo) != 3 or len(hi) != 3:
        return False
    try:
        return all(float(lo[i]) <= float(hi[i]) for i in range(3))
    except (TypeError, ValueError):
        return False


def build_scene_placement(join: Mapping[str, Any]) -> dict[str, Any]:
    if join.get("format") != PLACEMENT_JOIN_FORMAT:
        raise ValueError("input must be SHIFT.SGBPlacementJoin/1")

    blockers = list(join.get("blocking_reasons") or [])
    placements: list[dict[str, Any]] = []

    flat_summ = join.get("flat_summ") or {}
    if flat_summ.get("present"):
        if flat_summ.get("ready") is not True:
            blockers.append("scene-placement:flat-summ-not-ready")
        for link in flat_summ.get("links") or []:
            if not isinstance(link, Mapping):
                continue
            flat = link.get("flat") or {}
            summ = link.get("summ") or {}
            node_aabb = flat.get("node_aabbox")
            sphere = flat.get("bounding_sphere")
            bounds = flat.get("spatial_bounds")
            masks = flat.get("filter_masks")
            idx = link.get("runtime_index")

            if not _valid_aabb(node_aabb):
                blockers.append(
                    f"scene-placement:flat-summ-{idx}:node-aabb-invalid"
                )
            if not _valid_aabb(bounds):
                blockers.append(
                    f"scene-placement:flat-summ-{idx}:leaf-bounds-invalid"
                )
            if not isinstance(sphere, Mapping):
                blockers.append(
                    f"scene-placement:flat-summ-{idx}:sphere-missing"
                )
            if not isinstance(masks, Mapping):
                blockers.append(
                    f"scene-placement:flat-summ-{idx}:filter-masks-missing"
                )

            placements.append({
                "placement_id": f"flat-summ:{idx}",
                "mode": "flat-summ",
                "identity": {
                    "runtime_index": idx,
                    "tree_path": flat.get("tree_path"),
                    "leaf_offset": flat.get("leaf_offset"),
                },
                "object": deepcopy(dict(summ)),
                "resource": summ.get("resource"),
                "object_kind": summ.get("object_kind"),
                "spatial": {
                    "partition_aabbox": deepcopy(node_aabb),
                    "bounding_sphere": deepcopy(sphere),
                    "bounds": deepcopy(bounds),
                    "filter_masks": deepcopy(masks),
                },
                "precision": "leaf",
                "source": {
                    "placement_join": "FLAT +0x3c -> SUMM wrapper order",
                    "bounds_query": (
                        "FUN_006afb20 -> FUN_006aef20 -> "
                        "query vfunc +0x2c"
                    ),
                },
            })

    part_node = join.get("part_node") or {}
    if part_node.get("present"):
        if part_node.get("ready") is not True:
            blockers.append("scene-placement:part-node-not-ready")
        for link in part_node.get("links") or []:
            if not isinstance(link, Mapping):
                continue
            aabb = link.get("partition_aabbox")
            part_index = link.get("part_record_index")
            child_slot = link.get("child_slot")
            if not _valid_aabb(aabb):
                blockers.append(
                    "scene-placement:part-node-"
                    f"{part_index}-{child_slot}:partition-aabb-invalid"
                )
            node = link.get("node") or {}
            placements.append({
                "placement_id": f"part-node:{part_index}:{child_slot}",
                "mode": "part-node",
                "identity": {
                    "part_record_index": part_index,
                    "partition_id": link.get("partition_id"),
                    "child_slot": child_slot,
                    "source_child_object_id": link.get(
                        "source_child_object_id"
                    ),
                    "node_registry_index": link.get("node_registry_index"),
                },
                "object": deepcopy(dict(node)),
                "resource": node.get("resource"),
                "object_kind": node.get("object_kind"),
                "spatial": {
                    "partition_aabbox": deepcopy(aabb),
                    "bounding_sphere": None,
                    "bounds": None,
                    "filter_masks": None,
                },
                "precision": "partition",
                "source": {
                    "placement_join": (
                        "PART one-based child ID -> NODE wrapper registry"
                    ),
                },
            })

    blockers = list(dict.fromkeys(str(value) for value in blockers))
    ready = bool(placements) and not blockers
    modes = sorted({row["mode"] for row in placements})
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "modes": modes,
        "placement_count": len(placements),
        "placements": placements,
        "stats": {
            "flat_summ": sum(row["mode"] == "flat-summ" for row in placements),
            "part_node": sum(row["mode"] == "part-node" for row in placements),
            "leaf_precision": sum(row["precision"] == "leaf" for row in placements),
            "partition_precision": sum(
                row["precision"] == "partition" for row in placements
            ),
        },
        "boundary": {
            "world_matrix_synthesized": False,
            "render_command_modified": False,
            "filter_mask_bit_meanings_claimed": False,
            "runtime_class_identity_required": False,
        },
    }


def attach_scene_placement(
    render_binding: Mapping[str, Any],
    placement: Mapping[str, Any],
) -> dict[str, Any]:
    if render_binding.get("format") != RENDER_BINDING_FORMAT:
        raise ValueError("render input must be SHIFT.RenderBinding/1")
    if placement.get("format") != FORMAT:
        raise ValueError("placement input must be SHIFT.ScenePlacement/1")
    if placement.get("ready") is not True:
        raise ValueError("scene placement is not ready")

    out = deepcopy(dict(render_binding))
    out["scene_placement"] = deepcopy(dict(placement))
    stats = deepcopy(dict(out.get("stats") or {}))
    stats["scene_placements"] = int(placement.get("placement_count") or 0)
    stats["scene_placement_modes"] = list(placement.get("modes") or [])
    out["stats"] = stats
    return out


__all__ = [
    "FORMAT",
    "build_scene_placement",
    "attach_scene_placement",
]
