"""Evidence-backed mapping of the recovered D3D9 primitive type switch.

The recovered renderer uses a 0..16 switch in FUN_00854e70. This module records
the exact source behavior for each case and the corresponding D3D9 declaration
enum name. It never uses the mapping to resolve an MEB property id.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


FORMAT = "SHIFT.D3D9TypeSemanticsEvidence/1"
FUNCTION = "FUN_00854e70"
SWITCH_MARKER = "switch(*pbVar18)"


D3D9_TYPES: dict[int, str] = {
    0: "D3DDECLTYPE_FLOAT1",
    1: "D3DDECLTYPE_FLOAT2",
    2: "D3DDECLTYPE_FLOAT3",
    3: "D3DDECLTYPE_FLOAT4",
    4: "D3DDECLTYPE_D3DCOLOR",
    5: "D3DDECLTYPE_UBYTE4",
    6: "D3DDECLTYPE_SHORT2",
    7: "D3DDECLTYPE_SHORT4",
    8: "D3DDECLTYPE_UBYTE4N",
    9: "D3DDECLTYPE_SHORT2N",
    10: "D3DDECLTYPE_SHORT4N",
    11: "D3DDECLTYPE_USHORT2N",
    12: "D3DDECLTYPE_USHORT4N",
    13: "D3DDECLTYPE_UDEC3",
    14: "D3DDECLTYPE_DEC3N",
    15: "D3DDECLTYPE_FLOAT16_2",
    16: "D3DDECLTYPE_FLOAT16_4",
}


CASE_DETAILS: dict[int, dict[str, Any]] = {
    0: {"behavior": "fallthrough to float memcpy; copies uVar4 32-bit components"},
    1: {"behavior": "fallthrough to float memcpy; copies uVar4 32-bit components"},
    2: {"behavior": "fallthrough to float memcpy; copies uVar4 32-bit components"},
    3: {"behavior": "memcpy(local_18, local_84, uVar4 * 4)"},
    4: {
        "behavior": "packs four float components through FUN_008310c0",
        "required": (
            "local_100 = local_84[0];",
            "local_fc = local_84[1];",
            "local_f8 = local_84[2];",
            "local_f4 = local_78;",
            "FUN_008310c0(&local_100);",
        ),
    },
    5: {
        "behavior": "rounds each source component directly to an 8-bit byte",
        "required": ("ROUND(local_84[uVar11])", "*(undefined1 *)((int)&local_c0 + uVar11)"),
    },
    6: {
        "behavior": "rounds components to signed 16-bit storage",
        "required": ("FUN_00901310(uVar5,uVar4);", "local_c4"),
    },
    7: {
        "behavior": "rounds components to signed 16-bit storage",
        "required": ("FUN_00901310(uVar5,uVar4);", "local_dc"),
    },
    8: {
        "behavior": "rounds components after multiplying by 255.0",
        "required": ("ROUND(local_84[uVar11] * 255.0)", "local_b4"),
    },
    9: {
        "behavior": "rounds components to signed 16-bit storage",
        "required": ("FUN_00901310(uVar5,uVar4);", "local_ac"),
        "note": "the recovered conversion path does not explicitly multiply by 32767.0",
    },
    10: {
        "behavior": "rounds components to signed 16-bit storage",
        "required": ("FUN_00901310(uVar5,uVar4);", "local_a4"),
        "note": "the recovered conversion path does not explicitly multiply by 32767.0",
    },
    11: {
        "behavior": "rounds components after multiplying by 65535.0",
        "required": ("ROUND(*pfVar14 * 65535.0)", "uStack_76"),
    },
    12: {
        "behavior": "rounds components after multiplying by 65535.0",
        "required": ("ROUND(*pfVar14 * 65535.0)", "local_98"),
    },
    13: {
        "behavior": "packs three clamped 10-bit values",
        "required": ("0x3fe", "0x400", "local_ec"),
    },
    14: {
        "behavior": "packs three rounded values into a 10:10:10-style integer",
        "required": ("FUN_00901310(uVar5,uVar4);", "local_d0", "0x400"),
    },
    15: {
        "behavior": "encodes two float components through the recovered 16-bit float helper",
        "required": ("FUN_0064fcb0(this,(uint)local_84[uVar11]);", "local_38"),
    },
    16: {
        "behavior": "encodes four float components through the recovered 16-bit float helper",
        "required": ("FUN_0064fcb0(puVar16,(uint)local_84[uVar11]);", "local_8c"),
    },
}


def _line_number(source: str, needle: str, start: int = 0) -> int | None:
    offset = source.find(needle, start)
    if offset < 0:
        return None
    return source.count("\n", 0, offset) + 1


def _switch_region(source: str) -> tuple[str, int] | None:
    function_start = source.find(f"undefined4 __fastcall {FUNCTION}")
    if function_start < 0:
        return None
    switch_start = source.find(SWITCH_MARKER, function_start)
    if switch_start < 0:
        return None
    end_marker = "\n  FUN_00886930(local_3c"
    switch_end = source.find(end_marker, switch_start)
    if switch_end < 0:
        switch_end = len(source)
    return source[switch_start:switch_end], switch_start


def _case_positions(switch_text: str) -> dict[int, int]:
    positions: dict[int, int] = {}
    for match in re.finditer(r"(?m)^\s*case (0x[0-9A-Fa-f]+|[0-9]+):", switch_text):
        positions[int(match.group(1), 0)] = match.start()
    return positions


def analyze_d3d9_type_semantics(source: str | bytes) -> dict[str, Any]:
    if isinstance(source, bytes):
        raw = source
        text = source.decode("utf-8", errors="replace")
    else:
        text = str(source)
        raw = text.encode("utf-8")

    region_info = _switch_region(text)
    if region_info is None:
        return {
            "format": FORMAT,
            "function": FUNCTION,
            "enum_alignment": {"status": "not-found", "observed_case_count": 0},
            "cases": [],
            "source": {"bytes": len(raw)},
        }

    switch_text, switch_offset = region_info
    positions = _case_positions(switch_text)
    expected = set(D3D9_TYPES)
    observed = set(positions)
    all_cases_present = expected.issubset(observed)
    sorted_codes = sorted(code for code in observed if code in expected)

    rows: list[dict[str, Any]] = []
    for code in sorted_codes:
        start = positions[code]
        following = [
            pos for other, pos in positions.items()
            if pos > start
        ]
        end = min(following) if following else len(switch_text)
        block = switch_text[start:end]
        details = CASE_DETAILS[code]
        if code in (0, 1, 2):
            ok = all(
                marker in switch_text
                for marker in ("case 0:", "case 1:", "case 2:", "case 3:", "_memcpy(local_18,local_84,uVar4 * 4);")
            )
        elif code == 3:
            ok = "_memcpy(local_18,local_84,uVar4 * 4);" in block
        else:
            ok = all(marker in block for marker in details.get("required", ()))
        rows.append(
            {
                "type_code": code,
                "d3d9_type": D3D9_TYPES[code],
                "status": "observed" if ok else "not-found",
                "source_line": _line_number(text, f"case {code}:" if code < 11 else f"case 0x{code:x}:", switch_offset),
                "source_behavior": details["behavior"],
                **({"note": details["note"]} if "note" in details else {}),
                "identity_basis": "numeric D3D9 enum alignment + recovered conversion behavior",
            }
        )

    observed_count = sum(row["status"] == "observed" for row in rows)
    return {
        "format": FORMAT,
        "function": FUNCTION,
        "enum_alignment": {
            "status": "observed" if all_cases_present else "not-proven",
            "expected_case_count": len(expected),
            "observed_case_count": len(observed & expected),
            "missing_cases": sorted(expected - observed),
        },
        "cases": rows,
        "source": {
            "kind": "shift-exe-c",
            "bytes": len(raw),
            "line_count": len(text.splitlines()),
        },
        "meb_property_mapping": {
            "status": "not-proven",
            "reason": "this module identifies the recovered primitive-type switch only; it does not establish MEB 460/461 -> type code",
        },
    }


def analyze_d3d9_type_semantics_file(path: str | Path) -> dict[str, Any]:
    source_path = Path(path)
    report = analyze_d3d9_type_semantics(source_path.read_bytes())
    report["source"]["path"] = str(source_path)
    return report
