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
    verify_bmw_m3_capture_structure,
    verify_bff_domain,
)
from sdf_solver_capture_runtime import compare_solver_captures
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



