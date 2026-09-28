#!/usr/bin/env python3
"""Verify a captured SDF solver frame against the real BMW M3 resource domain."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bmw_m3_e36_solver_domain_runtime import build_solver_domain
from bmw_m3_solver_capture_verify_runtime import (
    EXPECTED,
    verify_bmw_m3_capture_pair,
    verify_bmw_m3_capture_structure,
)
from rigid_body_sdf_runtime import parse_sdf
from shift_importer_v3_reference import BFF


TARGET_ARCHIVE_SHA256 = "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70"
TARGET_RESOURCE = "vehicles/physics/suspension/aarm_multilink.sdf"
TARGET_RESOURCE_SHA256 = "fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed"


def extract_target_sdf(bff_path: Path) -> tuple[bytes, dict[str, Any]]:
    import hashlib
    archive_sha = hashlib.sha256(bff_path.read_bytes()).hexdigest()
    if archive_sha != TARGET_ARCHIVE_SHA256:
        raise ValueError(
            f"unexpected BMW_M3_E36.bff SHA-256: {archive_sha} != {TARGET_ARCHIVE_SHA256}"
        )
    with BFF(bff_path) as archive:
        target = TARGET_RESOURCE.strip("/").lower()
        matches = [
            entry for entry in archive.entries
            if entry.path.replace("\\", "/").strip("/").lower() == target
        ]
        if len(matches) != 1:
            raise ValueError(
                f"expected exactly one {TARGET_RESOURCE!r}, found {len(matches)}"
            )
        entry = matches[0]
        data = archive.extract_entry(entry, type2="lzx")
        digest = hashlib.sha256(data).hexdigest()
        if digest != TARGET_RESOURCE_SHA256:
            raise ValueError(
                f"unexpected SDF SHA-256: {digest} != {TARGET_RESOURCE_SHA256}"
            )
        return data, {
            "archive": archive.path.name,
            "archive_sha256": archive_sha,
            "entry_index": entry.index,
            "path": entry.path,
            "compression_type": entry.type,
            "compressed_size": entry.compressed_size,
            "uncompressed_size": entry.uncompressed_size,
            "decoded_sha256": digest,
        }


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
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
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
