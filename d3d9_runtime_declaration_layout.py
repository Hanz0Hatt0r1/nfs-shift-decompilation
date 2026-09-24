"""Validate runtime D3D9 declaration offsets against the recovered Type sizes.

The validator consumes either SHIFT.D3D9DeclarationInstanceEvidence/1 or
SHIFT.D3D9MemoryDeclarationEvidence/1 and checks the source-backed invariant
used by the recovered STREAM builder: within each Stream, declaration Offset
advances by the packed byte size of the previous Type.

This is a runtime consistency check, not a MEB property mapper.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Any, Mapping

from d3d9_type_profile import TYPE_PROFILE, TYPE_UNUSED

FORMAT = "SHIFT.D3D9RuntimeDeclarationLayoutEvidence/1"
RECORD_STRIDE = 8


def _unwrap_declaration(report: Mapping[str, Any]) -> tuple[Mapping[str, Any], str]:
    if report.get("format") == "SHIFT.D3D9MemoryDeclarationEvidence/1":
        nested = report.get("declaration_instance")
        if not isinstance(nested, Mapping):
            return {}, "invalid-wrapper"
        return nested, "memory-wrapper"
    return report, "direct-instance"


def validate_d3d9_runtime_declaration_layout(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    declaration, input_kind = _unwrap_declaration(report)
    declaration_status = declaration.get("status")
    records = declaration.get("records", [])
    validation = declaration.get("validation", {})
    shape_status = (
        declaration.get("semantic_links", {})
        .get("d3dvertexelement9_shape", {})
        .get("status")
        if isinstance(declaration.get("semantic_links"), Mapping)
        else None
    )
    if not isinstance(records, list) or not isinstance(validation, Mapping):
        return {
            "format": FORMAT,
            "status": "not-proven",
            "input_kind": input_kind,
            "error": "declaration instance shape is unavailable",
            "meb_property_mapping": {"status": "not-proven"},
        }

    end_index = validation.get("end_sentinel_index")
    declaration_records = [
        row for row in records
        if isinstance(row, Mapping)
        and isinstance(row.get("index"), int)
        and (end_index is None or row["index"] <= end_index)
        and not (
            row.get("index") == end_index
            and row.get("stream") == 0xFFFF
            and row.get("offset") == 0
            and row.get("type") == TYPE_UNUSED
            and row.get("method") == 0
            and row.get("usage") == 0
            and row.get("usage_index") == 0
        )
    ]

    stream_states: "OrderedDict[int, dict[str, Any]]" = OrderedDict()
    issues: list[dict[str, Any]] = []

    for row in declaration_records:
        stream = row.get("stream")
        element_offset = row.get("offset")
        type_code = row.get("type")
        index = row.get("index")
        if not all(isinstance(value, int) for value in (stream, element_offset, type_code, index)):
            issues.append({
                "index": index,
                "reason": "non-integer declaration field",
            })
            continue
        profile = TYPE_PROFILE.get(type_code)
        if profile is None:
            issues.append({
                "index": index,
                "reason": "unknown Type code",
                "type": type_code,
            })
            continue
        type_name, component_count, element_size = profile
        state = stream_states.setdefault(
            stream,
            {
                "stream": stream,
                "element_count": 0,
                "expected_next_offset": 0,
                "byte_size": 0,
                "type_codes": [],
                "records": [],
            },
        )
        expected_offset = state["expected_next_offset"]
        offset_match = element_offset == expected_offset
        record = {
            "index": index,
            "stream": stream,
            "offset": element_offset,
            "type": type_code,
            "type_name": type_name,
            "source_components": component_count,
            "element_size_bytes": element_size,
            "expected_offset": expected_offset,
            "offset_match": offset_match,
            "end_offset": element_offset + element_size,
        }
        state["records"].append(record)
        state["element_count"] += 1
        state["type_codes"].append(type_code)
        state["byte_size"] += element_size
        state["expected_next_offset"] = expected_offset + element_size
        if not offset_match:
            issues.append({
                "index": index,
                "reason": "offset does not follow recovered Type byte size",
                "stream": stream,
                "observed_offset": element_offset,
                "expected_offset": expected_offset,
                "type": type_code,
                "element_size_bytes": element_size,
            })

    stream_summaries = []
    for state in stream_states.values():
        stream_summaries.append({
            "stream": state["stream"],
            "element_count": state["element_count"],
            "byte_size": state["byte_size"],
            "final_offset": state["expected_next_offset"],
            "type_codes": state["type_codes"],
            "contiguous_offsets": all(row["offset_match"] for row in state["records"]),
        })

    if declaration_status != "match" or shape_status != "observed":
        status = "not-proven"
    elif end_index is None:
        status = "partial"
    elif issues:
        status = "mismatch"
    else:
        status = "match"

    return {
        "format": FORMAT,
        "status": status,
        "input_kind": input_kind,
        "record_stride": RECORD_STRIDE,
        "declaration": {
            "status": declaration_status,
            "end_sentinel_index": end_index,
            "end_sentinel_status": (
                "observed" if end_index is not None else "not-present"
            ),
            "records_considered": len(declaration_records),
        },
        "stream_summaries": stream_summaries,
        "issues": issues,
        "semantic_links": {
            "offsets_follow_type_sizes": {
                "status": (
                    "observed"
                    if status == "match"
                    else ("mismatch" if status == "mismatch" else "not-proven")
                ),
                "detail": "each Stream starts at Offset 0 and advances by the recovered packed size for its preceding Type",
            },
            "type_code_to_profile": {
                "status": (
                    "observed"
                    if not any(issue.get("reason") == "unknown Type code" for issue in issues)
                    else "mismatch"
                ),
            },
        },
        "meb_property_mapping": {
            "status": "not-proven",
            "detail": "Runtime Offset/Type consistency does not establish MEB 460/461 linkage.",
        },
    }


def validate_d3d9_runtime_declaration_layout_file(path: str) -> dict[str, Any]:
    import json
    from pathlib import Path

    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("expected JSON object")
    return validate_d3d9_runtime_declaration_layout(value)
