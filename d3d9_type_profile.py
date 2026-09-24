"""Deterministic semantic profile for the recovered D3D9 declaration Type codes.

The numeric Type codes 0..16 are source-backed by FUN_00854e70 and align with
the documented D3DDECLTYPE enumeration. This module supplies expected byte
sizes and source-component counts so a future raw DAT_00b8eef0/DAT_00b8ef38
memory dump can be checked without guessing table contents.

The profile is a validation oracle, not a replacement for the runtime table
bytes.
"""
from __future__ import annotations

from typing import Any, Mapping


FORMAT = "SHIFT.D3D9TypeProfile/1"
TYPE_UNUSED = 17

# (D3D9 enum name, source components consumed, packed element byte size)
TYPE_PROFILE: dict[int, tuple[str, int, int]] = {
    0: ("D3DDECLTYPE_FLOAT1", 1, 4),
    1: ("D3DDECLTYPE_FLOAT2", 2, 8),
    2: ("D3DDECLTYPE_FLOAT3", 3, 12),
    3: ("D3DDECLTYPE_FLOAT4", 4, 16),
    4: ("D3DDECLTYPE_D3DCOLOR", 4, 4),
    5: ("D3DDECLTYPE_UBYTE4", 4, 4),
    6: ("D3DDECLTYPE_SHORT2", 2, 4),
    7: ("D3DDECLTYPE_SHORT4", 4, 8),
    8: ("D3DDECLTYPE_UBYTE4N", 4, 4),
    9: ("D3DDECLTYPE_SHORT2N", 2, 4),
    10: ("D3DDECLTYPE_SHORT4N", 4, 8),
    11: ("D3DDECLTYPE_USHORT2N", 2, 4),
    12: ("D3DDECLTYPE_USHORT4N", 4, 8),
    13: ("D3DDECLTYPE_UDEC3", 3, 4),
    14: ("D3DDECLTYPE_DEC3N", 3, 4),
    15: ("D3DDECLTYPE_FLOAT16_2", 2, 4),
    16: ("D3DDECLTYPE_FLOAT16_4", 4, 8),
}


def expected_type_profile() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "types": [
            {
                "type_code": code,
                "d3d9_type": name,
                "source_components": components,
                "element_size_bytes": element_size,
            }
            for code, (name, components, element_size) in TYPE_PROFILE.items()
        ],
        "sentinel": {
            "type_code": TYPE_UNUSED,
            "d3d9_type": "D3DDECLTYPE_UNUSED",
            "role": "declaration terminator in the recovered renderer",
        },
        "basis": {
            "enum_alignment": "documented D3DDECLTYPE numeric order",
            "conversion_switch": "FUN_00854e70 cases 0..16",
            "runtime_size_lookup": "DAT_00b8eef0[Type]",
            "runtime_component_lookup": "DAT_00b8ef38[Type]",
        },
    }


def validate_type_tables(
    type_size_values: Mapping[int, int] | list[int | None],
    type_component_values: Mapping[int, int] | list[int | None],
) -> dict[str, Any]:
    """Compare raw Type tables with the semantic profile.

    Values are expected to be DWORDs already decoded from the runtime memory
    window. Missing entries are reported as unavailable rather than treated as
    zero.
    """
    def value_at(values: Mapping[int, int] | list[int | None], code: int) -> int | None:
        if isinstance(values, Mapping):
            value = values.get(code)
        elif code < len(values):
            value = values[code]
        else:
            value = None
        return int(value) if value is not None else None

    rows: list[dict[str, Any]] = []
    for code, (name, expected_components, expected_size) in TYPE_PROFILE.items():
        observed_size = value_at(type_size_values, code)
        observed_components = value_at(type_component_values, code)
        size_match = observed_size == expected_size if observed_size is not None else None
        components_match = (
            observed_components == expected_components
            if observed_components is not None
            else None
        )
        if observed_size is None or observed_components is None:
            status = "unavailable"
        elif size_match and components_match:
            status = "match"
        else:
            status = "mismatch"
        rows.append(
            {
                "type_code": code,
                "d3d9_type": name,
                "expected_element_size_bytes": expected_size,
                "observed_element_size_bytes": observed_size,
                "expected_source_components": expected_components,
                "observed_source_components": observed_components,
                "size_match": size_match,
                "component_match": components_match,
                "status": status,
            }
        )

    match_count = sum(row["status"] == "match" for row in rows)
    mismatch_count = sum(row["status"] == "mismatch" for row in rows)
    unavailable_count = sum(row["status"] == "unavailable" for row in rows)

    return {
        "format": FORMAT,
        "profile": expected_type_profile(),
        "validation": {
            "status": (
                "match"
                if match_count == len(rows)
                else ("mismatch" if mismatch_count else "partial")
            ),
            "match_count": match_count,
            "mismatch_count": mismatch_count,
            "unavailable_count": unavailable_count,
            "rows": rows,
        },
        "meb_property_mapping": {
            "status": "not-proven",
            "reason": "Type-table validation does not establish MEB 460/461 -> Type ordinal linkage",
        },
    }


def validate_type_table_report(report: Mapping[str, Any]) -> dict[str, Any]:
    tables = report.get("tables", {})
    type_size = tables.get("type_code", {}).get("values", [])
    type_components = tables.get("type_component_count", {}).get("values", [])
    return validate_type_tables(type_size, type_components)
