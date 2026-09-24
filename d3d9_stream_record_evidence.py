"""Source-backed semantics of the 8-byte STREAM declaration records.

FUN_008587e0 builds a compact vertex-element record whose byte layout is
compatible with D3DVERTEXELEMENT9:
  +0x00: Stream (WORD), explicitly initialized to 0
  +0x02: Offset (WORD), the running byte offset
  +0x04: Type (BYTE), resolved from the Type ordinal table
  +0x05: Method (BYTE), explicitly initialized to 0
  +0x06: Usage (BYTE), resolved from the Usage ordinal table
  +0x07: UsageIndex (BYTE), read from the XML Channel attribute

This module records those writes from the recovered Ghidra C without assigning
MEB property ids to the records.
"""
from __future__ import annotations

from typing import Any


FORMAT = "SHIFT.D3D9StreamRecordEvidence/1"
FUNCTION = "FUN_008587e0"
RECORD_STRIDE = 8

FIELDS = {
    "stream": {
        "offset": 0,
        "width": 2,
        "basis": "*(undefined2 *)(record + 0) = 0",
    },
    "offset": {
        "offset": 2,
        "width": 2,
        "basis": "*(undefined2 *)(record + 2) = local_48",
    },
    "type": {
        "offset": 4,
        "width": 1,
        "basis": "FUN_00853c20(type_ordinal) -> *(char *)(record + 4)",
    },
    "method": {
        "offset": 5,
        "width": 1,
        "basis": "record + 5 is explicitly zeroed",
    },
    "usage": {
        "offset": 6,
        "width": 1,
        "basis": "FUN_00853c40(usage_ordinal) -> *(char *)(record + 6)",
    },
    "usage_index": {
        "offset": 7,
        "width": 1,
        "basis": "Channel attribute -> record + 7",
    },
}


OBSERVATIONS = {
    "record_array": "param_1 + 0x1c",
    "record_pointer_array": "*(int *)(*(int *)(param_1 + 0x24) + 8)",
    "record_stride": 8,
    "type_field_offset": 4,
    "usage_field_offset": 6,
    "usage_index_field_offset": 7,
}


def _contains_all(source: str, needles: tuple[str, ...]) -> bool:
    return all(needle in source for needle in needles)


def _line_number(source: str, needle: str, start: int = 0) -> int | None:
    offset = source.find(needle, start)
    if offset < 0:
        return None
    return source.count("\n", 0, offset) + 1


def analyze_d3d9_stream_record_semantics(source: str | bytes) -> dict[str, Any]:
    if isinstance(source, bytes):
        raw = source
        text = source.decode("utf-8", errors="replace")
    else:
        text = str(source)
        raw = text.encode("utf-8")

    function_start = text.find(f"uint __fastcall {FUNCTION}")
    if function_start < 0:
        return {
            "format": FORMAT,
            "function": FUNCTION,
            "status": "not-found",
            "source": {"kind": "shift-exe-c", "bytes": len(raw)},
            "record": {},
            "fields": [],
            "meb_property_mapping": {"status": "not-proven"},
        }

    markers = {
        "function_line": text.count("\n", 0, function_start) + 1,
        "stream_field": _contains_all(
            text,
            (
                "*(undefined2 *)(iVar7 + *(int *)(param_1 + 0x1c)) = 0;",
            ),
        ),
        "type_field": _contains_all(
            text,
            (
                "uVar9 = FUN_00853c20((int)local_18);",
                "*(char *)(iVar7 + 4 + *(int *)(param_1 + 0x1c)) = (char)uVar9;",
            ),
        ),
        "usage_field": _contains_all(
            text,
            (
                "uVar9 = FUN_00853c40(local_5c);",
                "*(char *)(iVar7 + 6 + *(int *)(param_1 + 0x1c)) = (char)uVar9;",
            ),
        ),
        "method_field": _contains_all(
            text,
            (
                "*(undefined1 *)(iVar7 + 5 + *(int *)(param_1 + 0x1c)) = 0;",
            ),
        ),
        "channel_field": _contains_all(
            text,
            (
                'FUN_0063d410(local_40,"Channel",&local_1c);',
                "*(undefined1 *)(iVar7 + 7 + *(int *)(param_1 + 0x1c)) = local_1c._0_1_;",
            ),
        ),
        "reserved_field": _contains_all(
            text,
            (
                "*(undefined1 *)(iVar7 + 5 + *(int *)(param_1 + 0x1c)) = 0;",
            ),
        ),
        "running_offset_field": _contains_all(
            text,
            (
                "*(undefined2 *)(iVar7 + 2 + *(int *)(param_1 + 0x1c)) = (undefined2)local_48;",
            ),
        ),
        "pointer_array_stride": _contains_all(
            text,
            (
                "*(int *)(*(int *)(*(int *)(param_1 + 0x24) + 8) + (int)local_10 * 4) =",
                "*(int *)(param_1 + 0x1c) + iVar7;",
            ),
        ),
    }

    type_line = _line_number(
        text,
        "*(char *)(iVar7 + 4 + *(int *)(param_1 + 0x1c)) = (char)uVar9;",
        function_start,
    )
    usage_line = _line_number(
        text,
        "*(char *)(iVar7 + 6 + *(int *)(param_1 + 0x1c)) = (char)uVar9;",
        function_start,
    )
    channel_line = _line_number(
        text,
        "*(undefined1 *)(iVar7 + 7 + *(int *)(param_1 + 0x1c)) = local_1c._0_1_;",
        function_start,
    )

    field_rows: list[dict[str, Any]] = []
    for name, spec in FIELDS.items():
        observed = {
            "stream": markers["stream_field"],
            "offset": markers["running_offset_field"],
            "type": markers["type_field"],
            "method": markers["method_field"],
            "usage": markers["usage_field"],
            "usage_index": markers["channel_field"],
        }[name]
        source_line = {
            "type_code": type_line,
            "usage_code": usage_line,
            "channel": channel_line,
            "reserved": _line_number(
                text,
                "*(undefined1 *)(iVar7 + 5 + *(int *)(param_1 + 0x1c)) = 0;",
                function_start,
            ),
            "running_offset": _line_number(
                text,
                "*(undefined2 *)(iVar7 + 2 + *(int *)(param_1 + 0x1c)) = (undefined2)local_48;",
                function_start,
            ),
        }[name]
        field_rows.append(
            {
                "name": name,
                "offset": spec["offset"],
                "width": spec["width"],
                "status": "observed" if observed else "not-found",
                "source_line": source_line,
                "basis": spec["basis"],
            }
        )

    all_core_observed = all(
        row["status"] == "observed"
        for row in field_rows
        if row["name"] in {"type_code", "usage_code", "channel", "reserved", "running_offset"}
    )

    return {
        "format": FORMAT,
        "function": FUNCTION,
        "status": "observed" if all_core_observed else "not-proven",
        "source": {
            "kind": "shift-exe-c",
            "bytes": len(raw),
            "line_count": len(text.splitlines()),
            "function_line": function_start,
        },
        "record": {
            "base": OBSERVATIONS["record_array"],
            "stride": RECORD_STRIDE,
            "pointer_array": OBSERVATIONS["record_pointer_array"],
            "pointer_array_stride": 4 if markers["pointer_array_stride"] else None,
            "field_offsets": {
                name: spec["offset"] for name, spec in FIELDS.items()
            },
            "status": "observed" if markers["pointer_array_stride"] else "not-proven",
        },
        "fields": field_rows,
        "semantic_links": {
            "d3dvertexelement9_shape": {
                "status": "observed" if all(
                    row["status"] == "observed"
                    for row in field_rows
                ) else "not-proven",
                "detail": "the recovered record contains the six D3DVERTEXELEMENT9-shaped fields Stream/Offset/Type/Method/Usage/UsageIndex in the documented 8-byte order",
            },
            "xml_type_to_record_type_code": {
                "status": "observed"
                if markers["type_field"]
                else "not-proven",
                "detail": "XML Type is searched through PTR_DAT_00b901d0 and the matched ordinal is passed to FUN_00853c20 before being stored at record + 4",
            },
            "xml_usage_to_record_usage_code": {
                "status": "observed"
                if markers["usage_field"]
                else "not-proven",
                "detail": "XML Usage is searched through the fixed usage-name table and the matched ordinal is passed to FUN_00853c40 before being stored at record + 6",
            },
            "xml_channel_to_record_usage_index": {
                "status": "observed"
                if markers["channel_field"]
                else "not-proven",
                "detail": "Channel is read directly from the XML STREAM entry and stored at record + 7",
            },
            "colour_usage_to_record_usage_code_6": {
                "status": "observed" if markers["usage_field"] and '"Colour"' in text else "not-proven",
                "detail": "Usage code 6 is the source-backed Colour branch from phase 80",
            },
        },
        "meb_property_mapping": {
            "status": "not-proven",
            "reason": "the recovered stream record contains no literal MEB property ids 460/461",
        },
    }


def analyze_d3d9_stream_record_semantics_file(path: str) -> dict[str, Any]:
    from pathlib import Path

    source_path = Path(path)
    report = analyze_d3d9_stream_record_semantics(source_path.read_bytes())
    report["source"]["path"] = str(source_path)
    return report
