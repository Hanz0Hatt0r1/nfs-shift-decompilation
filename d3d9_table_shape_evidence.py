"""Shape evidence for the recovered D3D9 primitive-type lookup tables.

This module records what the exported Ghidra C can prove about table bounds and
indexing. It does not reconstruct opaque initializer bytes.
"""
from __future__ import annotations

import re
from typing import Any


FORMAT = "SHIFT.D3D9TypeTableShapeEvidence/1"

TARGETS = {
    "DAT_00b90088": 0x00B90088,
    "DAT_00b900d8": 0x00B900D8,
    "DAT_00b9011c": 0x00B9011C,
    "DAT_00b90140": 0x00B90140,
    "DAT_00b90178": 0x00B90178,
    "PTR_DAT_00b901d0": 0x00B901D0,
}

TARGET_ORDER = tuple(sorted(TARGETS.items(), key=lambda item: item[1]))


def _line_number(source: str, needle: str, start: int = 0) -> int | None:
    offset = source.find(needle, start)
    if offset < 0:
        return None
    return source.count("\n", 0, offset) + 1


def _line_numbers(source: str, needle: str) -> list[int]:
    return [
        source.count("\n", 0, match.start()) + 1
        for match in re.finditer(re.escape(needle), source)
    ]


def analyze_d3d9_table_shapes(source: str | bytes) -> dict[str, Any]:
    if isinstance(source, bytes):
        raw = source
        text = source.decode("utf-8", errors="replace")
    else:
        text = str(source)
        raw = text.encode("utf-8")

    declarations: dict[str, dict[str, Any]] = {}
    for name, address in TARGET_ORDER:
        marker = re.compile(
            rf"(?m)^.*\b{re.escape(name)}\s*;"
        )
        match = marker.search(text)
        declarations[name] = {
            "address": f"0x{address:08x}",
            "declared": bool(match),
            "source_line": text.count("\n", 0, match.start()) + 1 if match else None,
        }

    global_spans: list[dict[str, Any]] = []
    for (left_name, left_addr), (right_name, right_addr) in zip(
        TARGET_ORDER, TARGET_ORDER[1:]
    ):
        span = right_addr - left_addr
        global_spans.append(
            {
                "from": left_name,
                "to_next_symbol": right_name,
                "byte_span": span,
                "dword_slots_if_contiguous": span // 4 if span % 4 == 0 else None,
                "status": "layout-hint" if span > 0 and span % 4 == 0 else "not-proven",
            }
        )

    type_getter = _line_numbers(
        text,
        "return *(undefined4 *)(&DAT_00b90088 + param_1 * 4);",
    )
    size_getter = _line_numbers(
        text,
        "return *(undefined4 *)(&DAT_00b900d8 + param_1 * 4);",
    )
    usage_getter = _line_numbers(
        text,
        "return *(undefined4 *)(&DAT_00b9011c + param_1 * 4);",
    )
    usage_index_getter = _line_numbers(
        text,
        "return *(undefined4 *)(&DAT_00b90140 + param_1 * 4);",
    )
    channel_getter = _line_numbers(
        text,
        "return *(undefined4 *)(&DAT_00b90178 + param_1 * 4);",
    )

    xml_type_lookup = _line_numbers(
        text,
        "pbVar17 = (&PTR_DAT_00b901d0)[(int)local_18];",
    )
    xml_type_loop_limit = _line_numbers(
        text,
        "} while (local_18 < (AptCIH *)0x11);",
    )
    xml_usage_loop_limit = _line_numbers(
        text,
        "} while (local_5c < 9);",
    )
    xml_type_to_code = _line_numbers(
        text,
        "uVar9 = FUN_00853c20((int)local_18);",
    )

    type_table_span = next(
        (
            item["dword_slots_if_contiguous"]
            for item in global_spans
            if item["from"] == "DAT_00b90088"
            and item["to_next_symbol"] == "DAT_00b900d8"
        ),
        None,
    )
    size_table_span = next(
        (
            item["dword_slots_if_contiguous"]
            for item in global_spans
            if item["from"] == "DAT_00b900d8"
            and item["to_next_symbol"] == "DAT_00b9011c"
        ),
        None,
    )

    return {
        "format": FORMAT,
        "source": {
            "kind": "shift-exe-c",
            "bytes": len(raw),
            "line_count": len(text.splitlines()),
        },
        "tables": declarations,
        "adjacent_global_spans": global_spans,
        "indexing": {
            "type_table": {
                "getter": "FUN_00853c20",
                "source_lines": type_getter,
                "byte_stride": 4,
                "layout_hint_dword_slots": type_table_span,
            },
            "size_table": {
                "getter": "FUN_00853c30",
                "source_lines": size_getter,
                "byte_stride": 4,
                "layout_hint_dword_slots": size_table_span,
            },
            "usage_table": {
                "getter": "FUN_00853c40",
                "source_lines": usage_getter,
                "byte_stride": 4,
            },
            "usage_index_table": {
                "getter": "FUN_00853c50",
                "source_lines": usage_index_getter,
                "byte_stride": 4,
            },
            "channel_table": {
                "getter": "FUN_00853c60",
                "source_lines": channel_getter,
                "byte_stride": 4,
            },
        },
        "xml_stream": {
            "type_pointer_table_lookup_lines": xml_type_lookup,
            "type_ordinal_limit_lines": xml_type_loop_limit,
            "type_ordinal_exclusive_limit": 0x11 if xml_type_loop_limit else None,
            "usage_limit_lines": xml_usage_loop_limit,
            "usage_exclusive_limit": 9 if xml_usage_loop_limit else None,
            "type_ordinal_to_code_lines": xml_type_to_code,
            "status": (
                "observed"
                if xml_type_lookup and xml_type_loop_limit and xml_type_to_code
                else "not-proven"
            ),
        },
        "conclusions": {
            "type_code_switch_and_xml_ordinal_domain": {
                "status": "observed" if xml_type_loop_limit else "not-proven",
                "detail": "XML Type names are searched across exactly 17 ordinals before the selected ordinal is passed to FUN_00853c20",
            },
            "type_table_initializer_bytes": {
                "status": "opaque",
                "detail": "global DAT_00b90088 is declared without initializer bytes in the exported C; only indexed access and symbol-address layout are recoverable",
            },
            "meb_460_461_mapping": {
                "status": "not-proven",
                "detail": "no direct MEB property-to-type-table ordinal linkage is exposed by the recovered C",
            },
        },
    }
