"""Join source-backed SGB wrapper registries to spatial placement records.

Two retail paths are kept distinct:

* FLAT/SUMM: SUMM wrappers are copied into sequential secondary slots and
  FLAT leaf +0x3c indexes those slots.
* PART/NODE: PART child object IDs are one-based indices into the NODE wrapper
  registry.

The PART runtime can later be materialized into FLAT-like 0x40-byte records by
FUN_00689db0; that runtime conversion is described as evidence but is not
invented as serialized data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.SGBPlacementJoin/1"
SGB_FORMAT = "SHIFT.SGBRuntime/1"


def _chunk(report: Mapping[str, Any], tag: str) -> Mapping[str, Any] | None:
    hits = [
        row
        for row in (report.get("chunks") or [])
        if isinstance(row, Mapping) and row.get("tag") == tag
    ]
    if len(hits) > 1:
        raise ValueError(f"placement-join: multiple {tag} chunks are unsupported")
    return hits[0] if hits else None


def _flatten_flat_records(
    node: Mapping[str, Any] | None,
    *,
    path: tuple[int, ...] = (),
) -> list[dict[str, Any]]:
    if not isinstance(node, Mapping):
        return []
    rows: list[dict[str, Any]] = []
    for local_index, record in enumerate(node.get("records") or []):
        if not isinstance(record, Mapping):
            continue
        rows.append({
            "tree_path": list(path),
            "node_offset": node.get("offset"),
            "node_depth": node.get("depth"),
            "node_aabbox": node.get("aabbox"),
            "leaf_local_index": local_index,
            "leaf": record,
        })
    for child_index, child in enumerate(node.get("children") or []):
        rows.extend(
            _flatten_flat_records(
                child,
                path=(*path, child_index),
            )
        )
    return rows


def _record_summary(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = row.get("object_payload") or {}
    object_report = (
        payload.get("report")
        if isinstance(payload, Mapping)
        else {}
    ) or {}
    kind = (
        (object_report.get("kind") or {}).get("text")
        if isinstance(object_report, Mapping)
        else None
    )
    return {
        "index": row.get("index"),
        "offset": row.get("offset"),
        "name": (row.get("name") or {}).get("text"),
        "resource": (row.get("resource") or {}).get("text"),
        "object_kind": kind,
        "object_decoded": bool(
            isinstance(object_report, Mapping)
            and object_report.get("decoded")
        ),
    }


def _join_flat_summ(
    flat_chunk: Mapping[str, Any] | None,
    summ_chunk: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if flat_chunk is None and summ_chunk is None:
        return {
            "present": False,
            "ready": False,
            "status": "not-present",
            "blocking_reasons": [],
            "links": [],
        }

    blockers: list[str] = []
    if flat_chunk is None:
        blockers.append("flat-summ:flat-chunk-missing")
    if summ_chunk is None:
        blockers.append("flat-summ:summ-chunk-missing")
    if blockers:
        return {
            "present": True,
            "ready": False,
            "status": "blocked",
            "blocking_reasons": blockers,
            "links": [],
        }

    flat_runtime = flat_chunk.get("flat_runtime") or {}
    summ_records = [
        row
        for row in (summ_chunk.get("records") or [])
        if isinstance(row, Mapping)
    ]
    if flat_runtime.get("ready") is not True:
        blockers.append("flat-summ:flat-runtime-not-ready")

    flat_rows = _flatten_flat_records(flat_runtime.get("root"))
    by_index: dict[int, dict[str, Any]] = {}
    duplicate_indices: list[int] = []
    out_of_range: list[int] = []
    links: list[dict[str, Any]] = []

    for ordinal, row in enumerate(flat_rows):
        leaf = row["leaf"]
        try:
            runtime_index = int(leaf.get("runtime_index"))
        except (TypeError, ValueError):
            blockers.append(
                f"flat-summ:leaf-{ordinal}:runtime-index-invalid"
            )
            continue
        if runtime_index in by_index:
            duplicate_indices.append(runtime_index)
        else:
            by_index[runtime_index] = row
        if runtime_index < 0 or runtime_index >= len(summ_records):
            out_of_range.append(runtime_index)
            continue

        summ = summ_records[runtime_index]
        links.append({
            "runtime_index": runtime_index,
            "flat": {
                "leaf_ordinal": ordinal,
                "tree_path": row["tree_path"],
                "node_offset": row["node_offset"],
                "node_depth": row["node_depth"],
                "node_aabbox": row.get("node_aabbox"),
                "leaf_offset": leaf.get("offset"),
                "filter_masks": leaf.get("filter_masks"),
                "bounding_sphere": leaf.get("bounding_sphere"),
                "spatial_bounds": leaf.get("spatial_bounds"),
                "direct_object_pointer_word": (
                    leaf.get("direct_object_pointer_word")
                ),
            },
            "summ": _record_summary(summ),
            "runtime_join": {
                "secondary_stride": 0x40,
                "primary_stride": 0x28,
                "secondary_node_pointer_offset": 0x30,
                "secondary_record_pointer_offset": 0x34,
                "secondary_primary_slot_pointer_offset": 0x38,
                "primary_record_pointer_offset": 0x20,
            },
        })

    if len(flat_rows) != len(summ_records):
        blockers.append(
            "flat-summ:count-mismatch:"
            f"flat={len(flat_rows)}:summ={len(summ_records)}"
        )
    if duplicate_indices:
        blockers.append(
            "flat-summ:duplicate-runtime-indices:"
            + ",".join(str(v) for v in sorted(set(duplicate_indices)))
        )
    if out_of_range:
        blockers.append(
            "flat-summ:runtime-index-out-of-range:"
            + ",".join(str(v) for v in sorted(set(out_of_range)))
        )

    expected = set(range(len(summ_records)))
    actual = set(by_index)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing:
        blockers.append(
            "flat-summ:missing-runtime-indices:"
            + ",".join(str(v) for v in missing)
        )
    if unexpected:
        blockers.append(
            "flat-summ:unexpected-runtime-indices:"
            + ",".join(str(v) for v in unexpected)
        )

    links.sort(key=lambda row: row["runtime_index"])
    ready = not blockers
    return {
        "present": True,
        "ready": ready,
        "status": "ready" if ready else "blocked",
        "blocking_reasons": blockers,
        "flat_leaf_count": len(flat_rows),
        "summ_wrapper_count": len(summ_records),
        "runtime_index_min": min(actual) if actual else None,
        "runtime_index_max": max(actual) if actual else None,
        "runtime_index_unique_count": len(actual),
        "runtime_index_contiguous": actual == expected,
        "serialized_nonzero_direct_object_pointer_count": sum(
            bool(row["leaf"].get("direct_object_pointer_word"))
            for row in flat_rows
        ),
        "links": links,
        "source_evidence": {
            "summ_slot_allocation": (
                "FUN_006a4900 -> FUN_0068a920 -> FUN_006af330"
            ),
            "summ_slot_append": (
                "FUN_006a4900 -> FUN_00688510 -> FUN_006af4b0"
            ),
            "flat_index_link": (
                "FUN_006a4900 -> FUN_00688520 -> "
                "FUN_006af820 -> FUN_006af780"
            ),
            "rule": (
                "SUMM record order selects secondary slot i; "
                "FLAT leaf +0x3c selects the same slot i"
            ),
        },
    }


def _join_part_node(
    part_chunk: Mapping[str, Any] | None,
    node_chunk: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if part_chunk is None and node_chunk is None:
        return {
            "present": False,
            "ready": False,
            "status": "not-present",
            "blocking_reasons": [],
            "links": [],
        }

    if part_chunk is None:
        return {
            "present": False,
            "ready": False,
            "status": "not-present",
            "blocking_reasons": [],
            "links": [],
        }

    blockers: list[str] = []
    if node_chunk is None:
        blockers.append("part-node:node-chunk-missing")
        node_records: list[Mapping[str, Any]] = []
    else:
        node_records = [
            row
            for row in (node_chunk.get("records") or [])
            if isinstance(row, Mapping)
        ]

    links: list[dict[str, Any]] = []
    for part in part_chunk.get("records") or []:
        if not isinstance(part, Mapping):
            continue
        part_index = part.get("index")
        partition_id = part.get("partition_id")
        source_ids = list(part.get("child_object_indices") or [])
        for slot, source_id in enumerate(source_ids):
            try:
                source_id = int(source_id)
            except (TypeError, ValueError):
                blockers.append(
                    f"part-node:part-{part_index}:child-{slot}:id-invalid"
                )
                continue
            if source_id <= 0:
                blockers.append(
                    f"part-node:part-{part_index}:child-{slot}:id-not-one-based"
                )
                continue
            node_index = source_id - 1
            if node_index >= len(node_records):
                blockers.append(
                    f"part-node:part-{part_index}:child-{slot}:"
                    f"node-index-out-of-range:{node_index}"
                )
                continue
            node = node_records[node_index]
            links.append({
                "part_record_index": part_index,
                "partition_id": partition_id,
                "child_slot": slot,
                "source_child_object_id": source_id,
                "node_registry_index": node_index,
                "node": _record_summary(node),
                "partition_aabbox": {
                    "min_xyz": part.get("aabbox_min"),
                    "max_xyz": part.get("aabbox_max"),
                    "source": "PART record +0x04..+0x18",
                },
                "runtime_join": {
                    "lookup": "FUN_006885b0(scene_wrapper_list, source_id - 1)",
                    "node_registry_owner_offset": 0x54,
                    "node_registry_append": (
                        "FUN_006a4b40 -> FUN_004cb900(this+0x54, wrapper)"
                    ),
                },
            })

    ready = not blockers
    return {
        "present": True,
        "ready": ready,
        "status": "ready" if ready else "blocked",
        "blocking_reasons": blockers,
        "node_registry_count": len(node_records),
        "linked_child_object_count": len(links),
        "links": links,
        "source_evidence": {
            "node_registry": (
                "FUN_006a4b40 appends each binary NODE wrapper to manager +0x54"
            ),
            "part_lookup": (
                "FUN_0068a360/FUN_00689a30 resolve each PART child object "
                "with FUN_006885b0(manager+0x54, source_id-1)"
            ),
        },
    }


def build_sgb_placement_join(
    sgb_report: Mapping[str, Any],
) -> dict[str, Any]:
    if sgb_report.get("format") != SGB_FORMAT:
        raise ValueError("input must be SHIFT.SGBRuntime/1")

    flat_summ = _join_flat_summ(
        _chunk(sgb_report, "FLAT"),
        _chunk(sgb_report, "SUMM"),
    )
    part_node = _join_part_node(
        _chunk(sgb_report, "PART"),
        _chunk(sgb_report, "NODE"),
    )

    blockers = [
        *flat_summ.get("blocking_reasons", []),
        *part_node.get("blocking_reasons", []),
    ]
    present_modes = [
        name
        for name, value in (
            ("flat-summ", flat_summ),
            ("part-node", part_node),
        )
        if value.get("present")
    ]
    ready_modes = [
        name
        for name, value in (
            ("flat-summ", flat_summ),
            ("part-node", part_node),
        )
        if value.get("present") and value.get("ready")
    ]

    if not present_modes:
        blockers.append("placement:no-supported-spatial-mode")
    ready = bool(present_modes) and len(ready_modes) == len(present_modes) and not blockers

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "modes_present": present_modes,
        "modes_ready": ready_modes,
        "flat_summ": flat_summ,
        "part_node": part_node,
        "part_runtime_flat_materialization": {
            "source": "FUN_0068a810 -> FUN_006afd50 -> FUN_00689db0",
            "serialized_claim": False,
            "generated_leaf_bytes": 0x40,
            "generated_leaf_direct_object_pointer_offset": 0x38,
            "generated_leaf_runtime_index_offset": 0x3C,
            "direct_object_pointer_source": (
                "PART child runtime wrapper entry +0x0c"
            ),
            "runtime_index_source": "sequential traversal ordinal",
            "secondary_slot_copy": "FUN_00687b00",
            "secondary_backrefs": {
                "partition_node": 0x30,
                "generated_leaf": 0x34,
                "primary_slot": 0x38,
            },
            "boundary": (
                "This proves runtime equivalence between PART child placement "
                "and FLAT index-table geometry; it does not claim that PART "
                "records serialize FLAT leaf +0x38 pointers."
            ),
        },
        "evidence": {
            "sgb_dispatch": "FUN_006a5270",
            "node_loader": "FUN_006a4b40",
            "part_loader": "FUN_006a4d10",
            "flat_loader": "FUN_006a48d0",
            "summ_loader": "FUN_006a4900",
        },
    }


def validate_file(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("SGB runtime input must be a JSON object")
    return build_sgb_placement_join(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Join SGB NODE/SUMM wrappers to PART/FLAT placement"
    )
    parser.add_argument("sgb_runtime")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_file(args.sgb_runtime)
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "modes_present": report["modes_present"],
        "modes_ready": report["modes_ready"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
