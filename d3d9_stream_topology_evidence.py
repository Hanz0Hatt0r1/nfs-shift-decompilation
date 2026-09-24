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
GROUP_STRIDE = 0x10

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
                "*(int *)(local_28 + 0x44)",
                "*(int *)(*(int *)(local_28 + 0x44) + local_70 * 4)",
            ),
            function_start,
        ),
        "type_ordinal_array": _contains_all(
            text,
            (
                "*(int *)(local_28 + 0x3c)",
                "FUN_00853c20(*(int *)(*(int *)(local_28 + 0x3c) + local_70 * 4))",
            ),
            function_start,
        ),
        "usage_ordinal_array": _contains_all(
            text,
            (
                "*(int *)(local_28 + 0x40)",
                "FUN_00853c40((int)local_6c)",
            ),
            function_start,
        ),
        "vertex_data_buffer_array": _contains_all(
            text,
            (
                "*(int *)(local_28 + 0x48)",
                "*(int *)(*(int *)(local_28 + 0x48) + iVar12 * 4)",
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
                "*(ushort **)(*(int *)(local_28 + 0x44) + local_70 * 4)",
                "*(int *)((int)local_38 * 0x10 + 8 + *(int *)(iVar15 + 0x24))",
            ),
            function_start,
        ),
        "record_pointer_array": _contains_all(
            text,
            (
                "*(int *)(*(int *)((int)local_38 * 0x10 + 8 + *(int *)(iVar15 + 0x24)) + local_24 * 4)",
                "*(int *)(iVar15 + 0x1c) + iVar12",
            ),
            function_start,
        ),
        "count_increment": _contains_all(
            text,
            (
                "local_24 = local_24 + 1;",
                "*(int *)((int)local_38 * 0x10 + 4 + *(int *)(iVar15 + 0x24))",
            ),
            function_start,
        ),
        "byte_size_accumulation": _contains_all(
            text,
            (
                "local_40 = local_40 +",
                "DAT_00b8eef0",
            ),
            function_start,
        ),
        "usage_index_counter": _contains_all(
            text,
            (
                "if (local_6c == (ushort *)0x3)",
                "else if (local_6c == (ushort *)0x6)",
                "local_31 = local_31 + '\\x01';",
                "local_14._3_1_ + '\\x01'",
            ),
            function_start,
        ),
    }
    source_lines = {
        "function": text.count("\n", 0, function_start) + 1,
        "stream_group_index": _line_number(
            text,
            "*(ushort **)(*(int *)(local_28 + 0x44) + local_70 * 4)",
            function_start,
        ),
        "record_pointer_write": _line_number(
            text,
            "*(int *)(*(int *)((int)local_38 * 0x10 + 8 + *(int *)(iVar15 + 0x24)) + local_24 * 4) =",
            function_start,
        ),
        "stream_field_write": _line_number(
            text,
            "*(undefined2 *)(iVar12 + *(int *)(iVar15 + 0x1c)) = local_38._0_2_;",
            function_start,
        ),
        "type_field_write": _line_number(
            text,
            "*(char *)(*(int *)(iVar15 + 0x1c) + 4 + iVar12) = (char)uVar5;",
            function_start,
        ),
        "usage_field_write": _line_number(
            text,
            "*(char *)(*(int *)(iVar15 + 0x1c) + 6 + iVar12) = (char)uVar5;",
            function_start,
        ),
        "usage_index_field_write": _line_number(
            text,
            "*(char *)(iVar10 + 7 + iVar12) =",
            function_start,
        ),
        "byte_size_increment": _line_number(
            text,
            "local_40 = local_40 +",
            function_start,
        ),
        "vertex_buffer_read": _line_number(
            text,
            "*(int *)(*(int *)(local_28 + 0x48) + iVar12 * 4)",
            function_start,
        ),
    }


