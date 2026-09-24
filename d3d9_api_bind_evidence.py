"""Extract source-backed evidence for the D3D9 declaration bind API boundary.

The recovered wrapper FUN_0082e510 dispatches through an IDirect3DDevice9-like
COM vtable. The D3D9 SDK method ordering identifies slot 87 as
SetVertexDeclaration; the corresponding byte offset is 87 * 4 = 0x15c.

This report records only source observations and the external ABI slot identity.
It does not infer MEB property mappings.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.D3D9ApiBindEvidence/1"
FUNCTION = "FUN_0082e510"
VTABLE_BYTE_OFFSET = 0x15C
VTABLE_SLOT = VTABLE_BYTE_OFFSET // 4
API_METHOD = "IDirect3DDevice9::SetVertexDeclaration"


def analyze_d3d9_api_bind_source(source: str) -> dict[str, Any]:
    if not isinstance(source, str):
        raise TypeError("source must be str")

    lines = source.splitlines()
    function_start = None
    function_end = None
    function_body: list[str] = []
    for index, line in enumerate(lines, 1):
        if line.startswith(f"uint __fastcall {FUNCTION}("):
            function_start = index
            break

    if function_start is not None:
        brace_depth = 0
        seen_brace = False
        for index in range(function_start, len(lines) + 1):
            line = lines[index - 1]
            function_body.append(line)
            brace_depth += line.count("{")
            brace_depth -= line.count("}")
            if "{" in line:
                seen_brace = True
            if seen_brace and brace_depth == 0:
                function_end = index
                break

    body = "\n".join(function_body)
    vtable_pattern = re.compile(
        r"\(\*\*\(code \*\*\)\(\*\*\(int \*\*\)"
        + re.escape(FUNCTION)
        + r"?"
    )
    exact_dispatch = (
        "(**(code **)(**(int **)(param_1 + 0x478) + 0x15c))"
        in body
    )
    argument_forwarding = (
        "*(int **)(param_1 + 0x478),*param_2" in body
        or "*(int **)(param_1 + 0x478),*param_2)" in body
    )
    cache_field = "*(undefined4 **)(param_1 + 0x70c) = param_2;" in body
    null_guard = "if (param_2 != (undefined4 *)0x0)" in body

    api_identity = {
        "vtable_slot": VTABLE_SLOT,
        "vtable_byte_offset": f"0x{VTABLE_BYTE_OFFSET:x}",
        "method": API_METHOD,
        "basis": "IDirect3DDevice9 method order / vtable slot reference",
    }

    observations = {
        "function_definition": {
            "status": "observed" if function_start is not None else "not-found",
            "line_start": function_start,
            "line_end": function_end,
        },
        "device_vtable_dispatch": {
            "status": "observed" if exact_dispatch else "not-found",
            "byte_offset": f"0x{VTABLE_BYTE_OFFSET:x}",
            "slot": VTABLE_SLOT,
        },
        "declaration_argument_forwarded": {
            "status": "observed" if argument_forwarding else "not-found",
            "detail": "the wrapper forwards *param_2 to the dispatched device method",
        },
        "null_declaration_guard": {
            "status": "observed" if null_guard else "not-found",
            "detail": "a null declaration pointer is not passed to the device dispatch",
        },
        "cached_current_declaration": {
            "status": "observed" if cache_field else "not-found",
            "field_offset": "0x70c",
        },
    }

    all_source_observed = all(
        item["status"] == "observed"
        for item in observations.values()
    )
    return {
        "format": FORMAT,
        "status": "observed" if all_source_observed else "not-proven",
        "source": {
            "kind": "shift-exe-c",
            "bytes": len(source.encode("utf-8")),
            "line_count": len(lines),
            "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        },
        "function": FUNCTION,
        "api_identity": api_identity,
        "observations": observations,
        "semantic_links": {
            "declaration_object_to_d3d9_bind": {
                "status": (
                    "observed"
                    if exact_dispatch and argument_forwarding
                    else "not-proven"
                ),
                "detail": (
                    "FUN_0082e510 dispatches the declaration object through the "
                    "D3D9 device vtable slot identified as SetVertexDeclaration"
                ),
            },
            "bind_cache": {
                "status": "observed" if cache_field else "not-proven",
                "detail": "the wrapper caches the current declaration pointer at device state offset 0x70c",
            },
        },
        "external_api_reference": {
            "method": API_METHOD,
            "vtable_slot": VTABLE_SLOT,
            "vtable_byte_offset": f"0x{VTABLE_BYTE_OFFSET:x}",
            "reference_basis": "documented IDirect3DDevice9 interface method ordering",
        },
        "meb_property_mapping": {
            "status": "not-proven",
            "detail": "The API bind boundary does not establish MEB 460/461 -> Type linkage.",
        },
    }


def analyze_d3d9_api_bind_file(path: str | Path) -> dict[str, Any]:
    source_path = Path(path)
    return analyze_d3d9_api_bind_source(
        source_path.read_text(encoding="utf-8")
    )
