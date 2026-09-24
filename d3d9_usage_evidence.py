"""Evidence-backed usage semantics from the recovered SHIFT.exe stream loader.

The original loader resolves XML STREAM Usage strings through a fixed 0..8 table.
This module records only source-visible names and preserves the unresolved entries
whose string initializers were not emitted by the Ghidra C export.
"""
from __future__ import annotations

import re
from typing import Any


FORMAT = "SHIFT.D3D9UsageSemanticsEvidence/1"
FUNCTIONS = {
    "stream_parser": "FUN_008587e0",
    "declaration_builder": "FUN_00854e70",
}


EXPECTED_USAGE_NAMES: dict[int, str | None] = {
    0: "Position",
    1: "Weights",
    2: "Normal",
    3: None,  # Ghidra emits DAT_00b1d188 for this entry.
    4: "Tangent",
    5: "Binormal",
    6: "Colour",
    7: "Depth",
    8: "Indices",
}


def _line_number(source: str, needle: str, start: int = 0) -> int | None:
    offset = source.find(needle, start)
    if offset < 0:
        return None
    return source.count("\n", 0, offset) + 1


def _switch_region(source: str) -> tuple[str, int, int] | None:
    """Return the target Usage switch, its absolute offset and function start."""
    function_start = source.find("uint __fastcall FUN_008587e0")
    if function_start < 0:
        return None
    switch_start = source.find("switch(local_5c)", function_start)
    if switch_start < 0:
        return None
    switch_end = source.find("\n              while (pvVar10 !=", switch_start)
    if switch_end < 0:
        switch_end = len(source)
    return source[switch_start:switch_end], switch_start, function_start


def _case_block(switch_text: str, case: int) -> tuple[str, int] | None:
    start = re.search(rf"(?m)^\s*case {case}:\s*$", switch_text)
    if not start:
        return None
    following = re.search(r"(?m)^\s*case (?:[0-9]+|default):", switch_text[start.end():])
    end = start.end() + following.start() if following else len(switch_text)
    return switch_text[start.start():end], start.start()


def analyze_d3d9_usage_semantics(source: str | bytes) -> dict[str, Any]:
    if isinstance(source, bytes):
        raw = source
        text = source.decode("utf-8", errors="replace")
    else:
        text = str(source)
        raw = text.encode("utf-8")

    region = _switch_region(text)
    switch_text = region[0] if region else ""
    switch_offset = region[1] if region else -1
    function_offset = region[2] if region else -1
    switch_line = (
        _line_number(text, "switch(local_5c)", switch_offset)
        if switch_offset >= 0
        else None
    )
    usage_loop_line = (
        _line_number(text, "} while (local_5c < 9);", function_offset)
        if function_offset >= 0
        else None
    )
    pointer_array_line = (
        _line_number(
            text,
            "pbVar17 = (&PTR_s_Position_00b901a8)[local_5c];",
            function_offset,
        )
        if function_offset >= 0
        else None
    )

    rows: list[dict[str, Any]] = []
    for code, expected_name in EXPECTED_USAGE_NAMES.items():
        case_info = _case_block(switch_text, code) if switch_text else None
        block = case_info[0] if case_info else ""
        case_offset = switch_offset + case_info[1] if case_info and switch_offset >= 0 else -1
        literal = f'pcVar23 = "{expected_name}";' if expected_name else 'pcVar23 = &DAT_00b1d188;'
        observed = bool(block) and literal in block
        rows.append(
            {
                "usage_code": code,
                "source_name": expected_name,
                "status": "observed" if observed else "not-found",
                "source_line": (
                    text.count("\n", 0, case_offset) + 1
                    if case_offset >= 0
                    else None
                ),
                "source_symbol": "DAT_00b1d188" if code == 3 else None,
            }
        )

    by_code = {row["usage_code"]: row for row in rows}
    return {
        "format": FORMAT,
        "functions": FUNCTIONS,
        "source": {
            "kind": "shift-exe-c",
            "bytes": len(raw),
            "line_count": len(text.splitlines()),
        },
        "switch": {
            "source_line": switch_line,
            "status": "observed" if switch_line is not None else "not-found",
            "usage_exclusive_limit": 9 if usage_loop_line is not None else None,
            "usage_loop_line": usage_loop_line,
            "pointer_array_lookup_line": pointer_array_line,
            "pointer_array": "PTR_s_Position_00b901a8" if pointer_array_line is not None else None,
        },
        "usages": rows,
        "semantic_links": {
            "usage_6_to_colour": {
                "status": "observed"
                if by_code[6]["status"] == "observed"
                else "not-proven",
                "detail": "source case 6 names the stream Usage as Colour",
            },
            "usage_6_to_meb_colour_properties": {
                "status": "not-proven",
                "detail": "this source-only module does not establish MEB property 460/461 linkage",
            },
        },
    }


def analyze_d3d9_usage_semantics_file(path: str) -> dict[str, Any]:
    from pathlib import Path

    source_path = Path(path)
    report = analyze_d3d9_usage_semantics(source_path.read_bytes())
    report["source"]["path"] = str(source_path)
    return report
