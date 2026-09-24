"""Source-level evidence extractor for the recovered SHIFT.exe Ghidra C output.

This module never promotes an ABI guess. It records only observations that are
explicitly visible in the supplied decompilation and keeps unresolved linkage
machine-readable.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


FORMAT = "SHIFT.D3D9SourceVertexEvidence/1"

FUNCTIONS = {
    "packed_color_helper": "FUN_008310c0",
    "declaration_builder": "FUN_00854e70",
    "stream_builder": "FUN_00858180",
    "stream_data_parser": "FUN_00859800",
}


def _contains_all(source: str, needles: tuple[str, ...]) -> bool:
    return all(needle in source for needle in needles)


def analyze_shift_exe_c(source: str | bytes) -> dict[str, Any]:
    """Extract explicit D3D9 vertex/color observations from SHIFT.exe.c text."""
    if isinstance(source, bytes):
        raw = source
        text = source.decode("utf-8", errors="replace")
    else:
        text = str(source)
        raw = text.encode("utf-8")

    packed_helper = _contains_all(
        text,
        (
            "uint __fastcall FUN_008310c0(float *param_1)",
            "local_10 = (uint)(longlong)ROUND(param_1[3] * 255.0);",
            "return uVar1 << 8 | local_10;",
        ),
    )

    declaration_type_switch = _contains_all(
        text,
        (
            "switch(*pbVar18)",
            "case 4:",
            "fVar7 = (float)FUN_008310c0(&local_100);",
            "case 5:",
        ),
    )

    declaration_record_layout = _contains_all(
        text,
        (
            "*(undefined2 *)(*(int *)(iVar15 + 0x1c) + local_68 * 8) = 0xff;",
            "*(undefined1 *)(*(int *)(iVar15 + 0x1c) + 4 + iVar12) =",
            "*(undefined1 *)(*(int *)(iVar15 + 0x1c) + 6 + iVar12) =",
            "*(undefined1 *)(*(int *)(iVar15 + 0x1c) + 7 + iVar12) =",
        ),
    )

    stream_fields = _contains_all(
        text,
        (
            '"STREAM"',
            '"Usage"',
            '"Channel"',
        ),
    )

    packed_path = packed_helper and declaration_type_switch
    observations = [
        {
            "id": "packed-color-helper",
            "status": "observed" if packed_helper else "not-found",
            "function": FUNCTIONS["packed_color_helper"],
            "address": "0x008310C0",
            "detail": "float RGBA components are rounded to 8-bit and accumulated as 0xAARRGGBB",
            "little_endian_memory_order": "BGRA",
        },
        {
            "id": "declaration-type-4-packed-color",
            "status": "observed" if declaration_type_switch else "not-found",
            "function": FUNCTIONS["declaration_builder"],
            "address": "0x00854E70",
            "detail": "vertex conversion switch handles type 4 by calling FUN_008310c0",
            "type_code": 4,
            "conversion": "packed-color",
        },
        {
            "id": "declaration-record-fields",
            "status": "observed" if declaration_record_layout else "not-found",
            "function": FUNCTIONS["declaration_builder"],
            "address": "0x00854E70",
            "detail": "8-byte declaration records carry stream/offset/type/method/usage/usageIndex fields",
        },
        {
            "id": "stream-type-usage-channel",
            "status": "observed" if stream_fields else "not-found",
            "function": FUNCTIONS["stream_data_parser"],
            "address": "0x00859800",
            "detail": "STREAM records are parsed through Type, Usage and Channel fields",
        },
    ]

    linkage = {
        "meb_460_461_to_type_4": {
            "status": "not-proven",
            "reason": "source contains the D3D9 type conversion path but the exported C does not expose the DAT_00b90088/PTR_DAT_00b901d0 contents needed to link MEB property ids 460/461 directly to type 4",
        },
        "type_4_to_packed_color": {
            "status": "observed" if packed_path else "not-proven",
            "reason": "FUN_00854e70 case 4 calls FUN_008310c0" if packed_path else "required source patterns were not found",
        },
    }

    return {
        "format": FORMAT,
        "source": {
            "kind": "shift-exe-c",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        },
        "functions": FUNCTIONS,
        "observations": observations,
        "linkage": linkage,
        "selection": "not-selected",
        "verified_abi": False,
    }


def analyze_shift_exe_c_file(path: str | Path) -> dict[str, Any]:
    """Read one decompilation C dump and return its source evidence report."""
    source_path = Path(path)
    data = source_path.read_bytes()
    report = analyze_shift_exe_c(data)
    report["source"]["path"] = str(source_path)
    return report
