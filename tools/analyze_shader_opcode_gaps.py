#!/usr/bin/env python3
"""Analyze observed FXO opcode coverage against the software shader oracle."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from shader_reference import _SUPPORTED


def analyze_opcode_gaps(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") or {}
    observed = {
        str(name): int(count)
        for name, count in (summary.get("opcode_counts") or {}).items()
    }
    unsupported_counts = {
        str(name): int(count)
        for name, count in (
            summary.get("unsupported_opcode_counts") or {}
        ).items()
    }

    gaps = [
        {
            "opcode": opcode,
            "observed_instruction_count": count,
            "parser_unsupported_count": unsupported_counts.get(opcode, 0),
        }
        for opcode, count in observed.items()
        if opcode not in _SUPPORTED
    ]
    gaps.sort(
        key=lambda row: (
            -row["observed_instruction_count"],
            row["opcode"],
        )
    )

    return {
        "format": "SHIFT.FXOShaderOpcodeGapAnalysis/1",
        "version": 1,
        "source_format": report.get("format"),
        "observed_opcode_count": len(observed),
        "reference_supported_opcode_count": len(_SUPPORTED),
        "observed_supported_count": sum(
            opcode in _SUPPORTED for opcode in observed
        ),
        "gap_count": len(gaps),
        "gaps": gaps,
        # Fail closed: a corpus cannot be backend-ready while any observed
        # instruction remains outside the executable shader oracle.
        "ready": report.get("ready") is True and not gaps,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = json.loads(args.report.read_text(encoding="utf-8"))
    analysis = analyze_opcode_gaps(report)

    payload = json.dumps(
        analysis,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")

    print(payload, end="")
    return 0 if analysis["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
