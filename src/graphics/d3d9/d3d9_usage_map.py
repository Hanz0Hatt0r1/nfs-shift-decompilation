"""Build a strict D3D9 Usage ordinal map from raw PE evidence."""
from __future__ import annotations

from typing import Any, Mapping
from pathlib import Path

FORMAT = "SHIFT.D3D9UsageMap/1"
EXPECTED_COUNT = 9


def build_d3d9_usage_map(pe_evidence: Mapping[str, Any]) -> dict[str, Any]:
    if pe_evidence.get("format") != "SHIFT.PEImageEvidence/1":
        raise ValueError("input is not SHIFT.PEImageEvidence/1")
    decoded = pe_evidence.get("decoded_tables")
    usage_rows = decoded.get("usage") if isinstance(decoded, Mapping) else None
    rows = [
        row for row in (usage_rows or [])
        if isinstance(row, Mapping)
        and isinstance(row.get("ordinal"), int)
        and isinstance(row.get("value"), int)
    ]
    by_ordinal = {row["ordinal"]: row["value"] for row in rows}
    missing = [ordinal for ordinal in range(EXPECTED_COUNT) if ordinal not in by_ordinal]
    blockers = ["usage-map:missing-ordinal:" + str(ordinal) for ordinal in missing]
    mapping = {
        str(ordinal): by_ordinal[ordinal]
        for ordinal in range(EXPECTED_COUNT)
        if ordinal in by_ordinal
    }
    return {
        "format": FORMAT,
        "status": "ready" if not blockers else "partial",
        "ready": not blockers,
        "source": {
            "format": pe_evidence.get("format"),
            "usage_table_status": (
                (pe_evidence.get("conclusions") or {}).get("usage_table_status")
            ),
        },
        "usage_map": mapping,
        "entry_count": len(mapping),
        "blocking_reasons": blockers,
        "evidence_policy": {
            "numeric_usage_source": "SHIFT.PEImageEvidence/1:decoded_tables.usage",
            "allows_inference": False,
        },
    }



def build_d3d9_usage_map_file(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    import json
    evidence = json.loads(source.read_text(encoding="utf-8"))
    return build_d3d9_usage_map(evidence)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Build SHIFT.D3D9UsageMap/1 from SHIFT.PEImageEvidence/1"
    )
    parser.add_argument("pe_evidence")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = build_d3d9_usage_map_file(args.pe_evidence)
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "format": report["format"],
                "status": report["status"],
                "ready": report["ready"],
                "entry_count": report["entry_count"],
                "blocking_reasons": report["blocking_reasons"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
