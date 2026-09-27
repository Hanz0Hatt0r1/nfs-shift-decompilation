#!/usr/bin/env python3
"""Verify the real BMW M3 SDF solver domain directly from a retail BFF."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from rigid_body_sdf_runtime import parse_sdf
from shift_importer_v3_reference import BFF
from bmw_m3_e36_solver_domain_runtime import build_solver_domain, validate_expected_bmw_shape

TARGET_ARCHIVE_SHA256 = "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70"
TARGET_RESOURCE = "vehicles/physics/suspension/aarm_multilink.sdf"
TARGET_RESOURCE_SHA256 = "fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed"
EXPECTED_BODY_COUNT = 11
EXPECTED_JOINT_HINGE_COUNT = 4
EXPECTED_BAR_COUNT = 20

FORMAT = "SHIFT.BMWM3SolverDomainVerifier/1"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_target_sdf(bff_path: str | Path) -> tuple[bytes, dict[str, Any]]:
    path = Path(bff_path)
    archive_sha = sha256_bytes(path.read_bytes())
    if archive_sha != TARGET_ARCHIVE_SHA256:
        raise ValueError(
            f"unexpected BMW_M3_E36.bff SHA-256: {archive_sha} != {TARGET_ARCHIVE_SHA256}"
        )

    with BFF(path) as archive:
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
        digest = sha256_bytes(data)
        if digest != TARGET_RESOURCE_SHA256:
            raise ValueError(
                f"unexpected SDF SHA-256: {digest} != {TARGET_RESOURCE_SHA256}"
            )
        provenance = {
            "archive": archive.path.name,
            "archive_sha256": archive_sha,
            "entry_index": entry.index,
            "path": entry.path,
            "compression_type": entry.type,
            "compressed_size": entry.compressed_size,
            "uncompressed_size": entry.uncompressed_size,
            "decoded_sha256": digest,
        }
        return data, provenance


def verify(bff_path: str | Path) -> dict[str, Any]:
    data, provenance = extract_target_sdf(bff_path)
    sdf = parse_sdf(data, strict=True)
    topology = sdf.get("topology", {})
    solver = build_solver_domain(sdf)
    shape = validate_expected_bmw_shape(
        solver,
        body_count=int(topology.get("body_count", 0)),
        joint_hinge_count=int(topology.get("joint_hinge_count", 0)),
        bar_count=int(topology.get("bar_count", 0)),
    )
    expected_shape = validate_expected_bmw_shape(
        solver,
        body_count=EXPECTED_BODY_COUNT,
        joint_hinge_count=EXPECTED_JOINT_HINGE_COUNT,
        bar_count=EXPECTED_BAR_COUNT,
    )
    ready = bool(
        solver.get("ready") is True
        and shape.get("ready") is True
        and expected_shape.get("ready") is True
        and int(solver.get("solver_scalar_count", 0)) == 40
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "verified" if ready else "blocked",
        "ready": ready,
        "source": provenance,
        "sdf": {
            "record_count": sdf.get("record_count"),
            "entry_count": sdf.get("entry_count"),
            "topology": topology,
        },
        "solver_domain": solver,
        "shape_validation": shape,
        "expected_bmw_shape_validation": expected_shape,
        "blocking_reasons": [
            *list(solver.get("errors") or []),
            *list(shape.get("errors") or []),
            *list(expected_shape.get("errors") or []),
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bff", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = verify(args.bff)
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
                "entry_index": report["source"]["entry_index"],
                "record_count": report["sdf"]["record_count"],
                "solver_scalar_count": report["solver_domain"]["solver_scalar_count"],
                "blocking_reasons": report["blocking_reasons"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
