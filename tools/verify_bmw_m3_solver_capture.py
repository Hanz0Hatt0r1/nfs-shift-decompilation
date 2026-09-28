#!/usr/bin/env python3
"""Verify a captured SDF solver frame against the real BMW M3 resource domain."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bmw_m3_e36_solver_domain_runtime import build_solver_domain
from bmw_m3_solver_capture_verify_runtime import (
    EXPECTED,
    verify_bmw_m3_capture_pair,
    verify_bmw_m3_capture_structure,
)
from rigid_body_sdf_runtime import parse_sdf
from shift_importer_v3_reference import BFF
from tools.verify_bmw_m3_e36_solver_domain import (
    extract_target_sdf,
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def verify_bff_domain(bff_path: Path) -> dict[str, Any]:
    data, provenance = extract_target_sdf(bff_path)
    sdf = parse_sdf(data, strict=True)
    solver = build_solver_domain(sdf)
    return {
        "ready": (
            solver.get("ready") is True
            and int(solver.get("solver_scalar_count", 0)) == EXPECTED["solver_scalar_count"]
        ),
        "source": provenance,
        "sdf": {
            "record_count": sdf.get("record_count"),
            "topology": sdf.get("topology", {}),
        },
        "solver_domain": solver,
    }


def build_report(
    *,
    bff_path: Path,
    capture_path: Path,
    expected_capture_path: Path | None = None,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
) -> dict[str, Any]:
    domain = verify_bff_domain(bff_path)
    capture = load_json(capture_path)
    structure = verify_bmw_m3_capture_structure(capture)

    expected = None
    comparison = None
    if expected_capture_path is not None:
        expected = load_json(expected_capture_path)
        comparison = verify_bmw_m3_capture_pair(
            capture,
            expected,
            abs_tol=abs_tol,
            rel_tol=rel_tol,
        )

    ready = bool(domain["ready"] and structure["ready"])
    if expected_capture_path is not None:
        ready = bool(ready and comparison and comparison["ready"])

    return {
        "format": "SHIFT.BMWM3SolverCaptureCLIReport/1",
        "version": 1,
        "status": (
            "verified-values"
            if expected_capture_path is not None and ready
            else "verified-structure"
            if ready
            else "diverged-or-blocked"
        ),
        "ready": ready,
        "expected_shape": EXPECTED,
        "domain": domain,
        "capture": {
            "path": str(capture_path),
            "structure": structure,
        },
        "expected_capture": (
            {"path": str(expected_capture_path)}
            if expected_capture_path is not None
            else None
        ),
        "comparison": comparison,
        "limitations": [
            "Without --expected-capture, this command verifies only BMW/domain/storage structure.",
            "Numeric equality requires a real expected solver frame; no values are synthesized.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bff", type=Path, help="real BMW_M3_E36.bff")
    parser.add_argument("capture", type=Path, help="normalized solver-frame JSON")
    parser.add_argument("--expected-capture", type=Path)
    parser.add_argument("--abs-tol", type=float, default=0.0)
    parser.add_argument("--rel-tol", type=float, default=0.0)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = build_report(
        bff_path=args.bff,
        capture_path=args.capture,
        expected_capture_path=args.expected_capture,
        abs_tol=args.abs_tol,
        rel_tol=args.rel_tol,
    )
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "
"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")

    print(
        json.dumps(
            {
                "format": report["format"],
                "status": report["status"],
                "ready": report["ready"],
                "solver_scalar_count": report["domain"]["solver_domain"].get("solver_scalar_count"),
                "capture_scalar_count": report["capture"]["structure"]["observed"]["solver_scalar_count"],
                "blocking_errors": report["capture"]["structure"]["errors"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
