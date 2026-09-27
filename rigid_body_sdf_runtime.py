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
        matches = list(re.finditer(r"(?<!\\s)([A-Za-z_][A-Za-z0-9_&]*)\\s*=", stripped))
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


def compile_sdf_runtime_topology(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    """Lower parsed SDF records into the proven FUN_007b3150 topology boundary.

    This does not create PhysX objects. It records body indices, section flags,
    endpoint references and the runtime record stride used for each allocation.
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

    constraints: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for record_index, record in enumerate(report.get("records") or []):
        section = str(record.get("section", "")).upper()
        if section not in {"JOINT", "HINGE", "BAR", "JOINT&HINGE"}:
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
            unresolved.append(f"record:{record_index}:posbody:{posbody}")
        if negbody_key and negbody_key not in body_index:
            unresolved.append(f"record:{record_index}:negbody:{negbody}")

        flags = {
            "joint": section in {"JOINT", "JOINT&HINGE"},
            "hinge": section in {"HINGE", "JOINT&HINGE"},
            "bar": section == "BAR",
        }
        flag_word = (
            (SDF_FLAG_JOINT if flags["joint"] else 0)
            | (SDF_FLAG_HINGE if flags["hinge"] else 0)
            | (SDF_FLAG_BAR if flags["bar"] else 0)
        )
        vectors = {}
        for key in ("axis", "neg", "pos"):
            value = values.get(key)
            if isinstance(value, list) and len(value) == 3:
                vectors[key] = [float(component) for component in value]
        if isinstance(values.get("pos"), str):
            vectors["pos_body_anchor_name"] = str(values["pos"])

        constraints.append({
            "record_index": record_index,
            "section": section,
            "flags": flags,
            "flag_word": flag_word,
            "posbody": posbody,
            "negbody": negbody,
            "posbody_index": body_index.get(posbody_key),
            "negbody_index": body_index.get(negbody_key),
            "vectors": vectors,
            "runtime_stride": 0xB8 if section == "BAR" else 0xA0,
            "body_pointer_slots": {
                "posbody": "+0x78",
                "negbody": "+0x80",
            },
            "source_constructor": "FUN_007b3150",
        })

    return {
        "format": "SHIFT.SDFRuntimeTopology/1",
        "version": 1,
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
            "posbody_runtime_slot": "+0x78",
            "negbody_runtime_slot": "+0x80",
            "bar_endpoint_vectors": ["+0x28", "+0x30", "+0x38", "+0x40", "+0x48", "+0x50"],
        },
        "limitations": [
            "PhysX object classes and SDK calls remain opaque.",
            "Anchor semantics are preserved as source vectors/names; no coordinate-system naming is inferred.",
        ],
    }



def describe_sdf_constraint_runtime_lowering(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    """Describe the source-backed FUN_007b3150 constraint materialization map.

    The returned contract names storage/call boundaries only; it deliberately
    does not assign PhysX SDK class names or physical-unit semantics.
    """
    section_specs = {
        "JOINT": {
            "flag_bit": SDF_FLAG_JOINT,
            "runtime_stride": 0xA0,
            "body_counter_offset": "+0x98",
            "source_value_fields": ["pos"],
            "source_descriptor_offsets": ["+0x28", "+0x30", "+0x38"],
            "runtime_vector_offsets": ["+0x88", "+0x90", "+0x98"],
            "sample_helper": "FUN_007ba8b0",
            "sample_stride": 0x40,
            "postload_helper": "FUN_007b2da0",
        },
        "HINGE": {
            "flag_bit": SDF_FLAG_HINGE,
            "runtime_stride": 0xA0,
            "body_counter_offset": "+0x9c",
            "source_value_fields": ["axis"],
            "source_descriptor_offsets": ["+0x58", "+0x60", "+0x68"],
            "runtime_vector_offsets": ["+0x88", "+0x90", "+0x98"],
            "sample_helper": "FUN_007ba900",
            "sample_stride": 0xA0,
            "postload_helper": "FUN_007b2de0",
        },
        "BAR": {
            "flag_bit": SDF_FLAG_BAR,
            "runtime_stride": 0xB8,
            "body_counter_offset": "+0xa0",
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
        "JOINT&HINGE": {
            "flag_bit": SDF_FLAG_JOINT | SDF_FLAG_HINGE,
            "runtime_stride": 0xA0,
            "body_counter_offset": ["+0x98", "+0x9c"],
            "source_value_fields": {
                "joint": ["+0x28", "+0x30", "+0x38"],
                "hinge": ["+0x58", "+0x60", "+0x68"],
            },
            "runtime_vector_offsets": ["+0x88", "+0x90", "+0x98"],
            "sample_helpers": ["FUN_007ba8b0", "FUN_007ba900"],
            "sample_strides": [0x40, 0xA0],
            "postload_helpers": ["FUN_007b2da0", "FUN_007b2de0"],
        },
    }

    rows: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for record_index, record in enumerate(report.get("records") or []):
        section = str(record.get("section", "")).upper()
        spec = section_specs.get(section)
        if spec is None:
            continue
        values = {
            str(entry.get("name")): entry.get("value")
            for entry in record.get("entries") or []
        }
        posbody = values.get("posbody")
        negbody = values.get("negbody")
        for field, body in (("posbody", posbody), ("negbody", negbody)):
            if body is None:
                unresolved.append(f"record:{record_index}:{section}:missing-{field}")
        flags = {
            "joint": bool(int(spec["flag_bit"]) & SDF_FLAG_JOINT),
            "hinge": bool(int(spec["flag_bit"]) & SDF_FLAG_HINGE),
            "bar": bool(int(spec["flag_bit"]) & SDF_FLAG_BAR),
        }
        rows.append({
            "record_index": record_index,
            "section": section,
            "name": values.get("name"),
            "posbody": posbody,
            "negbody": negbody,
            "flags": flags,
            "flag_word": spec["flag_bit"],
            "runtime_stride": spec["runtime_stride"],
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
                "helper": spec.get("sample_helper") or spec.get("sample_helpers"),
                "sample_stride": spec.get("sample_stride") or spec.get("sample_strides"),
            },
            "postload": {
                "helper": spec.get("postload_helper") or spec.get("postload_helpers"),
            },
        })

    return {
        "format": "SHIFT.SDFConstraintRuntimeLowering/1",
        "version": 1,
        "status": "ready" if not unresolved else "blocked",
        "ready": not unresolved,
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
            "BAR secondary vector source names are intentionally structural because the text loader does not establish gameplay names.",
            "Returned sample pointers remain opaque runtime allocations; only their proven strides/helpers are recorded.",
        ],
    }



def describe_sdf_pre_physx_build(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    """Expose the deterministic pre-PhysX allocation/build phases of FUN_007b3820."""
    topology = compile_sdf_runtime_topology(report)
    bodies = topology["body_count"]
    joints = sum(1 for row in topology["constraints"] if row["flags"]["joint"])
    hinges = sum(1 for row in topology["constraints"] if row["flags"]["hinge"])
    bars = sum(1 for row in topology["constraints"] if row["flags"]["bar"])
    return {
        "format": "SHIFT.SDFPrePhysXBuildRuntime/1",
        "version": 1,
        "status": "ready" if topology["ready"] else "blocked",
        "ready": topology["ready"],
        "counts": {
            "bodies": bodies,
            "joints": joints,
            "hinges": hinges,
            "bars": bars,
        },
        "allocations": {
            "per_joint_resolved_samples": joints * 2,
            "per_hinge_resolved_samples": hinges * 2,
            "per_bar_resolved_samples": bars * 2,
            "body_index_matrix_elements": bodies * bodies,
            "body_index_matrix_bytes": bodies * bodies * 8,
            "body_index_vector_elements": bodies,
            "body_index_vector_bytes": bodies * 4,
            "body_runtime_stride": 0x170,
            "joint_runtime_stride": 0xA0,
            "hinge_runtime_stride": 0xA0,
            "bar_runtime_stride": 0xB8,
        },
        "stages": [
            {"function": "FUN_007ba4e0", "purpose": "allocate/reset per-constraint sampled arrays"},
            {"function": "FUN_007b1b60", "purpose": "derive aggregate body/node count"},
            {"function": "FUN_007b2010", "purpose": "prepare connectivity matrix and index base"},
            {"function": "FUN_007ba8b0", "purpose": "joint endpoint sample generation"},
            {"function": "FUN_007ba900", "purpose": "hinge endpoint sample generation"},
            {"function": "FUN_007ba990", "purpose": "bar endpoint sample generation"},
            {"function": "FUN_007b2da0/FUN_007b2de0/FUN_007b2f70", "purpose": "copy generated sample transforms into runtime records"},
            {"function": "FUN_007b1360", "purpose": "final body-node connectivity setup"},
        ],
        "topology": topology,
        "evidence": {
            "source_function": "FUN_007b3820",
            "body_matrix_element_size": 8,
            "body_index_element_size": 4,
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
