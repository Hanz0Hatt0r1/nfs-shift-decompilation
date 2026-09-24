"""Extract source-backed evidence for the D3D9 declaration terminator producer.

FUN_008587e0 writes the complete final 8-byte declaration record:
Stream=0xffff, Offset=0, Type=0x11, Method=0, Usage=0, UsageIndex=0.
This module makes that producer explicit and connects it to the recovered
declaration count boundary without inventing any MEB mapping.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.D3D9DeclarationSentinelEvidence/1"
FUNCTION = "FUN_008587e0"
RECORD_STRIDE = 8
SENTINEL = {
    "stream": 0xFFFF,
    "offset": 0,
    "type": 0x11,
    "method": 0,
    "usage": 0,
    "usage_index": 0,
}


def _function_body(source: str, function: str) -> tuple[int | None, int | None, str]:
    lines = source.splitlines()
    pattern = re.compile(
        rf"(?m)^[^\n{{}}]*\b{re.escape(function)}\s*\([^;\n]*\)\s*(?:\n[^\n{{}}]*)?\{{"
    )
    match = pattern.search(source)
    if match is None:
        return None, None, ""
    start = source.count("\n", 0, match.start()) + 1
    depth = 0
    seen = False
    body: list[str] = []
    for index in range(start, len(lines) + 1):
        line = lines[index - 1]
        body.append(line)
        depth += line.count("{")
        depth -= line.count("}")
        if "{" in line:
            seen = True
        if seen and depth == 0:
            return start, index, "\n".join(body)
    return start, None, "\n".join(body)

def analyze_d3d9_declaration_sentinel(source: str) -> dict[str, Any]:
    if not isinstance(source, str):
        raise TypeError("source must be str")

    start, end, body = _function_body(source, FUNCTION)

    write_patterns = {
        "stream": r"\*\(undefined2 \*\)\(\*\(int \*\)\(param_1 \+ 0x1c\) \+ [^;=]+\) = 0xff;",
        "offset": r"\*\(undefined2 \*\)\(\*\(int \*\)\(param_1 \+ 0x1c\) \+ 2 \+ [^;=]+\) = 0;",
        "type": r"\*\(undefined1 \*\)\(\*\(int \*\)\(param_1 \+ 0x1c\) \+ 4 \+ [^;=]+\) = 0x11;",
        "method": r"\*\(undefined1 \*\)\(\*\(int \*\)\(param_1 \+ 0x1c\) \+ 5 \+ [^;=]+\) = 0;",
        "usage": r"\*\(undefined1 \*\)\(\*\(int \*\)\(param_1 \+ 0x1c\) \+ 6 \+ [^;=]+\) = 0;",
        "usage_index": r"\*\(undefined1 \*\)\(\*\(int \*\)\(param_1 \+ 0x1c\) \+ 7 \+ [^;=]+\) = 0;",
    }
    writes = {
        field: re.search(pattern, body, flags=re.MULTILINE) is not None
        for field, pattern in write_patterns.items()
    }
    count_indexing = any(
        re.search(r"\+ (?:\(int\))?[A-Za-z_]\w* \* 8", line)
        for line in body.splitlines()
    )
    all_fields = all(writes.values())

    return {
        "format": FORMAT,
        "status": "observed" if start is not None and all_fields and count_indexing else "not-proven",
        "source": {
            "kind": "shift-exe-c",
            "bytes": len(source.encode("utf-8")),
            "line_count": len(source.splitlines()),
            "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        },
        "function": FUNCTION,
        "record_stride": RECORD_STRIDE,
        "sentinel": SENTINEL,
        "observations": {
            "function_definition": {
                "status": "observed" if start is not None else "not-found",
                "line_start": start,
                "line_end": end,
            },
            "field_writes": {
                field: {
                    "status": "observed" if present else "not-found",
                    "value": SENTINEL[field],
                }
                for field, present in writes.items()
            },
            "record_indexing": {
                "status": "observed" if count_indexing else "not-found",
                "detail": "the six fields are written at count_index * 8",
            },
        },
        "semantic_links": {
            "exact_d3ddecl_end_shape": {
                "status": "observed" if all_fields else "not-proven",
                "detail": "all six D3DVERTEXELEMENT9 fields are source-written to the exact D3DDECL_END values",
            },
            "sentinel_follows_data_count": {
                "status": "observed" if count_indexing else "not-proven",
                "detail": "the sentinel is stored at the first record position after the parsed data elements",
            },
        },
        "meb_property_mapping": {
            "status": "not-proven",
            "detail": "Sentinel production does not establish MEB 460/461 -> Type linkage.",
        },
    }


def analyze_d3d9_declaration_sentinel_file(path: str | Path) -> dict[str, Any]:
    source_path = Path(path)
    return analyze_d3d9_declaration_sentinel(
        source_path.read_text(encoding="utf-8")
    )
