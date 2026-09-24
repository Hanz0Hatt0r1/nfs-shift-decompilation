"""Source-backed STREAM grouping topology from FUN_00854e70.

The recovered loader receives per-element arrays for Stream, Type, Usage and
Channel, groups declaration records by Stream id, and maintains a per-stream
record pointer array plus a byte-size accumulator.

This module intentionally does not map MEB property ids to those arrays.
"""
from __future__ import annotations

from typing import Any


FORMAT = "SHIFT.D3D9StreamTopologyEvidence/1"
FUNCTION = "FUN_00854e70"
GROUP_STRIDE = 0x14

GROUP_FIELDS = {
    "stream_id": {"group_offset": 0, "width": 4},
    "element_count": {"group_offset": 4, "width": 4},
    "byte_size": {"group_offset": 8, "width": 4},
    "resource_ref": {"group_offset": 0x0C, "width": 4},
}


def _line_number(source: str, needle: str, start: int = 0) -> int | None:
    offset = source.find(needle, start)
    if offset < 0:
        return None
    return source.count("\n", 0, offset) + 1


def _contains_all(source: str, needles: tuple[str, ...], start: int = 0) -> bool:
    return all(source.find(needle, start) >= 0 for needle in needles)


def analyze_d3d9_stream_topology(source: str | bytes) -> dict[str, Any]:
    if isinstance(source, bytes):
        raw = source
        text = source.decode("utf-8", errors="replace")
    else:
        text = str(source)
        raw = text.encode("utf-8")

    function_start = text.find(f"undefined4 __fastcall {FUNCTION}")
    if function_start < 0:
        return {
            "format": FORMAT,
            "function": FUNCTION,
            "status": "not-found",
            "source": {"kind": "shift-exe-c", "bytes": len(raw)},
            "inputs": {},
            "grouping": {},
            "meb_property_mapping": {"status": "not-proven"},
        }

    inputs = {
        "stream_array": _contains_all(
            text,
            (
                "*(int *)(uVar3 + 0x6c)",
                "*(int *)(uVar3 + 0x6c) + local_8 * 4",
            ),
            function_start,
        ),
        "type_ordinal_array": _contains_all(
            text,
            (
                "*(int *)(uVar3 + 0x70)",
                "FUN_00853c20(*(int *)(*(int *)(uVar3 + 0x70) + local_8 * 4))",
            ),
            function_start,
        ),
        "usage_ordinal_array": _contains_all(
            text,
            (
                "*(int *)(uVar3 + 0x74)",
                "FUN_00853c40(*(int *)(*(int *)(uVar3 + 0x74) + uVar11 * 4))",
            ),
            function_start,
        ),
        "channel_array": _contains_all(
            text,
            (
                "*(int *)(uVar3 + 0x78)",
                "*(undefined1 *)(extraout_EDX_01 + 7 + *(int *)((int)this + 0x1c))",
            ),
            function_start,
        ),
    }

    grouping = {
        "group_array_base": "this + 0x24",
        "group_stride": GROUP_STRIDE,
        "stream_to_group_index": _contains_all(
            text,
            (
                "iVar1 = *(int *)(*(int *)(uVar3 + 0x6c) + local_8 * 4) * 0x14;",
                "iVar9 = iVar1 + *(int *)((int)this + 0x24);",
            ),
            function_start,
        ),
        "record_pointer_array": _contains_all(
            text,
            (
                "*(int *)(*(int *)(iVar9 + 8) + *(int *)(iVar9 + 4) * 4) =",
                "*(int *)((int)this + 0x1c) + iVar8;",
            ),
            function_start,
        ),
        "count_increment": _contains_all(
            text,
            (
                "piVar7 = (int *)(iVar1 + 4 + *(int *)((int)this + 0x24));",
                "*piVar7 = *piVar7 + 1;",
            ),
            function_start,
        ),
        "byte_size_accumulation": _contains_all(
            text,
            (
                "*piVar7 = *piVar7 + *(int *)(&DAT_00b8eef0 +",
                "uint)(byte)extraout_EDX_01[extraout",
            ),
            function_start,
        ),
    }

    source_lines = {
        "function": text.count("\n", 0, function_start) + 1,
        "stream_group_index": _line_number(
            text,
            "iVar1 = *(int *)(*(int *)(uVar3 + 0x6c) + local_8 * 4) * 0x14;",
            function_start,
        ),
        "record_pointer_write": _line_number(
            text,
            "*(int *)(*(int *)(iVar9 + 8) + *(int *)(iVar9 + 4) * 4) = *(int *)((int)this + 0x1c) + iVar8;",
            function_start,
        ),
        "stream_field_write": _line_number(
            text,
            "*(undefined2 *)(iVar8 + *(int *)((int)this + 0x1c)) =",
            function_start,
        ),
        "type_field_write": _line_number(
            text,
            "*(char *)(extraout_EDX_00 + 4 + *(int *)((int)this + 0x1c)) = (char)uVar5;",
            function_start,
        ),
        "usage_field_write": _line_number(
            text,
            "*(char *)(extraout_EDX_01 + 6 + *(int *)((int)this + 0x1c)) = (char)uVar5;",
            function_start,
        ),
        "channel_field_write": _line_number(
            text,
            "*(undefined1 *)(extraout_EDX_01 + 7 + *(int *)((int)this + 0x1c)) =",
            function_start,
        ),
        "byte_size_increment": _line_number(
            text,
            "*piVar7 = *piVar7 + *(int *)(&DAT_00b8eef0 +",
            function_start,
        ),
    }

    input_status = "observed" if all(inputs.values()) else "not-proven"
    grouping_status = "observed" if all(
        value for key, value in grouping.items()
        if key != "group_stride"
    ) else "not-proven"

    return {
        "format": FORMAT,
        "function": FUNCTION,
        "status": "observed" if input_status == "observed" and grouping_status == "observed" else "not-proven",
        "source": {
            "kind": "shift-exe-c",
            "bytes": len(raw),
            "line_count": len(text.splitlines()),
            "function_line": source_lines["function"],
        },
        "inputs": {
            "stream_array": {
                "object_offset": "0x6c",
                "element_width": 4,
                "status": "observed" if inputs["stream_array"] else "not-proven",
            },
            "type_ordinal_array": {
                "object_offset": "0x70",
                "element_width": 4,
                "status": "observed" if inputs["type_ordinal_array"] else "not-proven",
            },
            "usage_ordinal_array": {
                "object_offset": "0x74",
                "element_width": 4,
                "status": "observed" if inputs["usage_ordinal_array"] else "not-proven",
            },
            "channel_array": {
                "object_offset": "0x78",
                "element_width": 4,
                "value_width": 1,
                "status": "observed" if inputs["channel_array"] else "not-proven",
            },
        },
        "grouping": {
            **GROUP_FIELDS,
            "group_array_base": grouping["group_array_base"],
            "group_stride": GROUP_STRIDE,
            "stream_to_group_index": "observed" if grouping["stream_to_group_index"] else "not-proven",
            "record_pointer_array": "observed" if grouping["record_pointer_array"] else "not-proven",
            "count_increment": "observed" if grouping["count_increment"] else "not-proven",
            "byte_size_accumulation": "observed" if grouping["byte_size_accumulation"] else "not-proven",
            "status": grouping_status,
        },
        "semantic_links": {
            "stream_id_to_group": {
                "status": "observed" if grouping["stream_to_group_index"] else "not-proven",
                "detail": "the Stream value from the per-element input array selects a 0x14-byte group object",
            },
            "group_to_record_list": {
                "status": "observed" if grouping["record_pointer_array"] else "not-proven",
                "detail": "each group exposes an 8-byte-record pointer array at group + 8, indexed by the group's current element count",
            },
            "type_to_group_byte_size": {
                "status": "observed" if grouping["byte_size_accumulation"] else "not-proven",
                "detail": "each record's Type byte indexes DAT_00b8eef0 and its size is added to the group's running byte-size accumulator",
            },
        },
        "source_lines": source_lines,
        "meb_property_mapping": {
            "status": "not-proven",
            "reason": "the recovered constructor carries ordinal arrays and channel data into declaration records but contains no literal MEB property ids 460/461",
        },
    }


def analyze_d3d9_stream_topology_file(path: str) -> dict[str, Any]:
    from pathlib import Path

    source_path = Path(path)
    report = analyze_d3d9_stream_topology(source_path.read_bytes())
    report["source"]["path"] = str(source_path)
    return report
