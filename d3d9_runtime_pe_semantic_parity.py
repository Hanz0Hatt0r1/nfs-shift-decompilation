"""Compare runtime D3D9 declaration numeric fields against the supplied SHIFT.exe PE ABI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from d3d9_pe_semantic_map import build_d3d9_pe_semantic_map

FORMAT = "SHIFT.D3D9RuntimePESemanticParity/1"


def _load(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    payload = json.loads(Path(value).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {value}")
    return payload


def validate_runtime_against_pe(
    runtime: str | Path | Mapping[str, Any],
    pe_evidence: str | Path | Mapping[str, Any],
) -> dict[str, Any]:
    runtime_report = _load(runtime)
    pe_report = _load(pe_evidence)
    pe_map = build_d3d9_pe_semantic_map(pe_report)

    if runtime_report.get("format") != "SHIFT.D3D9DeclarationInstanceEvidence/1":
        return {
            "format": FORMAT,
            "status": "invalid",
            "ready": False,
            "blocking_reasons": ["runtime-pe-parity:invalid-runtime-format"],
        }
    if not pe_map.get("ready"):
        return {
            "format": FORMAT,
            "status": "blocked",
            "ready": False,
            "blocking_reasons": [
                "runtime-pe-parity:pe-semantic-map-not-ready",
                *(pe_map.get("blocking_reasons") or []),
            ],
        }

    type_map = {
        int(row["ordinal"]): row
        for row in pe_map["types"]
        if isinstance(row.get("ordinal"), int)
    }
    usage_map = {
        int(row["ordinal"]): row
        for row in pe_map["usages"]
        if isinstance(row.get("ordinal"), int)
    }
    usage_values = {
        int(row["numeric_d3d9_usage"])
        for row in usage_map.values()
        if isinstance(row.get("numeric_d3d9_usage"), int)
    }

    records = runtime_report.get("records")
    if not isinstance(records, list) or not records:
        return {
            "format": FORMAT,
            "status": "blocked",
            "ready": False,
            "blocking_reasons": ["runtime-pe-parity:runtime-records-missing"],
            "records": [],
        }

    checks: list[dict[str, Any]] = []
    blockers: list[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            blockers.append(f"runtime-pe-parity:record-not-object:{index}")
            continue

        type_code = record.get("type")
        usage = record.get("usage")
        row: dict[str, Any] = {
            "record_index": index,
            "type": type_code,
            "usage": usage,
            "type_status": "blocked",
            "usage_status": "blocked",
        }

        if isinstance(type_code, int) and type_code in type_map:
            expected = type_map[type_code]
            row["type_status"] = "observed" if expected["status"] == "observed" else "mismatch"
            row["d3d9_type"] = expected["d3d9_type"]
            row["element_size_bytes"] = expected["element_size_bytes"]
        else:
            row["type_status"] = "mismatch"
            blockers.append(
                f"runtime-pe-parity:type-code-not-in-pe-map:{index}:{type_code}"
            )

        if isinstance(usage, int) and usage in usage_values:
            row["usage_status"] = "observed"
            row["usage_ordinal_candidates"] = [
                ordinal
                for ordinal, usage_row in usage_map.items()
                if usage_row.get("numeric_d3d9_usage") == usage
            ]
        else:
            row["usage_status"] = "mismatch"
            blockers.append(
                f"runtime-pe-parity:usage-value-not-in-pe-map:{index}:{usage}"
            )

        checks.append(row)

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not blockers else "mismatch",
        "ready": not blockers,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "runtime_format": runtime_report.get("format"),
        "pe_map_format": pe_map.get("format"),
        "records": checks,
        "policy": {
            "type_source": "SHIFT.D3D9PESemanticMap/1",
            "usage_source": "SHIFT.D3D9PESemanticMap/1",
            "property_identity": "not-established-by-numeric-parity",
            "same_instance": "separate-gate",
        },
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Check runtime D3D9 declaration fields against SHIFT.exe PE ABI"
    )
    parser.add_argument("runtime")
    parser.add_argument("pe_evidence")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    result = validate_runtime_against_pe(args.runtime, args.pe_evidence)
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": result["format"],
        "status": result["status"],
        "ready": result["ready"],
        "blocking_reasons": result["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
