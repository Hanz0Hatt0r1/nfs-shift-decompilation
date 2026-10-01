"""Deterministic portable bundle for full-mode SDF runtime probe evidence."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.SDFRuntimeProbeEvidenceBundle/1"
TIMELINE_FORMAT = "SHIFT.ConstraintRelationStateMutationTimelineCorrelation/1"
DEFAULT_ARCHIVE_NAME = "sdf_capture_evidence.zip"
MANIFEST_NAME = "evidence_manifest.json"

_CAPTURE_PATTERNS = (
    ("relation-state-mutation", "relation_state_mutation_events.jsonl"),
    ("relation-state-timeline", "relation_state_mutation_timeline.json"),
    ("frame-entry", "frame_entry_*.json"),
    ("builtin-solver-entry", "pre_solve_*.json"),
    ("provider-solver-entry", "provider_pre_*_*.json"),
    ("provider-solver-return", "provider_post_*_*.json"),
    ("scalar-reset", "scalar_reset_events.jsonl"),
    ("provider-reset-effects", "provider_reset_effects.jsonl"),
    ("post-solve", "post_solve_*.json"),
)

_REQUIRED_CAPTURE_FILES = (
    "relation_state_mutation_events.jsonl",
    "relation_state_mutation_timeline.json",
)

_FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("top-level JSON value must be an object")
    return payload


def _classify_capture_files(
    capture_directory: Path,
) -> list[tuple[str, Path]]:
    matched: dict[str, tuple[str, Path]] = {}
    for kind, pattern in _CAPTURE_PATTERNS:
        for path in sorted(capture_directory.glob(pattern)):
            if not path.is_file():
                continue
            matched[path.name] = (kind, path)
    return [matched[name] for name in sorted(matched)]


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=_FIXED_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def build_sdf_runtime_probe_evidence_bundle(
    capture_directory: str | Path,
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Package capture evidence without executable or host-local launcher files.

    The ZIP uses sorted entries, fixed timestamps, fixed permissions and stored
    payloads so identical capture bytes produce an identical archive.
    """
    root = Path(capture_directory).resolve()
    archive = (
        root / DEFAULT_ARCHIVE_NAME
        if output_path is None
        else Path(output_path).resolve()
    )

    errors: list[str] = []
    if not root.is_dir():
        errors.append(f"capture-directory-missing:{root}")

    rows: list[dict[str, Any]] = []
    payloads: list[tuple[str, bytes]] = []
    kind_counts: dict[str, int] = {}

    if root.is_dir():
        classified = _classify_capture_files(root)
        for kind, path in classified:
            data = path.read_bytes()
            payloads.append((path.name, data))
            rows.append(
                {
                    "path": path.name,
                    "kind": kind,
                    "size": len(data),
                    "sha256": _sha256(data),
                }
            )
            kind_counts[kind] = kind_counts.get(kind, 0) + 1

        present = {row["path"] for row in rows}
        for required in _REQUIRED_CAPTURE_FILES:
            if required not in present:
                errors.append(f"missing-required-capture-file:{required}")

    timeline_path = root / "relation_state_mutation_timeline.json"
    timeline_ready = False
    timeline_status = None
    timeline_error_count = None
    if timeline_path.is_file():
        try:
            timeline = _read_json_object(timeline_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(
                f"timeline-json-invalid:{type(exc).__name__}:{exc}"
            )
        else:
            if timeline.get("format") != TIMELINE_FORMAT:
                errors.append("timeline-format-mismatch")
            timeline_ready = timeline.get("ready") is True
            timeline_status = timeline.get("status")
            timeline_errors = timeline.get("errors")
            if isinstance(timeline_errors, list):
                timeline_error_count = len(timeline_errors)

    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not errors else "blocked",
        "ready": not errors,
        "capture_ready": timeline_ready,
        "capture_status": timeline_status,
        "capture_error_count": timeline_error_count,
        "file_count": len(rows),
        "files": rows,
        "kind_counts": {
            key: kind_counts[key]
            for key in sorted(kind_counts)
        },
        "archive_policy": {
            "entry_order": "lexicographic-path",
            "compression": "stored",
            "fixed_timestamp": "1980-01-01T00:00:00",
            "fixed_mode": "0644",
            "includes_executable": False,
            "includes_attach_script": False,
            "includes_probe_manifest": False,
            "includes_preflight_manifest": False,
        },
        "errors": errors,
    }
    manifest_bytes = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, mode="w") as bundle:
        bundle.writestr(_zip_info(MANIFEST_NAME), manifest_bytes)
        for name, data in payloads:
            bundle.writestr(_zip_info(name), data)

    archive_bytes = archive.read_bytes()
    return {
        **manifest,
        "archive": {
            "path": str(archive),
            "size": len(archive_bytes),
            "sha256": _sha256(archive_bytes),
            "manifest_path": MANIFEST_NAME,
        },
    }


__all__ = [
    "FORMAT",
    "TIMELINE_FORMAT",
    "DEFAULT_ARCHIVE_NAME",
    "MANIFEST_NAME",
    "build_sdf_runtime_probe_evidence_bundle",
]
