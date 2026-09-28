"""Source-backed pre-PhysX construction plan for SHIFT vehicle physics.

This module does not invent PhysX classes. It lowers the already proven SDF/body
runtime records into the exact allocation and field-write contract surrounding
FUN_007b3670, FUN_007b3150 and FUN_007b3820, leaving provider/SDK vtables as an
explicit backend boundary.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.PrePhysXConstructionRuntime/1"
BODY_RUNTIME_STRIDE = 0x170
JOINT_RUNTIME_STRIDE = 0xA0
HINGE_RUNTIME_STRIDE = 0xA0
BAR_RUNTIME_STRIDE = 0xB8
SOLVER_WIDTHS = {"JOINT": 3, "HINGE": 2, "BAR": 1}

BODY_SOURCE_TO_RUNTIME = {
    "name": {"source": "+0x20", "runtime": "+0x100", "helper": "FUN_007bba90"},
    "mass": {"source": "+0x120", "runtime": "+0x120", "inverse": "+0x90", "helper": "FUN_007bba90"},
    "inertia": {
        "source": ["+0x128", "+0x12c", "+0x130"],
        "runtime": ["+0x128", "+0x12c", "+0x130"],
        "inverse": ["+0x138", "+0x140", "+0x148"],
        "helper": "FUN_007bba90",
    },
    "group_a": {
        "runtime": ["+0x108", "+0x110", "+0x118"],
        "source": ["+0x108", "+0x110", "+0x118"],
        "helper": "FUN_007bbb10",
    },
    "group_b": {
        "runtime": ["+0x18", "+0x20", "+0x28"],
        "source": ["+0x18", "+0x20", "+0x28"],
        "helper": "FUN_007bbb60",
    },
}

CONSTRAINT_RUNTIME = {
    "common": {
        "posbody_pointer": "+0x78",
        "negbody_pointer": "+0x80",
        "solver_node": "+0x70",
        "materializer": "FUN_007b3150",
    },
    "JOINT": {
        "stride": JOINT_RUNTIME_STRIDE,
        "source_vectors": ["+0x28", "+0x30", "+0x38"],
        "runtime_vector": ["+0x88", "+0x90", "+0x98"],
        "vector_copy": "FUN_007b3150",
        "array_base": "+0x1c",
        "body_reference_counters": {"positive": "+0x98", "negative": "+0x9c"},
    },
    "HINGE": {
        "stride": HINGE_RUNTIME_STRIDE,
        "source_vectors": ["+0x58", "+0x60", "+0x68"],
        "runtime_vector": ["+0x88", "+0x90", "+0x98"],
        "vector_copy": "FUN_007b3150",
        "array_base": "+0x24",
        "body_reference_counters": {"positive": "+0x98", "negative": "+0x9c"},
    },
    "BAR": {
        "stride": BAR_RUNTIME_STRIDE,
        "source_vectors": ["+0x28", "+0x30", "+0x38", "+0x40", "+0x48", "+0x50"],
        "runtime_vector": ["+0x88", "+0x90", "+0x98", "+0xa0", "+0xa8", "+0xb0"],
        "vector_copy": "FUN_007b3150",
        "array_base": "+0x2c",
        "body_reference_counters": {"positive": "+0x98", "negative": "+0xa0"},
    },
}


def _records(report: Mapping[str, Any], section: str) -> list[Mapping[str, Any]]:
    wanted = str(section).upper()
    return [r for r in (report.get("records") or []) if str(r.get("section", "")).upper() == wanted]


def _values(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(entry.get("name")): entry.get("value")
        for entry in (record.get("entries") or [])
    }


def _body_names(report: Mapping[str, Any]) -> list[str]:
    names: list[str] = []
    for record in _records(report, "BODY"):
        value = _values(record).get("name")
        names.append("" if value is None else str(value).upper())
    return names


def _topology_counts(report: Mapping[str, Any]) -> dict[str, int]:
    counts = {"BODY": len(_records(report, "BODY")), "JOINT": 0, "HINGE": 0, "BAR": 0}
    counts["JOINT"] = len(_records(report, "JOINT")) + len(_records(report, "JOINT&HINGE"))
    counts["HINGE"] = len(_records(report, "HINGE")) + len(_records(report, "JOINT&HINGE"))
    counts["BAR"] = len(_records(report, "BAR"))
    return counts


def build_body_construction_plan(report: Mapping[str, Any]) -> dict[str, Any]:
    names = _body_names(report)
    seen: set[str] = set()
    duplicate_names: list[str] = []
    rows: list[dict[str, Any]] = []
    for index, record in enumerate(_records(report, "BODY")):
        values = _values(record)
        name = "" if values.get("name") is None else str(values["name"])
        key = name.upper()
        if key in seen and key not in duplicate_names:
            duplicate_names.append(key)
        seen.add(key)
        rows.append({
            "index": index,
            "name": name,
            "normalized_name": key,
            "record_stride": BODY_RUNTIME_STRIDE,
            "operations": [
                {"op": "copy", "field": "name", "source": "+0x20", "destination": "+0x100", "helper": "FUN_007bba90"},
                {"op": "copy", "field": "mass", "source": "+0x120", "destination": "+0x120", "helper": "FUN_007bba90"},
                {"op": "reciprocal", "field": "mass", "source": "+0x120", "destination": "+0x90", "helper": "FUN_007bba90"},
                {"op": "copy", "field": "inertia", "source": ["+0x128", "+0x12c", "+0x130"], "destination": ["+0x128", "+0x12c", "+0x130"], "helper": "FUN_007bba90"},
                {"op": "reciprocal", "field": "inertia", "source": ["+0x128", "+0x12c", "+0x130"], "destination": ["+0x138", "+0x140", "+0x148"], "helper": "FUN_007bba90"},
                {"op": "copy_vector", "field": "group_a", "source": ["+0x108", "+0x110", "+0x118"], "destination": ["+0x108", "+0x110", "+0x118"], "helper": "FUN_007bbb10"},
                {"op": "copy_vector", "field": "group_b", "source": ["+0x18", "+0x20", "+0x28"], "destination": ["+0x18", "+0x20", "+0x28"], "helper": "FUN_007bbb60"},
            ],
        })
    return {
        "status": "ready" if not duplicate_names else "blocked",
        "ready": not duplicate_names,
        "body_count": len(names),
        "duplicate_names": sorted(duplicate_names),
        "runtime_stride": BODY_RUNTIME_STRIDE,
        "allocation_bytes": len(names) * BODY_RUNTIME_STRIDE,
        "constructor": "FUN_007b3670",
        "helpers": {"mass_inertia": "FUN_007bba90", "group_a": "FUN_007bbb10", "group_b": "FUN_007bbb60"},
        "rows": rows,
    }


def build_constraint_construction_plan(report: Mapping[str, Any]) -> dict[str, Any]:
    body_names = set(_body_names(report))
    rows: list[dict[str, Any]] = []
    unresolved: list[str] = []
    runtime_index = 0
    for source_index, record in enumerate(report.get("records") or []):
        source_section = str(record.get("section", "")).upper()
        if source_section not in {"JOINT", "HINGE", "BAR", "JOINT&HINGE"}:
            continue
        values = _values(record)
        expansions = ("JOINT", "HINGE") if source_section == "JOINT&HINGE" else (source_section,)
        for field in ("posbody", "negbody"):
            value = values.get(field)
            if value is None:
                continue
            if str(value).upper() not in body_names:
                unresolved.append(f"record:{source_index}:{field}:{value}")
        for section in expansions:
            spec = CONSTRAINT_RUNTIME[section]
            rows.append({
                "runtime_index": runtime_index,
                "source_record_index": source_index,
                "source_section": source_section,
                "runtime_section": section,
                "runtime_stride": spec["stride"],
                "solver_width": SOLVER_WIDTHS[section],
                "body_references": {"positive": "+0x78", "negative": "+0x80"},
                "solver_node_offset": "+0x70",
                "source_vector_offsets": list(spec["source_vectors"]),
                "runtime_vector_offsets": list(spec["runtime_vector"]),
                "array_base": spec["array_base"],
                "body_reference_counters": dict(spec["body_reference_counters"]),
                "constructor": "FUN_007b3150",
                "copy_body_name": values.get("pos") if isinstance(values.get("pos"), str) else None,
                "vectors_present": {
                    "axis": isinstance(values.get("axis"), list) and len(values.get("axis")) == 3,
                    "neg": isinstance(values.get("neg"), list) and len(values.get("neg")) == 3,
                    "pos": isinstance(values.get("pos"), list) and len(values.get("pos")) == 3,
                },
            })
            runtime_index += 1
    return {
        "status": "ready" if not unresolved else "blocked",
        "ready": not unresolved,
        "runtime_record_count": len(rows),
        "unresolved": list(dict.fromkeys(unresolved)),
        "runtime_arrays": {
            "JOINT": {"stride": JOINT_RUNTIME_STRIDE, "count": sum(r["runtime_section"] == "JOINT" for r in rows), "bytes": sum(r["runtime_section"] == "JOINT" for r in rows) * JOINT_RUNTIME_STRIDE},
            "HINGE": {"stride": HINGE_RUNTIME_STRIDE, "count": sum(r["runtime_section"] == "HINGE" for r in rows), "bytes": sum(r["runtime_section"] == "HINGE" for r in rows) * HINGE_RUNTIME_STRIDE},
            "BAR": {"stride": BAR_RUNTIME_STRIDE, "count": sum(r["runtime_section"] == "BAR" for r in rows), "bytes": sum(r["runtime_section"] == "BAR" for r in rows) * BAR_RUNTIME_STRIDE},
        },
        "rows": rows,
    }


def build_prephysx_construction_plan(report: Mapping[str, Any]) -> dict[str, Any]:
    body = build_body_construction_plan(report)
    constraints = build_constraint_construction_plan(report)
    counts = _topology_counts(report)
    solver_scalar_count = (
        sum(r["solver_width"] for r in constraints["rows"])
        if constraints["ready"] else 0
    )
    body_count = body["body_count"]
    matrix_bytes = solver_scalar_count * solver_scalar_count * 8
    row_pointer_bytes = solver_scalar_count * 4
    compact_graph_bytes = solver_scalar_count * 8
    per_body = {
        "matrix_bytes": matrix_bytes,
        "row_storage_bytes": solver_scalar_count * 8,
        "index_vector_bytes": solver_scalar_count * 4,
    }
    errors: list[str] = []
    if not body["ready"]:
        errors.extend(f"duplicate-body-name:{name}" for name in body["duplicate_names"])
    errors.extend(constraints["unresolved"])
    if constraints["ready"] and solver_scalar_count <= 0 and body_count > 0:
        errors.append("non-empty-body-model-has-zero-solver-scalars")
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not errors else "blocked",
        "ready": not errors,
        "counts": {
            "bodies": body_count,
            "joint": counts["JOINT"],
            "hinge": counts["HINGE"],
            "bar": counts["BAR"],
            "runtime_constraints": constraints["runtime_record_count"],
            "solver_scalar_count": solver_scalar_count,
        },
        "allocations": {
            "body_runtime_bytes": body_count * BODY_RUNTIME_STRIDE,
            "joint_runtime_bytes": constraints["runtime_arrays"]["JOINT"]["bytes"],
            "hinge_runtime_bytes": constraints["runtime_arrays"]["HINGE"]["bytes"],
            "bar_runtime_bytes": constraints["runtime_arrays"]["BAR"]["bytes"],
            "matrix_bytes": matrix_bytes,
            "row_pointer_bytes": row_pointer_bytes,
            "compact_graph_bytes": compact_graph_bytes,
            "per_body": per_body,
        },
        "construction_order": [
            "FUN_007b3670: lower BODY records into 0x170-byte runtime records",
            "FUN_007b3150: materialize JOINT/HINGE/BAR runtime records and endpoint links",
            "FUN_007b1b60: assign solver scalar widths/order",
            "FUN_007b3820: allocate matrix/row storage and initialize row pointers",
            "FUN_007b3820: probe source-visible physics provider slots",
            "provider or generic fallback: finalize backend storage",
        ],
        "body": body,
        "constraints": constraints,
        "backend_boundary": {
            "provider_selector": "FUN_007d2e70",
            "acceptance_vtable_offset": "+0x14",
            "generic_fallback": "FUN_007b1360",
            "sdk_object_classes": "unresolved",
            "physical_units": "unresolved",
        },
        "errors": list(dict.fromkeys(errors)),
        "evidence": {
            "body_constructor": "FUN_007b3670",
            "constraint_materializer": "FUN_007b3150",
            "solver_order": "FUN_007b1b60",
            "matrix_constructor": "FUN_007b3820",
            "source_file": ".\\Source\\System\\SDF.cpp / related retail decompilation boundary",
        },
        "limitations": [
            "This is a pre-PhysX construction IR, not an implementation of the PhysX SDK.",
            "Provider virtual methods are represented by offsets and observed allocation effects only.",
            "No physical unit conversion is inferred from raw asset fields.",
        ],
    }


def validate_expected_shape(plan: Mapping[str, Any], *, body_count: int, joint_hinge_count: int, bar_count: int) -> dict[str, Any]:
    expected_joint = joint_hinge_count
    expected_hinge = joint_hinge_count
    expected_bar = bar_count
    expected_constraints = expected_joint + expected_hinge + expected_bar
    expected_scalars = expected_joint * 3 + expected_hinge * 2 + expected_bar
    errors: list[str] = []
    counts = plan.get("counts") or {}
    checks = {
        "bodies": (counts.get("bodies"), body_count),
        "joint": (counts.get("joint"), expected_joint),
        "hinge": (counts.get("hinge"), expected_hinge),
        "bar": (counts.get("bar"), expected_bar),
        "runtime_constraints": (counts.get("runtime_constraints"), expected_constraints),
        "solver_scalar_count": (counts.get("solver_scalar_count"), expected_scalars),
    }
    for field, (actual, expected) in checks.items():
        if actual != expected:
            errors.append(f"{field}:expected={expected}:actual={actual}")
    return {
        "ready": not errors,
        "errors": errors,
        "expected": {"bodies": body_count, "joint": expected_joint, "hinge": expected_hinge, "bar": expected_bar, "runtime_constraints": expected_constraints, "solver_scalar_count": expected_scalars},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SHIFT pre-PhysX construction IR from parsed SDF JSON.")
    parser.add_argument("input", type=Path, help="parse_sdf() JSON report")
    parser.add_argument("-o", "--output", type=Path, help="output JSON file")
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    plan = build_prephysx_construction_plan(report)
    payload = json.dumps(plan, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if plan["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
