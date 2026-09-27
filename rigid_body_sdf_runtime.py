"""Source-backed parser for SHIFT rigid-body suspension SDF resources.

The retail loader is FUN_007b6900 in SHIFT.exe.c. It recognizes BODY, JOINT,
HINGE, BAR and JOINT&HINGE records. This module preserves the text faithfully
and normalizes only the fields that the loader explicitly reads.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.RigidBodySDFRuntime/1"
SOURCE_LOADER = "FUN_007b6900"
SECTIONS = ("BODY", "JOINT", "HINGE", "BAR", "JOINT&HINGE")

_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
_ASSIGN_RE = re.compile(r"^\s*([^=]+?)\s*=\s*(.*?)\s*$")
_NUM_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")

BODY_KEYS = {
    "name": "string",
    "mass": "scalar",
    "inertia": "tuple3",
    "pos": "tuple3",
    "ori": "tuple3",
    "vel": "tuple3",
    "rot": "tuple3",
}
CONSTRAINT_KEYS = {
    "name": "string",
    "posbody": "string",
    "negbody": "string",
    "axis": "tuple3",
    "neg": "tuple3",
    "pos": "tuple3-or-string",
}


def _atom(value: str) -> Any:
    value = value.strip()
    low = value.lower()
    if low in {"true", "false"}:
        return low == "true"
    if _NUM_RE.fullmatch(value):
        return float(value)
    return value.strip('"')


def _value(value: str) -> tuple[Any, str]:
    raw = value.strip()
    if raw.startswith("(") and raw.endswith(")"):
        inner = raw[1:-1].strip()
        parts = [] if not inner else [part.strip() for part in inner.split(",")]
        values = [_atom(part) for part in parts]
        if len(values) == 1:
            return values[0], "scalar"
        return values, f"tuple{len(values)}"
    if "," in raw:
        values = [_atom(part) for part in raw.split(",")]
        return values, f"tuple{len(values)}"
    return _atom(raw), "scalar" if _NUM_RE.fullmatch(raw) else "string"


def parse_sdf(data: str | bytes, *, strict: bool = False) -> dict[str, Any]:
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else str(data)
    records: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    warnings: list[str] = []

    for line_no, original in enumerate(text.splitlines(), 1):
        stripped = original.split("//", 1)[0].strip()
        if not stripped:
            continue

        match = _SECTION_RE.match(stripped)
        if match:
            name = match.group(1).strip().upper()
            current = {
                "section": name,
                "source_section": match.group(1).strip(),
                "line": line_no,
                "entries": [],
            }
            records.append(current)
            continue

        if current is None:
            warnings.append(f"line:{line_no}:property-before-section")
            if strict:
                raise ValueError(warnings[-1])
            continue

        # Real SDF lines pack multiple key=value assignments on one line.
        matches = list(re.finditer(r"([A-Za-z_][A-Za-z0-9_&]*)\s*=", stripped))
        if not matches:
            warnings.append(f"line:{line_no}:unparsed:{original.strip()}")
            if strict:
                raise ValueError(warnings[-1])
            continue

        schema = BODY_KEYS if current["section"] == "BODY" else CONSTRAINT_KEYS
        for index, match in enumerate(matches):
            key = match.group(1).strip()
            value_start = match.end()
            value_end = matches[index + 1].start() if index + 1 < len(matches) else len(stripped)
            raw = stripped[value_start:value_end].strip()
            if not raw:
                warnings.append(f"line:{line_no}:empty-value:{key}")
                if strict:
                    raise ValueError(warnings[-1])
                continue
            value, shape = _value(raw)
            expected_shape = schema.get(key)
            current["entries"].append({
                "name": key,
                "raw": raw,
                "value": value,
                "parsed_shape": shape,
                "line": line_no,
                "recognized_by_loader": expected_shape is not None,
                "loader_shape": expected_shape,
            })

    counts = {section: 0 for section in SECTIONS}
    for record in records:
        counts[record["section"]] = counts.get(record["section"], 0) + 1

    recognized = sum(
        1 for record in records
        for entry in record["entries"]
        if entry["recognized_by_loader"]
    )
    unknown = sum(
        1 for record in records
        for entry in record["entries"]
        if not entry["recognized_by_loader"]
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "parsed" if not warnings else "parsed-with-warnings",
        "ready": not warnings,
        "source": {
            "file": "SHIFT.exe.c",
            "loader": SOURCE_LOADER,
            "recognized_sections": list(SECTIONS),
        },
        "record_count": len(records),
        "entry_count": sum(len(record["entries"]) for record in records),
        "recognized_entry_count": recognized,
        "unknown_entry_count": unknown,
        "topology": {
            "body_count": counts.get("BODY", 0),
            "joint_count": counts.get("JOINT", 0) + counts.get("JOINT&HINGE", 0),
            "hinge_count": counts.get("HINGE", 0) + counts.get("JOINT&HINGE", 0),
            "bar_count": counts.get("BAR", 0),
            "joint_hinge_count": counts.get("JOINT&HINGE", 0),
            "combined_slot_weight": counts.get("JOINT&HINGE", 0) * 3,
        },
        "records": records,
        "warnings": warnings,
        "evidence": {
            "record_count_fields": {
                "bodies": "+0x10",
                "joints": "+0x18",
                "hinges": "+0x20",
                "bars": "+0x28",
                "joint_hinge_aux": "+0x30",
            },
            "body_array_stride": "0x170",
            "joint_array_stride": "0xa0",
            "hinge_array_stride": "0xa0",
            "bar_array_stride": "0xb8",
            "constraint_name_fields": ["name", "posbody", "negbody"],
            "constraint_vector_fields": ["axis", "neg", "pos"],
        },
        "limitations": [
            "Actual PhysX object construction in FUN_007b3150 is not reproduced here.",
            "Lengths/constraints are parsed structurally; no physical-unit normalization is attempted.",
            "Unknown keys remain in the IR rather than being discarded.",
        ],
    }


def describe_sdf_body_runtime_lowering(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    """Describe FUN_007b3670's proven BODY -> 0x170-byte runtime lowering."""
    body_records = records_by_type(report, "BODY")
    rows: list[dict[str, Any]] = []
    duplicate_names: set[str] = set()
    seen: set[str] = set()

    for index, record in enumerate(body_records):
        values = {
            str(entry.get("name")): entry.get("value")
            for entry in record.get("entries") or []
        }
        raw_name = values.get("name")
        name = "" if raw_name is None else str(raw_name)
        normalized = name.upper()
        if normalized in seen:
            duplicate_names.add(normalized)
        seen.add(normalized)
        rows.append({
            "index": index,
            "name": name,
            "normalized_name": normalized,
            "runtime_stride": 0x170,
            "lowering": {
                "name": {"descriptor": "+0x20", "runtime": "+0x100", "helper": "FUN_007bba90"},
                "mass": {"descriptor": "+0x120", "runtime": "+0x120", "inverse": "+0x90"},
                "inertia": {
                    "descriptor": "+0x128/+0x12c/+0x130",
                    "runtime": "+0x128/+0x12c/+0x130",
                    "inverse": "+0x138/+0x140/+0x148",
                },
                "group_a": {"descriptor": "+0x108/+0x110/+0x118", "helper": "FUN_007bbb10"},
                "group_b": {"descriptor": "+0x018/+0x020/+0x028", "helper": "FUN_007bbb60"},
            },
            "constructor": "FUN_007b3670",
        })

    return {
        "format": "SHIFT.SDFBodyRuntimeLowering/1",
        "version": 1,
        "status": "ready" if not duplicate_names else "blocked",
        "ready": not duplicate_names,
        "body_count": len(rows),
        "duplicate_names": sorted(duplicate_names),
        "runtime_stride": 0x170,
        "rows": rows,
        "evidence": {
            "body_builder": "FUN_007b3670",
            "mass_inertia_initializer": "FUN_007bba90",
            "group_a_copy": "FUN_007bbb10",
            "group_b_copy": "FUN_007bbb60",
        },
        "limitations": [
            "Group A/B semantic names are deliberately not inferred from the decompiler's opaque temporary structure.",
        ],
    }



def resolve_sdf_body_references(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve posbody/negbody names into a neutral SDF connectivity graph."""
    ordered_body_names = [
        str(entry.get("value")).upper()
        for record in report.get("records") or []
        if record.get("section") == "BODY"
        for entry in record.get("entries") or []
        if entry.get("name") == "name"
    ]
    body_names = set(ordered_body_names)
    duplicate_names = sorted({
        name for name in body_names if ordered_body_names.count(name) > 1
    })
    edges: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for record_index, record in enumerate(report.get("records") or []):
        if record.get("section") == "BODY":
            continue
        values = {
            str(entry.get("name")): entry.get("value")
            for entry in record.get("entries") or []
        }
        posbody = values.get("posbody")
        negbody = values.get("negbody")
        if posbody is None and negbody is None:
            continue
        for field, body in (("posbody", posbody), ("negbody", negbody)):
            if body is None:
                continue
            name = str(body).upper()
            if name not in body_names:
                unresolved.append(
                    f"record:{record_index}:{record.get('section')}:{field}:{name}"
                )
        posbody_key = "" if posbody is None else str(posbody).upper()
        negbody_key = "" if negbody is None else str(negbody).upper()
        edges.append({
            "record_index": record_index,
            "section": record.get("section"),
            "posbody": None if posbody is None else posbody_key,
            "negbody": None if negbody is None else negbody_key,
            "resolved": all(
                body is None or str(body).upper() in body_names
                for body in (posbody, negbody)
            ),
        })

    adjacency: dict[str, list[int]] = {name: [] for name in sorted(body_names)}
    for edge_index, edge in enumerate(edges):
        for body in (edge.get("posbody"), edge.get("negbody")):
            if body in adjacency:
                adjacency[body].append(edge_index)

    unresolved = list(dict.fromkeys(
        unresolved + [f"duplicate-body-name:{name}" for name in duplicate_names]
    ))
    return {
        "status": "resolved" if not unresolved else "blocked",
        "ready": not unresolved,
        "body_names": sorted(body_names),
        "duplicate_body_names": duplicate_names,
        "edge_count": len(edges),
        "edges": edges,
        "unresolved": unresolved,
        "adjacency": adjacency,
        "evidence": {
            "loader": SOURCE_LOADER,
            "body_reference_fields": ["posbody", "negbody"],
        },
    }



SDF_FLAG_JOINT = 0x01
SDF_FLAG_HINGE = 0x02
SDF_FLAG_BAR = 0x04


def sdf_constraint_solver_width(section: str) -> int:
    """Return the scalar solver-node width used by FUN_007b1b60."""
    wanted = str(section).upper()
    if wanted == "JOINT":
        return 3
    if wanted == "HINGE":
        return 2
    if wanted == "BAR":
        return 1
    raise ValueError(f"unsupported SDF solver section: {section}")



def compile_sdf_runtime_topology(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    """Lower parsed SDF records into the proven FUN_007b3150 topology boundary.

    JOINT&HINGE is materialized into two runtime records: one JOINT and one
    HINGE. The returned order matches the source construction arrays.
    """
    body_records = records_by_type(report, "BODY")
    body_index = {
        str(next(
            (entry.get("value") for entry in record.get("entries", [])
             if entry.get("name") == "name"),
            ""
        )).upper(): index
        for index, record in enumerate(body_records)
    }

    materializations = {
        "JOINT": ("JOINT",),
        "HINGE": ("HINGE",),
        "BAR": ("BAR",),
        "JOINT&HINGE": ("JOINT", "HINGE"),
    }
    strides = {"JOINT": 0xA0, "HINGE": 0xA0, "BAR": 0xB8}

    constraints: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for source_record_index, record in enumerate(report.get("records") or []):
        source_section = str(record.get("section", "")).upper()
        runtime_sections = materializations.get(source_section)
        if runtime_sections is None:
            continue

        values = {
            str(entry.get("name")): entry.get("value")
            for entry in record.get("entries") or []
        }
        posbody = values.get("posbody")
        negbody = values.get("negbody")
        posbody_key = "" if posbody is None else str(posbody).upper()
        negbody_key = "" if negbody is None else str(negbody).upper()
        if posbody_key and posbody_key not in body_index:
            unresolved.append(
                f"record:{source_record_index}:posbody:{posbody}"
            )
        if negbody_key and negbody_key not in body_index:
            unresolved.append(
                f"record:{source_record_index}:negbody:{negbody}"
            )

        vectors: dict[str, Any] = {}
        for key in ("axis", "neg", "pos"):
            value = values.get(key)
            if isinstance(value, list) and len(value) == 3:
                vectors[key] = [float(component) for component in value]
        if isinstance(values.get("pos"), str):
            vectors["copy_body_name"] = str(values["pos"])

        for materialization in runtime_sections:
            flag_word = {
                "JOINT": SDF_FLAG_JOINT,
                "HINGE": SDF_FLAG_HINGE,
                "BAR": SDF_FLAG_BAR,
            }[materialization]
            constraints.append({
                "source_record_index": source_record_index,
                "source_section": source_section,
                "section": materialization,
                "flags": {
                    "joint": materialization == "JOINT",
                    "hinge": materialization == "HINGE",
                    "bar": materialization == "BAR",
                },
                "flag_word": flag_word,
                "posbody": posbody,
                "negbody": negbody,
                "posbody_index": body_index.get(posbody_key),
                "negbody_index": body_index.get(negbody_key),
                "vectors": dict(vectors),
                "runtime_stride": strides[materialization],
                "solver_width": sdf_constraint_solver_width(materialization),
                "body_pointer_slots": {
                    "posbody": "+0x78",
                    "negbody": "+0x80",
                },
                "source_constructor": "FUN_007b3150",
                "array_slot": {
                    "JOINT": "+0x1c",
                    "HINGE": "+0x24",
                    "BAR": "+0x2c",
                }[materialization],
            })

    return {
        "format": "SHIFT.SDFRuntimeTopology/2",
        "version": 2,
        "status": "compiled" if not unresolved else "blocked",
        "ready": not unresolved,
        "body_count": len(body_records),
        "body_names": sorted(body_index),
        "constraint_count": len(constraints),
        "constraints": constraints,
        "unresolved": list(dict.fromkeys(unresolved)),
        "allocation": {
            "body_stride": 0x170,
            "joint_stride": 0xA0,
            "hinge_stride": 0xA0,
            "bar_stride": 0xB8,
        },
        "evidence": {
            "constructor": "FUN_007b3150",
            "joint_flag": "byte +0x10 & 1",
            "hinge_flag": "byte +0x10 & 2",
            "bar_flag": "byte +0x10 & 4",
            "joint_hinge_materialization": "JOINT&HINGE source record emits JOINT then HINGE runtime records",
            "posbody_runtime_slot": "+0x78",
            "negbody_runtime_slot": "+0x80",
            "bar_endpoint_vectors": ["+0x28", "+0x30", "+0x38", "+0x40", "+0x48", "+0x50"],
        },
        "limitations": [
            "PhysX object classes and SDK calls remain opaque.",
            "A string-valued pos is preserved as the source copy-body name; no gameplay anchor semantics are inferred.",
        ],
    }





def build_sdf_constraint_connectivity_matrix(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the source-visible constraint graph input used before FUN_007b1360.

    FUN_007b1b60 compares every pair of runtime constraints and connects two
    nodes when they share either endpoint body. JOINT&HINGE has already been
    split into two runtime nodes by compile_sdf_runtime_topology().
    """
    topology = compile_sdf_runtime_topology(report)
    if topology.get("ready") is not True:
        return {
            "format": "SHIFT.SDFConstraintConnectivityMatrix/1",
            "version": 1,
            "status": "blocked",
            "ready": False,
            "constraint_count": topology.get("constraint_count", 0),
            "matrix": [],
            "unresolved": list(topology.get("unresolved") or []),
            "evidence": {
                "source_builder": "FUN_007b1b60",
                "endpoint_fields": ["posbody", "negbody"],
            },
        }

    constraints = topology.get("constraints") or []
    n = len(constraints)
    matrix = [[0.0 for _ in range(n)] for _ in range(n)]
    shared_body_pairs: list[dict[str, int | str]] = []
    for left in range(n):
        left_bodies = {
            str(constraints[left].get("posbody")).upper()
            if constraints[left].get("posbody") is not None else "",
            str(constraints[left].get("negbody")).upper()
            if constraints[left].get("negbody") is not None else "",
        }
        for right in range(left + 1, n):
            right_bodies = {
                str(constraints[right].get("posbody")).upper()
                if constraints[right].get("posbody") is not None else "",
                str(constraints[right].get("negbody")).upper()
                if constraints[right].get("negbody") is not None else "",
            }
            shared = sorted((left_bodies & right_bodies) - {""})
            if not shared:
                continue
            matrix[left][right] = 1.0
            matrix[right][left] = 1.0
            shared_body_pairs.append({
                "left": left,
                "right": right,
                "shared_body": shared[0],
            })

    return {
        "format": "SHIFT.SDFConstraintConnectivityMatrix/1",
        "version": 1,
        "status": "ready",
        "ready": True,
        "constraint_count": n,
        "matrix": matrix,
        "shared_body_pair_count": len(shared_body_pairs),
        "shared_body_pairs": shared_body_pairs,
        "node_widths": [
            3 if row.get("section") == "JOINT"
            else 2 if row.get("section") == "HINGE"
            else 1
            for row in constraints
        ],
        "evidence": {
            "source_builder": "FUN_007b1b60",
            "endpoint_fields": ["posbody", "negbody"],
            "joint_block_width": 3,
            "hinge_block_width": 2,
            "bar_block_width": 1,
            "comparison_rule": "any shared posbody/negbody endpoint connects two constraint nodes",
        },
        "limitations": [
            "This reproduces the proven endpoint-sharing graph; the separate FUN_007b1b60 ordering heuristic is not applied here.",
            "The source writes integer/double matrix values, but only zero/nonzero connectivity is exposed.",
        ],
    }


def optimize_sdf_constraint_order(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    """Recover FUN_007b1b60's constraint permutation heuristic."""
    connectivity = build_sdf_constraint_connectivity_matrix(report)
    if connectivity.get("ready") is not True:
        return {
            "format": "SHIFT.SDFConstraintOrder/1",
            "version": 1,
            "status": "blocked",
            "ready": False,
            "order": [],
            "position_by_node": [],
            "unresolved": list(connectivity.get("unresolved") or []),
            "evidence": {"source_function": "FUN_007b1b60"},
        }

    matrix = connectivity["matrix"]
    widths = [int(value) for value in connectivity["node_widths"]]
    n = len(widths)
    pairs = [
        (int(item["left"]), int(item["right"]))
        for item in connectivity["shared_body_pairs"]
    ]

    order = list(range(n))
    position_by_node = list(range(n))

    def block_offsets(current_order: Sequence[int]) -> list[int]:
        offsets = [0] * n
        cursor = 0
        for node in current_order:
            offsets[node] = cursor
            cursor += widths[node]
        return offsets

    def cost(offsets: Sequence[int]) -> int:
        return sum((offsets[left] - offsets[right]) ** 2 for left, right in pairs)

    offsets = block_offsets(order)
    initial_cost = cost(offsets)
    best_cost = initial_cost
    best_position = list(position_by_node)
    improvement_count = 0
    pass_count = 0

    while True:
        improved_this_pass = False
        pass_count += 1
        for node in range(max(0, n - 1)):
            phase = 0
            while phase < 2:
                current_position = position_by_node[node]
                if phase == 0:
                    if current_position == 0:
                        phase = 1
                        continue
                    other = order[current_position - 1]
                    order[current_position - 1], order[current_position] = (
                        order[current_position],
                        order[current_position - 1],
                    )
                    position_by_node[node] -= 1
                    position_by_node[other] += 1
                else:
                    if current_position >= n - 1:
                        phase += 1
                        continue
                    other = order[current_position + 1]
                    order[current_position], order[current_position + 1] = (
                        order[current_position + 1],
                        order[current_position],
                    )
                    position_by_node[node] += 1
                    position_by_node[other] -= 1

                candidate_cost = cost(block_offsets(order))
                if candidate_cost < best_cost:
                    best_cost = candidate_cost
                    best_position = list(position_by_node)
                    improvement_count += 1
                    improved_this_pass = True
                    continue

                position_by_node = list(best_position)
                order = [0] * n
                for candidate_node, candidate_position in enumerate(position_by_node):
                    order[candidate_position] = candidate_node
                phase += 1

        if not improved_this_pass:
            break

    return {
        "format": "SHIFT.SDFConstraintOrder/1",
        "version": 1,
        "status": "optimized",
        "ready": True,
        "constraint_count": n,
        "solver_scalar_count": sum(widths),
        "order": order,
        "position_by_node": best_position,
        "block_widths": widths,
        "block_offsets": block_offsets(order),
        "initial_cost": initial_cost,
        "final_cost": best_cost,
        "improvement_count": improvement_count,
        "pass_count": pass_count,
        "connectivity": connectivity,
        "evidence": {
            "source_function": "FUN_007b1b60",
            "pair_rule": "constraints sharing posbody/negbody are paired",
            "joint_block_width": 3,
            "hinge_block_width": 2,
            "bar_block_width": 1,
            "objective": "sum((block_offset[left] - block_offset[right])^2)",
            "search": "repeated accepted adjacent left/right moves until no improvement",
        },
        "limitations": [
            "The upstream FUN_007b2010/FUN_007ba2b0 matrix population is represented by its proven endpoint-sharing relation, not by unknown coefficient values.",
        ],
    }



def compile_sdf_constraint_solver_graph(
    matrix: Sequence[Sequence[float | int]],
) -> dict[str, Any]:
    """Lower an ordered constraint connectivity matrix through FUN_007b1360.

    The input matrix is assumed to already have the constraint order selected by
    FUN_007b1b60. The function returns the compact forward/reverse dependency
    records consumed by FUN_007b0f20.
    """
    n = len(matrix)
    if any(len(row) != n for row in matrix):
        raise ValueError("constraint connectivity matrix must be square")

    work = [
        [1.0 if float(value) != 0.0 else 0.0 for value in row]
        for row in matrix
    ]

    # First source pass: retain the lower triangle, symmetrize it, and count
    # records. A temporary 2.0 marks an inferred two-hop relation.
    edge_record_count = 0
    for column in range(n):
        for row in range(column, n):
            if work[row][column] == 0.0 and column > 0:
                for via in range(column):
                    if work[row][via] != 0.0 and work[via][column] != 0.0:
                        work[row][column] = 2.0
                        break
            if work[row][column] != 0.0:
                edge_record_count += 1
            work[column][row] = work[row][column]

    # FUN_007b1360 always reserves one terminal forward record per node.
    edge_record_count += n

    for row in range(n):
        for column in range(n):
            if work[row][column] == 2.0:
                work[row][column] = 0.0

    dependency_byte_count = 0
    forward_records: list[dict[str, Any]] = []
    edge_pool: list[dict[str, Any]] = []

    for column in range(n + 1):
        items: list[dict[str, Any]] = []
        if column == n:
            for row in range(n):
                dependencies = [
                    via
                    for via in range(row)
                    if work[row][via] != 0.0
                ]
                item = {
                    "node": row,
                    "dependency_count": len(dependencies),
                    "dependencies": dependencies,
                }
                items.append(item)
                edge_pool.append({
                    "outer_record": column,
                    **item,
                })
                dependency_byte_count += len(dependencies)
        else:
            for row in range(column, n):
                if work[row][column] == 0.0 and column > 0:
                    for via in range(column):
                        if work[row][via] != 0.0 and work[via][column] != 0.0:
                            work[row][column] = 2.0
                            break
                if work[row][column] == 0.0:
                    continue
                dependencies = [
                    via
                    for via in range(column)
                    if work[row][via] != 0.0 and work[via][column] != 0.0
                ]
                item = {
                    "node": row,
                    "dependency_count": len(dependencies),
                    "dependencies": dependencies,
                }
                items.append(item)
                edge_pool.append({
                    "outer_record": column,
                    **item,
                })
                dependency_byte_count += len(dependencies)
                work[column][row] = work[row][column]

        forward_records.append({
            "count": len(items),
            "items": items,
        })

    reverse_records: list[dict[str, Any]] = []
    for row in range(n - 1, -1, -1):
        dependencies = [
            column
            for column in range(row + 1, n)
            if work[row][column] != 0.0
        ]
        reverse_records.append({
            "node": row,
            "dependency_count": len(dependencies),
            "dependencies": dependencies,
        })
        dependency_byte_count += len(dependencies)

    if len(edge_pool) != edge_record_count:
        # The retail routine's allocation size is deterministic. Expose a
        # mismatch instead of silently fabricating a compatible layout.
        raise RuntimeError(
            f"FUN_007b1360 record-count mismatch: expected {edge_record_count}, "
            f"built {len(edge_pool)}"
        )

    return {
        "format": "SHIFT.SDFConstraintSolverGraph/1",
        "version": 1,
        "status": "compiled",
        "ready": True,
        "constraint_count": n,
        "initial_solution": [1.0] * n,
        "normalized_matrix": [
            list(row) for row in work
        ],
        "forward_records": forward_records,
        "reverse_records": reverse_records,
        "edge_record_pool": edge_pool,
        "allocations": {
            "forward_table_bytes": (n + 1) * 8,
            "reverse_table_bytes": n * 8,
            "edge_record_bytes": edge_record_count * 8,
            "dependency_index_bytes": dependency_byte_count,
            "edge_record_count": edge_record_count,
            "dependency_index_count": dependency_byte_count,
        },
        "storage": {
            "forward_outer_stride": 8,
            "reverse_record_stride": 8,
            "edge_record_stride": 8,
            "dependency_index_width": 1,
            "forward_outer_count": n + 1,
            "reverse_record_count": n,
            "forward_item_layout": {
                "node": "byte +0x00",
                "dependency_count": "byte +0x01",
                "dependency_pointer": "u32 +0x04",
            },
        },
        "evidence": {
            "source_function": "FUN_007b1360",
            "consumer": "FUN_007b0f20",
            "reset_helper": "FUN_007b10d0",
            "initial_solution_value": 1.0,
            "terminal_forward_record": "outer index == constraint_count",
            "reverse_order": "constraint_count-1 down to 0",
            "inferred_relation_marker": 2.0,
            "inferred_relation_cleared_before_output": True,
        },
        "limitations": [
            "The input order must already represent FUN_007b1b60's optimized constraint permutation.",
            "The actual matrix coefficients remain owned by the upstream FUN_007b2010/FUN_007ba2b0 path.",
        ],
    }



def build_sdf_scalar_connectivity_matrix(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    """Expand record connectivity into the scalar node domain used by the solver."""
    ordering = optimize_sdf_constraint_order(report)
    if ordering.get("ready") is not True:
        return {
            "format": "SHIFT.SDFScalarConnectivityMatrix/1",
            "version": 1,
            "status": "blocked",
            "ready": False,
            "constraint_record_count": ordering.get("constraint_count", 0),
            "solver_scalar_count": 0,
            "matrix": [],
            "unresolved": list(ordering.get("unresolved") or []),
            "evidence": {
                "source_function": "FUN_007ba2b0",
                "order_source": "FUN_007b1b60",
            },
        }

    record_matrix = ordering["connectivity"]["matrix"]
    order = list(ordering["order"])
    widths = [int(value) for value in ordering["block_widths"]]
    record_count = len(order)
    ordered_widths = [widths[node] for node in order]
    offsets_by_position: list[int] = []
    cursor = 0
    for width in ordered_widths:
        offsets_by_position.append(cursor)
        cursor += width
    scalar_count = cursor

    scalar_matrix = [
        [0.0 for _ in range(scalar_count)]
        for _ in range(scalar_count)
    ]
    shared_blocks: list[dict[str, Any]] = []
    for ordered_left in range(record_count):
        left_start = offsets_by_position[ordered_left]
        left_width = ordered_widths[ordered_left]
        for left_scalar in range(left_start, left_start + left_width):
            for right_scalar in range(left_start, left_start + left_width):
                scalar_matrix[left_scalar][right_scalar] = 1.0
        original_left = order[ordered_left]
        for ordered_right in range(ordered_left + 1, record_count):
            original_right = order[ordered_right]
            if float(record_matrix[original_left][original_right]) == 0.0:
                continue
            right_start = offsets_by_position[ordered_right]
            right_width = ordered_widths[ordered_right]
            shared_blocks.append({
                "left_record": original_left,
                "right_record": original_right,
                "left_scalar_range": [left_start, left_start + left_width],
                "right_scalar_range": [right_start, right_start + right_width],
            })
            for left_scalar in range(left_start, left_start + left_width):
                for right_scalar in range(right_start, right_start + right_width):
                    scalar_matrix[left_scalar][right_scalar] = 1.0
                    scalar_matrix[right_scalar][left_scalar] = 1.0

    solver_base_index_by_record = {
        int(order[position]): int(offsets_by_position[position])
        for position in range(record_count)
    }
    return {
        "format": "SHIFT.SDFScalarConnectivityMatrix/1",
        "version": 1,
        "status": "ready",
        "ready": True,
        "constraint_record_count": record_count,
        "solver_scalar_count": scalar_count,
        "order": order,
        "block_widths": widths,
        "ordered_block_widths": ordered_widths,
        "scalar_block_offsets": offsets_by_position,
        "solver_base_index_by_record": solver_base_index_by_record,
        "matrix": scalar_matrix,
        "shared_block_count": len(shared_blocks),
        "shared_blocks": shared_blocks,
        "evidence": {
            "source_function": "FUN_007ba2b0",
            "order_source": "FUN_007b1b60",
            "scalar_matrix_rule": "shared runtime constraint records set every cross-product entry of their scalar blocks to 1.0",
            "joint_width": 3,
            "hinge_width": 2,
            "bar_width": 1,
        },
        "limitations": [
            "This exposes the coefficient writes proven by FUN_007ba2b0 before FUN_007b2210 resets selected solver rows/columns.",
            "Directional sample transforms, physical Jacobian meaning and provider-specific coefficients remain outside this contract.",
        ],
    }




def compile_sdf_constraint_solver_graph_from_report(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    """Build scalar connectivity, recover source order, then apply FUN_007b1360."""
    scalar = build_sdf_scalar_connectivity_matrix(report)
    if scalar.get("ready") is not True:
        return {
            "format": "SHIFT.SDFConstraintSolverGraph/2",
            "version": 2,
            "status": "blocked",
            "ready": False,
            "scalar_connectivity": scalar,
            "unresolved": list(scalar.get("unresolved") or []),
        }

    graph = compile_sdf_constraint_solver_graph(scalar["matrix"])
    return {
        **graph,
        "format": "SHIFT.SDFConstraintSolverGraph/2",
        "version": 2,
        "constraint_record_count": scalar["constraint_record_count"],
        "solver_scalar_count": scalar["solver_scalar_count"],
        "scalar_connectivity": scalar,
        "source_constraint_order": scalar["order"],
    }




def describe_sdf_constraint_runtime_lowering(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    """Describe the source-backed FUN_007b3150 constraint materialization map.

    One source record can materialize more than one runtime record: the retail
    JOINT&HINGE path emits separate JOINT and HINGE records.
    """
    materialization_specs = {
        "JOINT": {
            "runtime_section": "JOINT",
            "flag_bit": SDF_FLAG_JOINT,
            "runtime_stride": 0xA0,
            "body_counter_offset": "+0x98",
            "array_slot": "+0x1c",
            "source_value_fields": ["pos"],
            "source_descriptor_offsets": ["+0x28", "+0x30", "+0x38"],
            "runtime_vector_offsets": ["+0x88", "+0x90", "+0x98"],
            "sample_helper": "FUN_007ba8b0",
            "sample_stride": 0x40,
            "postload_helper": "FUN_007b2da0",
        },
        "HINGE": {
            "runtime_section": "HINGE",
            "flag_bit": SDF_FLAG_HINGE,
            "runtime_stride": 0xA0,
            "body_counter_offset": "+0x9c",
            "array_slot": "+0x24",
            "source_value_fields": ["axis"],
            "source_descriptor_offsets": ["+0x58", "+0x60", "+0x68"],
            "runtime_vector_offsets": ["+0x88", "+0x90", "+0x98"],
            "sample_helper": "FUN_007ba900",
            "sample_stride": 0xA0,
            "postload_helper": "FUN_007b2de0",
        },
        "BAR": {
            "runtime_section": "BAR",
            "flag_bit": SDF_FLAG_BAR,
            "runtime_stride": 0xB8,
            "body_counter_offset": "+0xa0",
            "array_slot": "+0x2c",
            "source_value_fields": ["pos", "neg"],
            "source_descriptor_offsets": [
                "+0x28", "+0x30", "+0x38", "+0x40", "+0x48", "+0x50"
            ],
            "runtime_vector_offsets": [
                "+0x88", "+0x90", "+0x98", "+0xa0", "+0xa8", "+0xb0"
            ],
            "sample_helper": "FUN_007ba990",
            "sample_stride": 0x60,
            "postload_helper": "FUN_007b2f70",
        },
    }
    source_to_materializations = {
        "JOINT": ("JOINT",),
        "HINGE": ("HINGE",),
        "BAR": ("BAR",),
        "JOINT&HINGE": ("JOINT", "HINGE"),
    }

    rows: list[dict[str, Any]] = []
    unresolved: list[str] = []
    source_record_count = 0
    for record_index, record in enumerate(report.get("records") or []):
        source_section = str(record.get("section", "")).upper()
        materializations = source_to_materializations.get(source_section)
        if materializations is None:
            continue
        source_record_count += 1
        values = {
            str(entry.get("name")): entry.get("value")
            for entry in record.get("entries") or []
        }
        posbody = values.get("posbody")
        negbody = values.get("negbody")
        for field, body in (("posbody", posbody), ("negbody", negbody)):
            if body is None:
                unresolved.append(
                    f"record:{record_index}:{source_section}:missing-{field}"
                )

        for materialization in materializations:
            spec = materialization_specs[materialization]
            rows.append({
                "source_record_index": record_index,
                "source_section": source_section,
                "runtime_section": spec["runtime_section"],
                "materialization": materialization,
                "name": values.get("name"),
                "posbody": posbody,
                "negbody": negbody,
                "flags": {
                    "joint": materialization == "JOINT",
                    "hinge": materialization == "HINGE",
                    "bar": materialization == "BAR",
                },
                "flag_word": spec["flag_bit"],
                "runtime_stride": spec["runtime_stride"],
                "array_slot": spec["array_slot"],
                "body_pointer_slots": {
                    "posbody": "+0x78",
                    "negbody": "+0x80",
                },
                "record_index_field": "+0x70",
                "endpoint_pointer_slots": {
                    "positive": "+0x7c",
                    "negative": "+0x84",
                },
                "body_counter_offset": spec["body_counter_offset"],
                "copy_helper": "FUN_007b2ae0",
                "source_descriptor": {
                    "common_flag_offset": "+0x10",
                    "string_fields": {
                        "constraint_name": "+0x14",
                        "posbody": "+0x18",
                        "negbody": "+0x1c",
                        "copy_body_name": "+0x20",
                    },
                    "common_string_offsets": ["+0x14", "+0x18", "+0x1c", "+0x20"],
                    "common_scalar_offsets": [
                        "+0x28", "+0x30", "+0x38", "+0x40", "+0x48", "+0x50",
                        "+0x58", "+0x60", "+0x68"
                    ],
                },
                "section_storage": {
                    "source_value_fields": spec["source_value_fields"],
                    "source_descriptor_offsets": spec["source_descriptor_offsets"],
                    "runtime_vector_offsets": spec["runtime_vector_offsets"],
                },
                "sampling": {
                    "helper": spec["sample_helper"],
                    "sample_stride": spec["sample_stride"],
                },
                "postload": {
                    "helper": spec["postload_helper"],
                },
            })

    return {
        "format": "SHIFT.SDFConstraintRuntimeLowering/2",
        "version": 2,
        "status": "ready" if not unresolved else "blocked",
        "ready": not unresolved,
        "source_record_count": source_record_count,
        "record_count": len(rows),
        "rows": rows,
        "unresolved": list(dict.fromkeys(unresolved)),
        "evidence": {
            "constructor": "FUN_007b3150",
            "body_record_lowering": "FUN_007b3670",
            "common_copy_helper": "FUN_007b2ae0",
            "joint_constructor_stage": "FUN_007ba8b0",
            "hinge_constructor_stage": "FUN_007ba900",
            "bar_constructor_stage": "FUN_007ba990",
            "joint_postload": "FUN_007b2da0",
            "hinge_postload": "FUN_007b2de0",
            "bar_postload": "FUN_007b2f70",
        },
        "limitations": [
            "The contract describes retail storage and helper boundaries, not concrete PhysX SDK classes.",
            "BAR endpoint source fields retain the exact structural names pos/neg; no gameplay label is inferred.",
            "Returned sample pointers remain opaque runtime allocations; only their proven strides/helpers are recorded.",
        ],
    }



def describe_sdf_pre_physx_build(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    """Expose deterministic pre-PhysX allocation/build phases of FUN_007b3820."""
    topology = compile_sdf_runtime_topology(report)
    solver_scalar_count = sum(
        sdf_constraint_solver_width(row["section"])
        for row in topology["constraints"]
    )
    joints = sum(1 for row in topology["constraints"] if row["section"] == "JOINT")
    hinges = sum(1 for row in topology["constraints"] if row["section"] == "HINGE")
    bars = sum(1 for row in topology["constraints"] if row["section"] == "BAR")
    return {
        "format": "SHIFT.SDFPrePhysXBuildRuntime/3",
        "version": 3,
        "status": "ready" if topology["ready"] else "blocked",
        "ready": topology["ready"],
        "counts": {
            "constraint_records": topology["constraint_count"],
            "solver_scalar_nodes": solver_scalar_count,
            "joints": joints,
            "hinges": hinges,
            "bars": bars,
            "bodies": topology["body_count"],
        },
        "allocations": {
            "per_joint_resolved_samples": joints * 2,
            "per_hinge_resolved_samples": hinges * 2,
            "per_bar_resolved_samples": bars * 2,
            "constraint_index_matrix_elements": solver_scalar_count * solver_scalar_count,
            "constraint_index_matrix_bytes": solver_scalar_count * solver_scalar_count * 8,
            "constraint_index_row_pointer_elements": solver_scalar_count,
            "constraint_index_row_pointer_bytes": solver_scalar_count * 4,
            "solver_initial_vector_elements": solver_scalar_count,
            "solver_initial_vector_bytes": solver_scalar_count * 8,
            "per_body_constraint_index_vector_elements": solver_scalar_count,
            "per_body_constraint_index_vector_bytes": solver_scalar_count * 4,
            "body_runtime_stride": 0x170,
            "joint_runtime_stride": 0xA0,
            "hinge_runtime_stride": 0xA0,
            "bar_runtime_stride": 0xB8,
        },
        "stages": [
            {"function": "FUN_007ba4e0", "purpose": "allocate/reset per-constraint sampled arrays"},
            {"function": "FUN_007b1b60", "purpose": "order runtime constraints and return scalar solver-node count"},
            {"function": "FUN_007b2010", "purpose": "clear/fill scalar constraint connectivity matrix"},
            {"function": "FUN_007ba8b0", "purpose": "joint endpoint sample generation"},
            {"function": "FUN_007ba900", "purpose": "hinge endpoint sample generation"},
            {"function": "FUN_007ba990", "purpose": "bar endpoint sample generation"},
            {"function": "FUN_007b2da0/FUN_007b2de0/FUN_007b2f70", "purpose": "copy generated sample transforms into runtime records"},
            {"function": "FUN_007b1360", "purpose": "build compact forward/reverse solver graph tables"},
        ],
        "topology": topology,
        "evidence": {
            "source_function": "FUN_007b3820",
            "scalar_count_source": "FUN_007b1b60 return stored at +0x34",
            "constraint_matrix_element_size": 8,
            "constraint_row_pointer_size": 4,
            "solver_initial_vector_element_size": 8,
            "per_body_constraint_index_element_size": 4,
        },
        "limitations": [
            "The selected backend/provider vtable is intentionally unnamed.",
            "This contract stops before claiming PhysX class construction or ownership semantics.",
        ],
    }





def records_by_type(report: Mapping[str, Any], section: str) -> list[Mapping[str, Any]]:
    wanted = section.strip().upper()
    return [
        record
        for record in report.get("records") or []
        if str(record.get("section", "")).upper() == wanted
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse SHIFT rigid-body SDF resources against the recovered runtime loader")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)

    report = parse_sdf(args.input.read_bytes(), strict=args.strict)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "record_count": report["record_count"],
        "topology": report["topology"],
        "warnings": len(report["warnings"]),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
