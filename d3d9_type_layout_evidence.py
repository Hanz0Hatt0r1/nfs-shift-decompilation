"""Evidence-backed semantics for D3D9 Type -> byte-size/component-count tables.

The recovered renderer indexes DAT_00b8eef0 by the Type byte at declaration
record +4 when calculating byte offsets, allocations and copies. It indexes
DAT_00b8ef38 by the same Type byte when deriving component counts for vertex
data. The exported C does not contain the table initializer bytes, so this
module reports the indexing semantics and address-span layout without
inventing numeric contents.
"""
from __future__ import annotations

import re
from typing import Any


FORMAT = "SHIFT.D3D9TypeLayoutTableEvidence/1"

TYPE_SIZE_TABLE = 0x00B8EEF0
TYPE_COMPONENT_TABLE = 0x00B8EF38
TYPE_COUNT_WITH_SENTINEL = 18
TYPE_SENTINEL = 0x11
TYPE_THIRD_ENTRY_ADDRESS = TYPE_SIZE_TABLE + 3 * 4


def _line_number(source: str, needle: str, start: int = 0) -> int | None:
    offset = source.find(needle, start)
    if offset < 0:
        return None
    return source.count("\n", 0, offset) + 1


def _contains_all(source: str, needles: tuple[str, ...]) -> bool:
    return all(needle in source for needle in needles)


def analyze_d3d9_type_layout_tables(source: str | bytes) -> dict[str, Any]:
    if isinstance(source, bytes):
        raw = source
        text = source.decode("utf-8", errors="replace")
    else:
        text = str(source)
        raw = text.encode("utf-8")

    size_base_decl = bool(re.search(r"(?m)^undefined DAT_00b8eef0;", text))
    size_third_entry_decl = bool(re.search(r"(?m)^undefined DAT_00b8eefc;", text))
    component_base_decl = bool(re.search(r"(?m)^undefined DAT_00b8ef38;", text))

    size_index_access = "(&DAT_00b8eef0 +" in text
    component_index_access = "(&DAT_00b8ef38 +" in text

    source_refs = {
        "type_size_getter": _line_number(
            text,
            "(&DAT_00b8eef0 +",
            text.find("undefined4 __fastcall FUN_00853d50"),
        ),
        "type_size_offset_accumulation": _line_number(
            text,
            "local_48 = local_48 +",
            text.find("undefined4 __fastcall FUN_00854e70"),
        ),
        "type_component_use": _line_number(
            text,
            "(&DAT_00b8ef38 +",
            text.find("undefined4 __fastcall FUN_00854e70"),
        ),
        "synthetic_type3_write": _line_number(
            text,
            "*puVar6 = 3;",
            text.find("void __fastcall FUN_00854040"),
        ),
        "synthetic_type3_size_increment": _line_number(
            text,
            "iVar9 = iVar9 + _DAT_00b8eefc;",
            text.find("void __fastcall FUN_00854040"),
        ),
        "sentinel_type_17": _line_number(
            text,
            "*(undefined1 *)(*(int *)(local_48 + 0x1c) + 4 + *(int *)(local_48 + 0x14) * 8) = 0x11;",
            text.find("undefined4 __fastcall FUN_00854e70"),
        ),
    }

    size_table_span = TYPE_COMPONENT_TABLE - TYPE_SIZE_TABLE
    size_table_slot_hint = size_table_span // 4 if size_table_span % 4 == 0 else None

    semantic_markers = {
        "record_type_to_size": _contains_all(
            text,
            (
                "*(byte *)(*(int *)(*(int *)(param_2 * 0x10 + 8 + *(int *)(param_1 + 0x24)) +",
                "(&DAT_00b8eef0 +",
            ),
        ),
        "record_type_to_size_runtime": _contains_all(
            text,
            (
                "*(byte *)(*(int *)(iVar15 + 0x1c) + 4 + iVar12)",
                "DAT_00b8eef0",
            ),
        ),
        "record_type_to_components": _contains_all(
            text,
            (
                "*(byte *)(*(int *)(iVar15 + 0x1c) + 4 + iVar12)",
                "DAT_00b8ef38",
            ),
        ),
        "type3_entry_anchor": _contains_all(
            text,
            (
                "*puVar6 = 3;",
                "iVar9 = iVar9 + _DAT_00b8eefc;",
            ),
        ),
    }

    sentinel_written = bool(
        re.search(
            r"\+ 4 \+ [^)]* \* 8\) = 0x11;",
            text,
        )
    )

    return {
        "format": FORMAT,
        "source": {
            "kind": "shift-exe-c",
            "bytes": len(raw),
            "line_count": len(text.splitlines()),
        },
        "tables": {
            "type_size": {
                "address": f"0x{TYPE_SIZE_TABLE:08x}",
                "declared": size_base_decl,
                "third_entry_address": f"0x{TYPE_THIRD_ENTRY_ADDRESS:08x}",
                "third_entry_symbol": "DAT_00b8eefc",
                "third_entry_declared": size_third_entry_decl,
                "source_indexed": size_index_access,
                "entry_width": 4,
                "layout_hint_slots_before_component_table": size_table_slot_hint,
                "initializer_status": "opaque",
            },
            "type_component_count": {
                "address": f"0x{TYPE_COMPONENT_TABLE:08x}",
                "declared": component_base_decl,
                "source_indexed": component_index_access,
                "entry_width": 4,
                "layout_hint_slots": TYPE_COUNT_WITH_SENTINEL,
                "initializer_status": "opaque",
            },
        },
        "type_domain": {
            "observed_conversion_cases": list(range(17)),
            "sentinel_type_code": TYPE_SENTINEL,
            "sentinel_write_observed": sentinel_written,
            "entry_count_inferred_from_span": TYPE_COUNT_WITH_SENTINEL,
            "status": "observed" if sentinel_written else "not-proven",
        },
        "semantics": {
            "type_code_to_byte_size": {
                "status": "observed"
                if semantic_markers["record_type_to_size"]
                and semantic_markers["record_type_to_size_runtime"]
                else "not-proven",
                "detail": "the declaration Type byte at record +4 indexes DAT_00b8eef0 and the returned DWORD is added to running byte offsets / used for buffer copy sizes",
            },
            "type_code_to_component_count": {
                "status": "observed" if semantic_markers["record_type_to_components"] else "not-proven",
                "detail": "the same declaration Type byte indexes DAT_00b8ef38; the returned DWORD is used as the number of source components",
            },
            "type3_size_entry": {
                "status": "observed"
                if semantic_markers["type3_entry_anchor"]
                else "not-proven",
                "detail": "synthetic declaration generation writes Type=3 and advances its Offset by DAT_00b8eefc, which is the Type-3 element inside the base size table",
            },
        },
        "source_lines": source_refs,
        "meb_property_mapping": {
            "status": "not-proven",
            "reason": "these runtime tables are indexed by declaration Type and contain opaque initializer bytes; the recovered C still exposes no direct MEB property 460/461 mapping",
        },
    }


def analyze_d3d9_type_layout_tables_file(path: str) -> dict[str, Any]:
    from pathlib import Path

    source_path = Path(path)
    report = analyze_d3d9_type_layout_tables(source_path.read_bytes())
    report["source"]["path"] = str(source_path)
    return report
