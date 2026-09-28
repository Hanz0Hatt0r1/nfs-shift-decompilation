"""Evidence-backed behavior of the recovered D3D9 declaration canonicalizer.

FUN_00830f80 interns/canonicalizes an array of 8-byte declaration records.
The comparison loop examines the two WORD fields and all four trailing BYTE
fields, establishing that the whole 8-byte record participates in identity.
"""
from __future__ import annotations

from typing import Any


FORMAT = "SHIFT.D3D9DeclarationCanonicalizerEvidence/1"
FUNCTION = "FUN_00830f80"
RECORD_STRIDE = 8

COMPARISON_MARKERS = {
    "stream_word": "puVar7[-2] != *puVar2",
    "offset_word": "puVar7[-1] != puVar2[1]",
    "type_byte": "(char)*puVar7 != (char)puVar2[2]",
    "method_byte": "*(char *)((int)puVar7 + 1) != (char)puVar2[5]",
    "usage_byte": "(char)puVar7[1] != (char)puVar2[3]",
    "usage_index_byte": "*(char *)((int)puVar7 + 3) != (char)puVar2[7]",
    "record_stride": "uVar1 = uVar1 * 8 + 8",
    "record_copy": "_memcpy(puVar6,param_1,uVar1)",
}


FIELDS = {
    "stream": {"offset": 0, "width": 2, "source_compare": COMPARISON_MARKERS["stream_word"]},
    "offset": {"offset": 2, "width": 2, "source_compare": COMPARISON_MARKERS["offset_word"]},
    "type": {"offset": 4, "width": 1, "source_compare": COMPARISON_MARKERS["type_byte"]},
    "method": {"offset": 5, "width": 1, "source_compare": COMPARISON_MARKERS["method_byte"]},
    "usage": {"offset": 6, "width": 1, "source_compare": COMPARISON_MARKERS["usage_byte"]},
    "usage_index": {"offset": 7, "width": 1, "source_compare": COMPARISON_MARKERS["usage_index_byte"]},
}


def _line_number(source: str, needle: str, start: int = 0) -> int | None:
    offset = source.find(needle, start)
    if offset < 0:
        return None
    return source.count("\n", 0, offset) + 1


def analyze_d3d9_declaration_canonicalizer(source: str | bytes) -> dict[str, Any]:
    if isinstance(source, bytes):
        raw = source
        text = source.decode("utf-8", errors="replace")
    else:
        text = str(source)
        raw = text.encode("utf-8")

    function_start = text.find(f"ushort * __fastcall {FUNCTION}")
    if function_start < 0:
        return {
            "format": FORMAT,
            "function": FUNCTION,
            "status": "not-found",
            "source": {"kind": "shift-exe-c", "bytes": len(raw)},
            "fields": [],
            "canonicalization": {},
            "meb_property_mapping": {"status": "not-proven"},
        }

    rows: list[dict[str, Any]] = []
    for name, spec in FIELDS.items():
        marker = spec["source_compare"]
        present = marker in text
        rows.append(
            {
                "name": name,
                "offset": spec["offset"],
                "width": spec["width"],
                "status": "observed" if present else "not-found",
                "source_line": _line_number(text, marker, function_start),
                "comparison_marker": marker,
            }
        )

    stride_observed = COMPARISON_MARKERS["record_stride"] in text
    copy_observed = COMPARISON_MARKERS["record_copy"] in text
    comparison_count = sum(row["status"] == "observed" for row in rows)

    return {
        "format": FORMAT,
        "function": FUNCTION,
        "status": "observed" if comparison_count == len(FIELDS) else "not-proven",
        "source": {
            "kind": "shift-exe-c",
            "bytes": len(raw),
            "line_count": len(text.splitlines()),
            "function_line": text.count("\n", 0, function_start) + 1,
        },
        "fields": rows,
        "canonicalization": {
            "record_stride": RECORD_STRIDE if stride_observed else None,
            "full_record_copy": "observed" if copy_observed else "not-proven",
            "full_record_identity": "observed" if comparison_count == len(FIELDS) else "not-proven",
            "identity_detail": "the comparison loop checks both WORD fields and all four BYTE fields of the 8-byte record",
        },
        "semantic_links": {
            "declaration_record_to_canonicalizer": {
                "status": "observed" if comparison_count == len(FIELDS) else "not-proven",
                "detail": "FUN_00830f80 compares the same six-field, 8-byte shape produced by FUN_008587e0",
            },
            "d3dvertexelement9_shape": {
                "status": "observed" if comparison_count == len(FIELDS) else "not-proven",
                "detail": "field offsets match the D3DVERTEXELEMENT9 six-field layout already recovered in phase 83",
            },
        },
        "meb_property_mapping": {
            "status": "not-proven",
            "reason": "canonicalization compares declaration records but exposes no literal MEB property ids 460/461",
        },
    }


def analyze_d3d9_declaration_canonicalizer_file(path: str) -> dict[str, Any]:
    from pathlib import Path

    source_path = Path(path)
    report = analyze_d3d9_declaration_canonicalizer(source_path.read_bytes())
    report["source"]["path"] = str(source_path)
    return report
