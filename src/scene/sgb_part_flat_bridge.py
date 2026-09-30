"""Source-backed bridge from SGB PART spatial trees to FLAT runtime layout.

Recovered from FUN_006a4d10/FUN_0068a360 and the finalize path
FUN_0068ab70 -> FUN_0068a810 -> FUN_00689cb0/FUN_006afd50/FUN_00689db0.

The bridge is deterministic over already-decoded SHIFT.SGBRuntime/1 input.  It
does not invent values for runtime pointers; pointer-bearing fields are exposed
as source/offset contracts.
"""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.SGBPartFlatBridge/1"
SGB_FORMAT = "SHIFT.SGBRuntime/1"

FLAT_NODE_BYTES = 0x20
FLAT_DIRECT_RECORD_BYTES = 0x40
PRIMARY_ENTRY_BYTES = 0x28
SECONDARY_ENTRY_BYTES = 0x40


class SGBPartFlatBridgeError(ValueError):
    pass


def _payload_kind(row: Mapping[str, Any]) -> str | None:
    payload = row.get("object_payload") or {}
    report = payload.get("report") if isinstance(payload, Mapping) else {}
    kind = report.get("kind") if isinstance(report, Mapping) else {}
    value = kind.get("text") if isinstance(kind, Mapping) else None
    return str(value) if value else None


def build_scene_wrapper_catalog(
    sgb_report: Mapping[str, Any],
    *,
    before_chunk_index: int | None = None,
) -> list[dict[str, Any]]:
    """Reconstruct the loader +0x54 wrapper-list order used by PART ids.

    FUN_006a4f10 appends OCCL wrappers only in per-record mode.
    FUN_006a4b40 appends every NODE wrapper.
    FUN_006a4900/SUMM bypasses this list and is therefore excluded.
    """
    if sgb_report.get("format") != SGB_FORMAT:
        raise SGBPartFlatBridgeError(
            "input must be SHIFT.SGBRuntime/1"
        )

    catalog: list[dict[str, Any]] = []
    for chunk_index, chunk in enumerate(sgb_report.get("chunks") or []):
        if before_chunk_index is not None and chunk_index >= before_chunk_index:
            break
        if not isinstance(chunk, Mapping):
            continue
        tag = chunk.get("tag")
        records = chunk.get("records") or []

        if tag == "OCCL":
            for row in records:
                if not isinstance(row, Mapping):
                    continue
                admission = row.get("runtime_admission") or {}
                if (
                    not isinstance(admission, Mapping)
                    or admission.get("mode") != "per-record-wrapper"
                ):
                    continue
                wrapper = admission.get("wrapper") or {}
                zero_index = len(catalog)
                catalog.append({
                    "zero_based_index": zero_index,
                    "source_id_one_based": zero_index + 1,
                    "chunk_index": chunk_index,
                    "chunk_tag": "OCCL",
                    "record_index": row.get("index"),
                    "record_offset": row.get("offset"),
                    "payload_kind": "OCCL",
                    "wrapper_vtable": (
                        wrapper.get("vtable")
                        if isinstance(wrapper, Mapping) else None
                    ),
                    "wrapper_source": "FUN_006a4f10 -> loader +0x54",
                })

        elif tag == "NODE":
            for row in records:
                if not isinstance(row, Mapping):
                    continue
                wrapper = row.get("runtime_wrapper") or {}
                zero_index = len(catalog)
                catalog.append({
                    "zero_based_index": zero_index,
                    "source_id_one_based": zero_index + 1,
                    "chunk_index": chunk_index,
                    "chunk_tag": "NODE",
                    "record_index": row.get("index"),
                    "record_offset": row.get("offset"),
                    "payload_kind": _payload_kind(row),
                    "wrapper_vtable": (
                        wrapper.get("vtable")
                        if isinstance(wrapper, Mapping) else None
                    ),
                    "wrapper_source": "FUN_006a4b40 -> loader +0x54",
                })

    return catalog


def _part_records(
    chunks: list[Any],
) -> tuple[list[dict[str, Any]], int | None]:
    rows: list[dict[str, Any]] = []
    first_chunk_index: int | None = None
    for chunk_index, chunk in enumerate(chunks):
        if not isinstance(chunk, Mapping) or chunk.get("tag") != "PART":
            continue
        if first_chunk_index is None:
            first_chunk_index = chunk_index
        for row in chunk.get("records") or []:
            if not isinstance(row, Mapping):
                continue
            copy = dict(row)
            copy["_bridge_chunk_index"] = chunk_index
            rows.append(copy)
    return rows, first_chunk_index


def _prebuilt_flat_summary(chunks: list[Any]) -> dict[str, Any] | None:
    for chunk_index, chunk in enumerate(chunks):
        if not isinstance(chunk, Mapping) or chunk.get("tag") != "FLAT":
            continue
        flat = chunk.get("flat_runtime") or {}
        stats = flat.get("stats") if isinstance(flat, Mapping) else {}
        return {
            "chunk_index": chunk_index,
            "chunk_offset": chunk.get("offset"),
            "chunk_size": chunk.get("size"),
            "ready": flat.get("ready") if isinstance(flat, Mapping) else None,
            "tree_nodes": (
                stats.get("tree_nodes")
                if isinstance(stats, Mapping) else None
            ),
            "direct_records": (
                stats.get("leaf_records")
                if isinstance(stats, Mapping) else None
            ),
            "max_depth": (
                stats.get("max_depth")
                if isinstance(stats, Mapping) else None
            ),
        }
    return None


def _resolve_catalog_entry(
    source_id: Any,
    catalog: list[dict[str, Any]],
    *,
    partition_id: Any,
    blockers: list[str],
) -> dict[str, Any] | None:
    try:
        value = int(source_id)
    except (TypeError, ValueError):
        blockers.append(
            f"part-flat:partition-{partition_id}:wrapper-id-invalid:{source_id}"
        )
        return None
    if value <= 0 or value > len(catalog):
        blockers.append(
            f"part-flat:partition-{partition_id}:wrapper-id-out-of-range:{value}"
        )
        return None
    return catalog[value - 1]


def _build_generated_flat(
    part_rows: list[dict[str, Any]],
    catalog: list[dict[str, Any]],
) -> dict[str, Any]:
    blockers: list[str] = []
    if not part_rows:
        return {
            "ready": False,
            "blocking_reasons": ["part-flat:part-records-missing"],
        }

    by_partition: dict[int, dict[str, Any]] = {}
    for row in part_rows:
        try:
            partition_id = int(row.get("partition_id"))
        except (TypeError, ValueError):
            blockers.append("part-flat:partition-id-invalid")
            continue
        if partition_id in by_partition:
            blockers.append(
                f"part-flat:partition-id-duplicate:{partition_id}"
            )
            continue
        by_partition[partition_id] = row

    root = part_rows[0]
    runtime_index = 0
    flat_cursor = 0
    visited: set[int] = set()
    active: set[int] = set()
    all_direct_records: list[dict[str, Any]] = []

    def walk(row: dict[str, Any]) -> dict[str, Any]:
        nonlocal runtime_index, flat_cursor
        partition_id = int(row.get("partition_id"))
        if partition_id in active:
            blockers.append(
                f"part-flat:partition-cycle:{partition_id}"
            )
            return {
                "partition_id": partition_id,
                "blocked": True,
                "children": [],
                "direct_records": [],
            }
        if partition_id in visited:
            blockers.append(
                f"part-flat:partition-reused:{partition_id}"
            )
            return {
                "partition_id": partition_id,
                "blocked": True,
                "children": [],
                "direct_records": [],
            }

        active.add(partition_id)
        visited.add(partition_id)

        node_offset = flat_cursor
        flat_cursor += FLAT_NODE_BYTES
        direct_records: list[dict[str, Any]] = []

        child_object_ids = list(row.get("child_object_indices") or [])
        for local_index, source_id in enumerate(child_object_ids):
            catalog_row = _resolve_catalog_entry(
                source_id,
                catalog,
                partition_id=partition_id,
                blockers=blockers,
            )
            record_offset = flat_cursor
            flat_cursor += FLAT_DIRECT_RECORD_BYTES
            index = runtime_index
            runtime_index += 1
            direct = {
                "local_index": local_index,
                "flat_runtime_index": index,
                "flat_record_offset": record_offset,
                "source_wrapper_id_one_based": source_id,
                "wrapper_catalog": catalog_row,
                "partition_id": partition_id,
                "partition_record_index": row.get("index"),
                "wrapper_partition_bounds_write": {
                    "wrapper_field_offset": 0x30,
                    "value_source": "PART runtime node +0x04 AABB",
                    "producer": "FUN_0068a360",
                },
                "serialized_words_0_3_source": {
                    "pointer_source": "scene wrapper +0x0c",
                    "pointee_offsets": [0x10, 0x14, 0x18, 0x1C],
                    "destination_offsets": [0x00, 0x04, 0x08, 0x0C],
                    "producer": "FUN_00689db0",
                },
                "direct_object_pointer": {
                    "destination_offset": 0x38,
                    "value_source": "scene wrapper +0x0c pointee",
                    "producer": "FUN_00689db0",
                },
                "runtime_index_field": {
                    "destination_offset": 0x3C,
                    "value": index,
                    "producer": "FUN_00689db0",
                },
                "primary_table": {
                    "entry_stride": PRIMARY_ENTRY_BYTES,
                    "entry_offset": index * PRIMARY_ENTRY_BYTES,
                    "record_pointer_field_offset": 0x20,
                    "record_pointer_target_offset": record_offset,
                },
                "secondary_table": {
                    "entry_stride": SECONDARY_ENTRY_BYTES,
                    "entry_offset": index * SECONDARY_ENTRY_BYTES,
                    "initializer": "FUN_00687b00(secondary, scene_wrapper)",
                    "node_pointer_field_offset": 0x30,
                    "node_pointer_target_offset": node_offset,
                    "record_pointer_field_offset": 0x34,
                    "record_pointer_target_offset": record_offset,
                    "primary_pointer_field_offset": 0x38,
                    "primary_pointer_target_offset": (
                        index * PRIMARY_ENTRY_BYTES
                    ),
                },
            }
            direct_records.append(direct)
            all_direct_records.append(direct)

        child_nodes: list[dict[str, Any]] = []
        child_ids = list(row.get("child_partition_ids") or [])
        table_present = bool(row.get("child_partition_table_present"))
        if table_present:
            for slot, raw_child in enumerate(child_ids[:4]):
                try:
                    child_id = int(raw_child)
                except (TypeError, ValueError):
                    blockers.append(
                        f"part-flat:partition-{partition_id}:"
                        f"child-id-invalid:slot-{slot}"
                    )
                    continue
                if child_id == 0:
                    continue
                child = by_partition.get(child_id)
                if child is None:
                    blockers.append(
                        f"part-flat:partition-{partition_id}:"
                        f"child-partition-unresolved:{child_id}"
                    )
                    child_nodes.append({
                        "slot": slot,
                        "source_partition_id": child_id,
                        "resolved": False,
                    })
                    continue
                built = walk(child)
                child_nodes.append({
                    "slot": slot,
                    "source_partition_id": child_id,
                    "resolved": True,
                    "node": built,
                })

        active.remove(partition_id)
        subtree_end = flat_cursor
        return {
            "partition_id": partition_id,
            "partition_record_index": row.get("index"),
            "partition_chunk_index": row.get("_bridge_chunk_index"),
            "flat_node_offset": node_offset,
            "aabbox_min": list(row.get("aabbox_min") or []),
            "aabbox_max": list(row.get("aabbox_max") or []),
            "aabb_copy": {
                "source": "PART runtime node +0x04..+0x18",
                "destination": "FLAT node +0x00..+0x14",
                "producer": "FUN_00689db0",
            },
            "direct_record_count": len(direct_records),
            "direct_records": direct_records,
            "children": child_nodes,
            "subtree_bytes": subtree_end - node_offset,
            "span_builder": {
                "source": "FUN_00689db0",
                "final_child_or_leaf_marker": "subtree_bytes | 0x01000000",
                "runtime_normalizer": "FUN_006afd30 -> FUN_006af6c0",
            },
        }

    root_node = walk(root)

    unreachable: list[int] = []
    for row in part_rows:
        try:
            partition_id = int(row.get("partition_id"))
        except (TypeError, ValueError):
            continue
        if partition_id not in visited:
            unreachable.append(partition_id)
    for partition_id in unreachable:
        blockers.append(
            f"part-flat:partition-unreachable:{partition_id}"
        )

    generated_bytes = flat_cursor
    expected_bytes = (
        len(visited) * FLAT_NODE_BYTES
        + len(all_direct_records) * FLAT_DIRECT_RECORD_BYTES
    )
    if generated_bytes != expected_bytes:
        blockers.append(
            f"part-flat:byte-accounting-mismatch:"
            f"{generated_bytes}:{expected_bytes}"
        )

    return {
        "ready": not blockers,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "root": root_node,
        "summary": {
            "part_record_count": len(part_rows),
            "reachable_partition_count": len(visited),
            "direct_record_count": len(all_direct_records),
            "generated_flat_bytes": generated_bytes,
            "counting_rule": (
                "0x20 per PART node + 0x40 per direct scene wrapper"
            ),
            "primary_table_bytes": (
                len(all_direct_records) * PRIMARY_ENTRY_BYTES
            ),
            "secondary_table_bytes": (
                len(all_direct_records) * SECONDARY_ENTRY_BYTES
            ),
            "runtime_index_min": (
                0 if all_direct_records else None
            ),
            "runtime_index_max": (
                len(all_direct_records) - 1
                if all_direct_records else None
            ),
        },
        "direct_records": all_direct_records,
        "teardown": {
            "part_tree_destroy": "FUN_00689d40 -> FUN_00687de0",
            "wrapper_payload_pointer_clear_offset": 0x08,
            "scenegraph_part_root_cleared": True,
        },
    }


def build_sgb_part_flat_bridge(
    sgb_report: Mapping[str, Any],
) -> dict[str, Any]:
    if sgb_report.get("format") != SGB_FORMAT:
        raise SGBPartFlatBridgeError(
            "input must be SHIFT.SGBRuntime/1"
        )

    chunks = list(sgb_report.get("chunks") or [])
    prebuilt = _prebuilt_flat_summary(chunks)
    part_rows, first_part_chunk_index = _part_records(chunks)

    catalog_limit = (
        first_part_chunk_index
        if first_part_chunk_index is not None
        else None
    )
    catalog = build_scene_wrapper_catalog(
        sgb_report,
        before_chunk_index=catalog_limit,
    )

    if prebuilt is not None:
        return {
            "format": FORMAT,
            "version": 1,
            "ready": True,
            "status": "prebuilt-flat",
            "mode": "prebuilt-flat",
            "conversion_required": False,
            "blocking_reasons": [],
            "wrapper_catalog": catalog,
            "wrapper_catalog_count": len(catalog),
            "part_record_count": len(part_rows),
            "prebuilt_flat": prebuilt,
            "generated_flat": None,
            "source_runtime_rule": {
                "finalizer": "FUN_0068ab70",
                "condition": (
                    "PART -> FLAT conversion only when scenegraph +0x30 "
                    "FLAT manager is null"
                ),
                "conversion": (
                    "FUN_0068a810 -> FUN_00689cb0/FUN_006afd50/"
                    "FUN_00689db0 -> FUN_006afd30"
                ),
            },
        }

    if not part_rows:
        return {
            "format": FORMAT,
            "version": 1,
            "ready": False,
            "status": "no-spatial-representation",
            "mode": "none",
            "conversion_required": False,
            "blocking_reasons": [
                "part-flat:neither-prebuilt-flat-nor-part"
            ],
            "wrapper_catalog": catalog,
            "wrapper_catalog_count": len(catalog),
            "part_record_count": 0,
            "prebuilt_flat": None,
            "generated_flat": None,
        }

    generated = _build_generated_flat(part_rows, catalog)
    return {
        "format": FORMAT,
        "version": 1,
        "ready": bool(generated.get("ready")),
        "status": (
            "generated-flat-ready"
            if generated.get("ready")
            else "generated-flat-blocked"
        ),
        "mode": "part-to-flat",
        "conversion_required": True,
        "blocking_reasons": list(
            generated.get("blocking_reasons") or []
        ),
        "wrapper_catalog": catalog,
        "wrapper_catalog_count": len(catalog),
        "part_record_count": len(part_rows),
        "prebuilt_flat": None,
        "generated_flat": generated,
        "source_runtime_rule": {
            "part_loader": "FUN_006a4d10 -> FUN_0068a360",
            "wrapper_lookup": (
                "FUN_006885b0(wrapper_list, source_id - 1)"
            ),
            "finalizer": "FUN_0068ab70",
            "count": "FUN_00689cb0",
            "allocate": "FUN_006afd50",
            "build": "FUN_00689db0",
            "normalize": "FUN_006afd30 -> FUN_006af6c0",
        },
    }


__all__ = [
    "FORMAT",
    "SGBPartFlatBridgeError",
    "build_scene_wrapper_catalog",
    "build_sgb_part_flat_bridge",
]
