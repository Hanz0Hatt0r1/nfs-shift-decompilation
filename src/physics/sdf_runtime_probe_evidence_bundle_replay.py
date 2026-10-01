"""Replay a verified portable SDF evidence bundle through Phase 637."""
from __future__ import annotations

import hashlib
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from relation_state_mutation_timeline_correlation_runtime import (
    analyze_relation_state_mutation_capture_directory,
)
from sdf_runtime_probe_evidence_bundle import MANIFEST_NAME
from sdf_runtime_probe_evidence_bundle_verify import (
    verify_sdf_runtime_probe_evidence_bundle,
)

FORMAT = "SHIFT.SDFRuntimeProbeEvidenceBundleReplay/1"
TIMELINE_NAME = "relation_state_mutation_timeline.json"


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replay_sdf_runtime_probe_evidence_bundle(
    archive_path: str | Path,
) -> dict[str, Any]:
    """Verify, safely materialize and recompute the embedded Phase 637 report."""
    archive = Path(archive_path).resolve()
    verification = verify_sdf_runtime_probe_evidence_bundle(archive)
    errors: list[str] = []

    if not verification["ready"]:
        errors.extend(
            f"verification:{error}"
            for error in verification["errors"]
        )
        return {
            "format": FORMAT,
            "version": 1,
            "status": "blocked",
            "ready": False,
            "package_ready": bool(verification["package_ready"]),
            "capture_ready": bool(verification["capture_ready"]),
            "evidence_ready": False,
            "verification_ready": False,
            "timeline_match": False,
            "archive_sha256": verification["archive"]["sha256"],
            "embedded_timeline_sha256": None,
            "recomputed_timeline_sha256": None,
            "summary": None,
            "errors": errors,
        }

    with zipfile.ZipFile(archive, "r") as bundle:
        manifest = json.loads(
            bundle.read(MANIFEST_NAME).decode("utf-8")
        )
        embedded_timeline = json.loads(
            bundle.read(TIMELINE_NAME).decode("utf-8")
        )
        evidence_paths = [
            row["path"]
            for row in manifest["files"]
        ]

        with tempfile.TemporaryDirectory(
            prefix="shift-sdf-evidence-replay-"
        ) as temp:
            root = Path(temp)
            for name in evidence_paths:
                (root / name).write_bytes(bundle.read(name))
            recomputed_timeline = (
                analyze_relation_state_mutation_capture_directory(root)
            )

    embedded_bytes = _canonical_json_bytes(embedded_timeline)
    recomputed_bytes = _canonical_json_bytes(recomputed_timeline)
    timeline_match = embedded_timeline == recomputed_timeline
    if not timeline_match:
        errors.append("embedded-timeline-replay-mismatch")

    package_ready = bool(verification["package_ready"])
    capture_ready = bool(verification["capture_ready"])
    recomputed_capture_ready = recomputed_timeline.get("ready") is True
    if capture_ready != recomputed_capture_ready:
        errors.append("verification-recomputed-readiness-mismatch")

    ready = not errors
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "package_ready": package_ready,
        "capture_ready": capture_ready,
        "evidence_ready": (
            ready
            and package_ready
            and capture_ready
            and bool(verification["evidence_ready"])
        ),
        "verification_ready": True,
        "timeline_match": timeline_match,
        "archive_sha256": verification["archive"]["sha256"],
        "embedded_timeline_sha256": _sha256(embedded_bytes),
        "recomputed_timeline_sha256": _sha256(recomputed_bytes),
        "summary": recomputed_timeline.get("summary"),
        "errors": errors,
    }


__all__ = [
    "FORMAT",
    "TIMELINE_NAME",
    "replay_sdf_runtime_probe_evidence_bundle",
]
