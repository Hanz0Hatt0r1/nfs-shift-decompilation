"""Verify the exact retail BMW M3 BFF intake before material extraction."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from shift_importer import BFF

FORMAT = "SHIFT.BMWBFFIntakeEvidence/1"
EXPECTED_SIZE = 18_934_688
TARGET_BMT = "vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt"
TARGET_MEB = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
EXPECTED_MEB_SHA256 = "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"
EXPECTED_MEB_SIZE = 300_764


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _exact_entries(archive: BFF, target: str):
    wanted = _norm(target)
    return [entry for entry in archive.entries if _norm(entry.path) == wanted]


def validate_bmw_bff(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    reasons: list[str] = []
    checks: list[dict[str, Any]] = []

    if not source.is_file():
        return {
            "format": FORMAT,
            "status": "blocked",
            "ready": False,
            "blocking_reasons": ["file:not-found"],
            "checks": [],
            "source": {"path": str(source)},
        }

    size = source.stat().st_size
    size_ok = size == EXPECTED_SIZE
    checks.append({"field": "archive_size", "expected": EXPECTED_SIZE, "observed": size, "status": "match" if size_ok else "mismatch"})
    if not size_ok:
        reasons.append("archive:size-mismatch")

    try:
        archive = BFF(source)
    except Exception as exc:
        reasons.append(f"archive:parse-error:{type(exc).__name__}:{exc}")
        return {
            "format": FORMAT,
            "status": "blocked",
            "ready": False,
            "blocking_reasons": list(dict.fromkeys(reasons)),
            "checks": checks,
            "source": {"path": str(source), "size": size},
        }

    try:
        for label, target, expected_sha, expected_size in (
            ("paint_bmt", TARGET_BMT, None, None),
            ("body_meb", TARGET_MEB, EXPECTED_MEB_SHA256, EXPECTED_MEB_SIZE),
        ):
            entries = _exact_entries(archive, target)
            entry_ok = len(entries) == 1
            checks.append({
                "field": label + "_entry_count",
                "expected": 1,
                "observed": len(entries),
                "status": "match" if entry_ok else "mismatch",
            })
            if not entry_ok:
                reasons.append(f"{label}:entry-count-mismatch")
                continue
            entry = entries[0]
            row = {
                "index": entry.index,
                "path": entry.path,
                "compressed_size": entry.compressed_size,
                "uncompressed_size": entry.uncompressed_size,
                "type": entry.type,
                "crc": entry.crc,
            }
            if expected_sha is not None:
                payload = archive.extract_entry(entry)
                digest = _sha256(payload)
                sha_ok = digest == expected_sha
                checks.append({
                    "field": label + "_sha256",
                    "expected": expected_sha,
                    "observed": digest,
                    "status": "match" if sha_ok else "mismatch",
                })
                checks.append({
                    "field": label + "_uncompressed_size",
                    "expected": expected_size,
                    "observed": len(payload),
                    "status": "match" if len(payload) == expected_size else "mismatch",
                })
                if not sha_ok:
                    reasons.append(f"{label}:sha256-mismatch")
                if len(payload) != expected_size:
                    reasons.append(f"{label}:size-mismatch")
            row["extracted_sha256"] = expected_sha if expected_sha is not None and not reasons else row.get("extracted_sha256")
            checks.append({"field": label + "_path", "expected": target, "observed": entry.path, "status": "match"})

    finally:
        archive.close()

    return {
        "format": FORMAT,
        "status": "ready" if not reasons else "blocked",
        "ready": not reasons,
        "blocking_reasons": list(dict.fromkeys(reasons)),
        "checks": checks,
        "source": {
            "path": str(source),
            "size": size,
            "magic": archive.magic.decode("latin-1", "replace") if 'archive' in locals() else None,
            "version": archive.version if 'archive' in locals() else None,
        },
        "targets": {
            "paint_bmt": TARGET_BMT,
            "body_meb": TARGET_MEB,
            "body_meb_sha256": EXPECTED_MEB_SHA256,
        },
    }
