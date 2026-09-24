"""Extract source-backed D3D9 vertex-declaration creation evidence.

FUN_00830f80 canonicalizes/interns an 8-byte declaration-record array,
allocates a byte buffer sized as element_count * 8 + 8, copies that byte
sequence, and dispatches through the IDirect3DDevice9 CreateVertexDeclaration
vtable slot.

This layer records the observed dataflow without guessing the contents of the
extra record or assigning MEB properties.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.D3D9DeclarationCreateEvidence/1"
FUNCTION = "FUN_00830f80"
VTABLE_BYTE_OFFSET = 0x158
VTABLE_SLOT = 86
API_METHOD = "IDirect3DDevice9::CreateVertexDeclaration"
RECORD_STRIDE = 8


def _function_body(source: str, function: str) -> tuple[int | None, int | None, str]:
    lines = source.splitlines()
    match = re.search(rf"\b{re.escape(function)}\s*\(", source)
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

def analyze_d3d9_declaration_create(source: str) -> dict[str, Any]:
    if not isinstance(source, str):
        raise TypeError("source must be str")

    start, end, body = _function_body(source, FUNCTION)
    allocation_pattern = re.search(
        r"uVar1\s*=\s*uVar1\s*\*\s*8\s*\+\s*8;",
        body,
    )
    memcpy_pattern = re.search(
        r"_memcpy\([^,]+,\s*param_1,\s*uVar1\);",
        body,
    )
    create_pattern = re.search(
        r"\(\*\*\(code \*\*\)\(\*piVar3 \+ 0x158\)\)\([^\n]+,\s*[^\n]+,\s*puVar5\);",
        body,
    )
    fallback_create_pattern = re.search(
        r"\+ 0x158\)\)\([^\n]+\);",
        body,
    )
    canonicalized_storage = "*(ushort **)(puVar5 + 2) = puVar6;" in body
    return_value = "return puVar5;" in body

    observations = {
        "function_definition": {
            "status": "observed" if start is not None else "not-found",
            "line_start": start,
            "line_end": end,
        },
        "record_buffer_growth": {
            "status": "observed" if allocation_pattern else "not-found",
            "expression": "uVar1 * 8 + 8",
            "record_stride": RECORD_STRIDE,
        },
        "record_bytes_copied": {
            "status": "observed" if memcpy_pattern else "not-found",
            "detail": "the canonicalized input bytes are copied into the created declaration buffer",
        },
        "create_vertex_declaration_dispatch": {
            "status": "observed" if create_pattern or fallback_create_pattern else "not-found",
            "vtable_slot": VTABLE_SLOT,
            "vtable_byte_offset": f"0x{VTABLE_BYTE_OFFSET:x}",
        },
        "created_object_storage": {
            "status": "observed" if canonicalized_storage else "not-found",
            "detail": "the resulting declaration object is retained by the interned record",
        },
        "intern_return": {
            "status": "observed" if return_value else "not-found",
        },
    }
    ok = all(row["status"] == "observed" for row in observations.values())

    return {
        "format": FORMAT,
        "status": "observed" if ok else "not-proven",
        "source": {
            "kind": "shift-exe-c",
            "bytes": len(source.encode("utf-8")),
            "line_count": len(source.splitlines()),
            "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        },
        "function": FUNCTION,
        "api_identity": {
            "method": API_METHOD,
            "vtable_slot": VTABLE_SLOT,
            "vtable_byte_offset": f"0x{VTABLE_BYTE_OFFSET:x}",
            "basis": "IDirect3DDevice9 documented method ordering",
        },
        "observations": observations,
        "semantic_links": {
            "canonical_record_bytes_to_create_call": {
                "status": (
                    "observed"
                    if observations["record_bytes_copied"]["status"] == "observed"
                    and observations["create_vertex_declaration_dispatch"]["status"] == "observed"
                    else "not-proven"
                ),
                "detail": "the recovered canonicalizer copies the declaration-record byte array into the buffer passed to CreateVertexDeclaration",
            },
            "create_to_declaration_object": {
                "status": "observed"
                if observations["created_object_storage"]["status"] == "observed"
                else "not-proven",
                "detail": "the create call's returned declaration object is retained in the interned declaration record",
            },
        },
        "record_layout": {
            "stride_bytes": RECORD_STRIDE,
            "buffer_expression": "element_count * 8 + 8",
            "extra_record_bytes": 8,
        },
        "meb_property_mapping": {
            "status": "not-proven",
            "detail": "Declaration creation evidence does not establish MEB 460/461 -> Type linkage.",
        },
    }


def analyze_d3d9_declaration_create_file(path: str | Path) -> dict[str, Any]:
    source_path = Path(path)
    return analyze_d3d9_declaration_create(
        source_path.read_text(encoding="utf-8")
    )
