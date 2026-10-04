"""Persist an exact admitted retail archive for downstream native/proof consumers.

This module is resource/provenance infrastructure only.  It consumes one role
from ``SHIFT.RetailArchiveIdentityAdmission/1`` and reconstructs that exact BFF
from its original BFF/ZIP/directory source without basename fallback or archive
order selection.  The resulting bytes must preserve the already-admitted retail
SHA-256 identity.
"""
from __future__ import annotations

import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, BinaryIO, Mapping

ADMISSION_FORMAT = "SHIFT.RetailArchiveIdentityAdmission/1"
FORMAT = "SHIFT.RetailArchiveMaterialization/1"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_verified_stream(
    source: BinaryIO,
    target: Path,
    *,
    expected_sha256: str,
    expected_bytes: int | None,
) -> tuple[str, int]:
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    total = 0
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=target.parent,
        prefix=target.name + ".",
        suffix=".tmp",
        delete=False,
    ) as temp:
        temp_path = Path(temp.name)
        try:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                temp.write(chunk)
                digest.update(chunk)
                total += len(chunk)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    actual_sha256 = digest.hexdigest()
    if actual_sha256.casefold() != expected_sha256.casefold():
        temp_path.unlink(missing_ok=True)
        raise ValueError(
            "retail archive SHA-256 drift: "
            f"{actual_sha256} != {expected_sha256}"
        )
    if expected_bytes is not None and total != expected_bytes:
        temp_path.unlink(missing_ok=True)
        raise ValueError(
            f"retail archive size drift: {total} != {expected_bytes}"
        )
    temp_path.replace(target)
    return actual_sha256, total


def _directory_candidate(
    source: Path,
    *,
    archive_name: str,
    expected_sha256: str,
) -> Path:
    hits: list[Path] = []
    for candidate in sorted(source.rglob("*.bff")):
        if candidate.name.casefold() != archive_name.casefold():
            continue
        if _sha256_file(candidate).casefold() == expected_sha256.casefold():
            hits.append(candidate)
    if len(hits) != 1:
        raise ValueError(
            "directory exact archive occurrence "
            + ("missing" if not hits else f"ambiguous:{len(hits)}")
        )
    return hits[0]


def materialize_admitted_archive_role(
    admission: Mapping[str, Any],
    *,
    role: str,
    output_dir: str | Path,
) -> dict[str, Any]:
    blockers: list[str] = []
    if admission.get("format") != ADMISSION_FORMAT:
        blockers.append("admission:invalid-format")
    if admission.get("ready") is not True:
        blockers.append("admission:not-ready")

    roles = admission.get("roles") or {}
    role_row = roles.get(role) if isinstance(roles, Mapping) else None
    if not isinstance(role_row, Mapping):
        blockers.append(f"role:{role}:missing")
        role_row = {}
    elif role_row.get("ready") is not True:
        blockers.append(f"role:{role}:not-ready")

    occurrence = role_row.get("admitted_occurrence") or {}
    expected = role_row.get("expected_identity") or {}
    if not isinstance(occurrence, Mapping):
        occurrence = {}
        blockers.append(f"role:{role}:admitted-occurrence-missing")
    if not isinstance(expected, Mapping):
        expected = {}
        blockers.append(f"role:{role}:expected-identity-missing")

    archive_name = str(expected.get("archive_name") or "").strip()
    expected_sha256 = str(expected.get("sha256") or "").strip().lower()
    occurrence_name = str(occurrence.get("archive_name") or "").strip()
    occurrence_sha256 = str(occurrence.get("sha256") or "").strip().lower()
    if not archive_name or Path(archive_name).name != archive_name or not archive_name.lower().endswith(".bff"):
        blockers.append(f"role:{role}:archive-name-invalid")
    if len(expected_sha256) != 64:
        blockers.append(f"role:{role}:expected-sha256-invalid")
    if occurrence_name.casefold() != archive_name.casefold():
        blockers.append(f"role:{role}:occurrence-name-mismatch")
    if occurrence_sha256 != expected_sha256:
        blockers.append(f"role:{role}:occurrence-sha256-mismatch")

    source_kind = str(occurrence.get("source_kind") or "")
    source_text = str(occurrence.get("source") or "").strip()
    source_member = occurrence.get("source_member")
    expected_bytes_raw = occurrence.get("bytes")
    try:
        expected_bytes = int(expected_bytes_raw) if expected_bytes_raw is not None else None
    except (TypeError, ValueError):
        expected_bytes = None
        blockers.append(f"role:{role}:occurrence-bytes-invalid")
    if not source_text:
        blockers.append(f"role:{role}:source-missing")

    blockers = list(dict.fromkeys(blockers))
    if blockers:
        return {
            "format": FORMAT,
            "version": 1,
            "status": "blocked",
            "ready": False,
            "role": role,
            "blocking_reasons": blockers,
            "path": None,
            "sha256": None,
            "bytes": None,
            "boundary": {
                "exact_admitted_occurrence_required": True,
                "basename_fallback_used": False,
                "archive_order_used": False,
                "byte_identical_duplicate_collapse_used": False,
            },
        }

    source = Path(source_text).expanduser()
    target = Path(output_dir) / role / archive_name
    try:
        if source_kind == "zip-member":
            if not source.is_file() or source.suffix.lower() != ".zip":
                raise ValueError("ZIP source missing or invalid")
            if not isinstance(source_member, str) or not source_member:
                raise ValueError("exact ZIP member missing")
            with zipfile.ZipFile(source) as archive:
                try:
                    info = archive.getinfo(source_member)
                except KeyError as exc:
                    raise ValueError("exact ZIP member not found") from exc
                if info.is_dir():
                    raise ValueError("exact ZIP member is a directory")
                with archive.open(info, "r") as stream:
                    actual_sha256, actual_bytes = _copy_verified_stream(
                        stream,
                        target,
                        expected_sha256=expected_sha256,
                        expected_bytes=expected_bytes,
                    )
        elif source_kind == "bff":
            if source_member is not None:
                raise ValueError("direct BFF occurrence unexpectedly has source_member")
            if not source.is_file() or source.suffix.lower() != ".bff":
                raise ValueError("direct BFF source missing or invalid")
            with source.open("rb") as stream:
                actual_sha256, actual_bytes = _copy_verified_stream(
                    stream,
                    target,
                    expected_sha256=expected_sha256,
                    expected_bytes=expected_bytes,
                )
        elif source_kind == "directory-bff":
            if source_member is not None:
                raise ValueError("directory BFF occurrence unexpectedly has source_member")
            if not source.is_dir():
                raise ValueError("directory source missing or invalid")
            candidate = _directory_candidate(
                source,
                archive_name=archive_name,
                expected_sha256=expected_sha256,
            )
            with candidate.open("rb") as stream:
                actual_sha256, actual_bytes = _copy_verified_stream(
                    stream,
                    target,
                    expected_sha256=expected_sha256,
                    expected_bytes=expected_bytes,
                )
        else:
            raise ValueError(f"unsupported source_kind:{source_kind or '<missing>'}")
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        target.unlink(missing_ok=True)
        return {
            "format": FORMAT,
            "version": 1,
            "status": "blocked",
            "ready": False,
            "role": role,
            "blocking_reasons": [f"materialization:{type(exc).__name__}:{exc}"],
            "path": None,
            "sha256": None,
            "bytes": None,
            "boundary": {
                "exact_admitted_occurrence_required": True,
                "basename_fallback_used": False,
                "archive_order_used": False,
                "byte_identical_duplicate_collapse_used": False,
            },
        }

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "role": role,
        "blocking_reasons": [],
        "path": str(target),
        "sha256": actual_sha256,
        "bytes": actual_bytes,
        "source": {
            "kind": source_kind,
            "path": source_text,
            "member": source_member,
        },
        "boundary": {
            "exact_admitted_occurrence_required": True,
            "retail_sha256_reverified_after_materialization": True,
            "basename_fallback_used": False,
            "archive_order_used": False,
            "byte_identical_duplicate_collapse_used": False,
            "resource_semantics_claimed": False,
        },
    }
