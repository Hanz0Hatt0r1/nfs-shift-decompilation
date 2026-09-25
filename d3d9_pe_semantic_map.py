"""Normalize file-backed SHIFT.exe D3D9 declaration tables into one ABI map.

This layer joins only evidence already present in SHIFT.PEImageEvidence/1:
the raw Type/size/component/Usage table words and the decoded internal Type names.
It does not infer MEB-property identities.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from d3d9_type_profile import TYPE_PROFILE

FORMAT = "SHIFT.D3D9PESemanticMap/1"
EXPECTED_TYPES = 17
EXPECTED_USAGES = 9

# Source-backed usage names from d3d9_usage_evidence.py. Numeric values come
# exclusively from the supplied PE report.
SOURCE_USAGE_NAMES: dict[int, str | None] = {
    0: "Position",
    1: "Weights",
    2: "Normal",
    3: None,
    4: "Tangent",
    5: "Binormal",
    6: "Colour",
    7: "Depth",
    8: "Indices",
}


def _rows_by_ordinal(rows: Any, count: int) -> dict[int, Any]:
    if not isinstance(rows, list):
        return {}
    result: dict[int, Any] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        ordinal = row.get("ordinal")
        if isinstance(ordinal, int) and 0 <= ordinal < count:
            result[ordinal] = row.get("value")
    return result


def _decoded_type_names(report: Mapping[str, Any]) -> dict[int, str]:
    result: dict[int, str] = {}
    for row in report.get("type_name_pointers", []) or []:
        if not isinstance(row, Mapping):
            continue
        ordinal = row.get("ordinal")
        name = row.get("string")
        if isinstance(ordinal, int) and 0 <= ordinal < EXPECTED_TYPES and isinstance(name, str):
            result[ordinal] = name
    # Accept the compact normalized projection too.
    for row in report.get("type_names", []) or []:
        if not isinstance(row, Mapping):
            continue
        ordinal = row.get("ordinal")
        name = row.get("name")
        if isinstance(ordinal, int) and 0 <= ordinal < EXPECTED_TYPES and isinstance(name, str):
            result[ordinal] = name
    return result


def build_d3d9_pe_semantic_map(
    pe_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    if pe_evidence.get("format") != "SHIFT.PEImageEvidence/1":
        return {
            "format": FORMAT,
            "status": "invalid",
            "ready": False,
            "blocking_reasons": ["pe-semantic-map:invalid-format"],
        }

    decoded = pe_evidence.get("decoded_tables")
    if not isinstance(decoded, Mapping):
        return {
            "format": FORMAT,
            "status": "blocked",
            "ready": False,
            "blocking_reasons": ["pe-semantic-map:decoded-tables-missing"],
        }

    type_codes = _rows_by_ordinal(decoded.get("type_code"), 20)
    type_sizes = _rows_by_ordinal(decoded.get("type_size"), 18)
    type_components = _rows_by_ordinal(decoded.get("type_components"), 18)
    usage_values = _rows_by_ordinal(decoded.get("usage"), EXPECTED_USAGES)
    names = _decoded_type_names(pe_evidence)

    blockers: list[str] = []
    types: list[dict[str, Any]] = []
    for ordinal in range(EXPECTED_TYPES):
        expected = TYPE_PROFILE[ordinal]
        code = type_codes.get(ordinal)
        size = type_sizes.get(ordinal)
        components = type_components.get(ordinal)
        row_status = "observed"
        if code is None:
            blockers.append(f"pe-semantic-map:type-code-missing:{ordinal}")
            row_status = "blocked"
        elif code != ordinal:
            blockers.append(
                f"pe-semantic-map:type-code-mismatch:{ordinal}:{code}"
            )
            row_status = "mismatch"
        if size is None:
            blockers.append(f"pe-semantic-map:type-size-missing:{ordinal}")
            row_status = "blocked"
        if components is None:
            blockers.append(f"pe-semantic-map:type-components-missing:{ordinal}")
            row_status = "blocked"
        if size is not None and size != expected[2]:
            blockers.append(
                f"pe-semantic-map:type-size-mismatch:{ordinal}:{size}:{expected[2]}"
            )
            row_status = "mismatch"
        if components is not None and components != expected[1]:
            blockers.append(
                f"pe-semantic-map:type-components-mismatch:{ordinal}:{components}:{expected[1]}"
            )
            row_status = "mismatch"
        types.append({
            "ordinal": ordinal,
            "d3d9_type": expected[0],
            "internal_name": names.get(ordinal),
            "element_size_bytes": size,
            "source_components": components,
            "status": row_status,
        })

    usages: list[dict[str, Any]] = []
    for ordinal in range(EXPECTED_USAGES):
        value = usage_values.get(ordinal)
        status = "observed" if value is not None else "blocked"
        if value is None:
            blockers.append(f"pe-semantic-map:usage-missing:{ordinal}")
        usages.append({
            "ordinal": ordinal,
            "source_name": SOURCE_USAGE_NAMES.get(ordinal),
            "numeric_d3d9_usage": value,
            "status": status,
        })

    color = {
        "type_4": next(row for row in types if row["ordinal"] == 4),
        "usage_6": next(row for row in usages if row["ordinal"] == 6),
    }

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "source": {
            "format": pe_evidence.get("format"),
            "image": pe_evidence.get("image"),
        },
        "types": types,
        "usages": usages,
        "color_abi": {
            "status": (
                "observed"
                if color["type_4"]["status"] == "observed"
                and color["usage_6"]["status"] == "observed"
                and color["type_4"]["d3d9_type"] == "D3DDECLTYPE_D3DCOLOR"
                and color["type_4"]["element_size_bytes"] == 4
                and color["type_4"]["source_components"] == 4
                and color["usage_6"]["numeric_d3d9_usage"] == 10
                else "blocked"
            ),
            **color,
        },
        "evidence_policy": {
            "source_of_numeric_type_code": "SHIFT.PEImageEvidence/1:decoded_tables.type_code",
            "source_of_numeric_usage": "SHIFT.PEImageEvidence/1:decoded_tables.usage",
            "allows_mib_property_inference": False,
        },
    }


def build_d3d9_pe_semantic_map_file(
    path: str | Path,
    output: str | Path,
) -> dict[str, Any]:
    source = Path(path)
    report = build_d3d9_pe_semantic_map(
        json.loads(source.read_text(encoding="utf-8"))
    )
    Path(output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Build SHIFT.D3D9PESemanticMap/1 from SHIFT.PEImageEvidence/1"
    )
    parser.add_argument("pe_evidence")
    parser.add_argument("output")
    args = parser.parse_args(argv)
    report = build_d3d9_pe_semantic_map_file(args.pe_evidence, args.output)
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "type_count": len(report["types"]),
        "usage_count": len(report["usages"]),
        "color_abi": report["color_abi"]["status"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
