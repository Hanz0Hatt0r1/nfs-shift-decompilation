"""Attach exact persistent typed-resource paths to a vehicle physics manifest.

This is a Process 3 resource/provenance join only.  It consumes the existing
``SHIFT.VehiclePhysicsResourceManifest/1`` exact entry identities plus the
existing ``SHIFT.TypedResourceClosure/1`` decoded outputs.  It never assigns
BODY semantics, participant identity, provider identity, or scheduling.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

PHYSICS_MANIFEST_FORMAT = "SHIFT.VehiclePhysicsResourceManifest/1"
TYPED_CLOSURE_FORMAT = "SHIFT.TypedResourceClosure/1"
PHYSICS_KINDS = ("cdf", "edf", "gdf", "sdf", "tbf", "bbf")


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _sha(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def attach_typed_physics_materializations(
    manifest: Mapping[str, Any],
    typed_closure: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the same manifest format with exact decoded file paths attached.

    A materialized path is admitted only when one typed-closure row matches the
    manifest resource ID, normalized retail path and decoded SHA-256, the row's
    extraction identity check is true, and the current file bytes still hash to
    the same decoded identity.
    """
    result = dict(manifest)
    blockers = [str(value) for value in manifest.get("blocking_reasons") or []]

    if manifest.get("format") != PHYSICS_MANIFEST_FORMAT:
        blockers.append("vehicle-physics-manifest:invalid-format")
    if manifest.get("ready") is not True:
        blockers.append("vehicle-physics-manifest:not-ready")

    if typed_closure.get("format") != TYPED_CLOSURE_FORMAT:
        blockers.append("typed-resource-closure:invalid-format")
    if typed_closure.get("ready") is not True:
        blockers.append("typed-resource-closure:not-ready")
        blockers.extend(
            f"typed-resource-closure:{reason}"
            for reason in typed_closure.get("blocking_reasons") or []
        )

    buckets: dict[str, list[Mapping[str, Any]]] = {}
    for raw in typed_closure.get("resources") or []:
        if not isinstance(raw, Mapping):
            continue
        resource_id = str(raw.get("resource_id") or "").strip()
        if not resource_id:
            continue
        buckets.setdefault(resource_id, []).append(raw)

    raw_entries = manifest.get("entries") or {}
    if not isinstance(raw_entries, Mapping):
        blockers.append("vehicle-physics-manifest:entries-missing")
        raw_entries = {}

    entries: dict[str, dict[str, Any]] = {}
    materialized_count = 0
    for kind in PHYSICS_KINDS:
        raw_entry = raw_entries.get(kind)
        if not isinstance(raw_entry, Mapping):
            blockers.append(f"{kind}:manifest-entry-missing")
            continue
        entry = dict(raw_entry)
        entries[kind] = entry

        resource_id = str(entry.get("resource_id") or "").strip()
        expected_path = _norm(entry.get("path"))
        expected_sha = _sha(entry.get("decoded_sha256"))
        if not resource_id:
            blockers.append(f"{kind}:resource-id-missing")
            continue
        if not expected_path:
            blockers.append(f"{kind}:path-missing")
            continue
        if expected_sha is None:
            blockers.append(f"{kind}:decoded-sha256-missing-or-invalid")
            continue

        hits = buckets.get(resource_id, [])
        if len(hits) != 1:
            blockers.append(
                f"{kind}:typed-resource-"
                + ("missing" if not hits else f"ambiguous:{len(hits)}")
                + f":{resource_id}"
            )
            continue

        typed_row = hits[0]
        if _norm(typed_row.get("path")) != expected_path:
            blockers.append(f"{kind}:typed-resource-path-mismatch")
        if typed_row.get("identity_match") is not True:
            blockers.append(f"{kind}:typed-resource-identity-mismatch")

        typed_sha = _sha(typed_row.get("decoded_sha256"))
        if typed_sha is None:
            blockers.append(f"{kind}:typed-resource-decoded-sha256-missing-or-invalid")
        elif typed_sha != expected_sha:
            blockers.append(f"{kind}:typed-resource-decoded-sha256-mismatch")

        catalog_sha = _sha(typed_row.get("catalog_decoded_sha256"))
        if catalog_sha is not None and catalog_sha != expected_sha:
            blockers.append(f"{kind}:typed-resource-catalog-sha256-mismatch")

        output = str(typed_row.get("output") or "").strip()
        if not output:
            blockers.append(f"{kind}:typed-resource-output-missing")
            continue
        path = Path(output).expanduser()
        if not path.is_file():
            blockers.append(f"{kind}:typed-resource-file-missing:{path}")
            continue

        actual_sha = _file_sha256(path)
        if actual_sha != expected_sha:
            blockers.append(f"{kind}:typed-resource-file-sha256-mismatch")
            continue
        if typed_sha is not None and actual_sha != typed_sha:
            blockers.append(f"{kind}:typed-resource-file-vs-closure-sha256-mismatch")
            continue

        # Do not attach a path if another exact-identity check for this row
        # already failed.  Presence must never conceal an identity mismatch.
        kind_prefix = f"{kind}:"
        if any(reason.startswith(kind_prefix) for reason in blockers):
            continue

        entry["materialized_path"] = str(path)
        entry["materialized_sha256"] = actual_sha
        entry["materialization_source"] = TYPED_CLOSURE_FORMAT
        materialized_count += 1

    result["entries"] = entries
    blockers = list(dict.fromkeys(blockers))
    ready = not blockers and materialized_count == len(PHYSICS_KINDS)
    result["status"] = "ready" if ready else "blocked"
    result["ready"] = ready
    result["blocking_reasons"] = blockers
    result["materialized_resource_count"] = materialized_count
    result["materialized_resources_ready"] = ready

    source = dict(result.get("source") or {})
    source["typed_resource_closure_format"] = typed_closure.get("format")
    result["source"] = source

    boundary = dict(result.get("boundary") or {})
    boundary.update({
        "typed_resource_materialization_evaluated": True,
        "typed_resource_materialization_join": (
            "exact-resource-id/path/decoded-sha256/file-sha256"
        ),
        "typed_resource_materialized_paths_ready": ready,
        "basename_fallback_used": False,
        "resource_similarity_used": False,
        "body_semantics_claimed": False,
        "participant_identity_claimed": False,
        "runtime_provider_identity_claimed": False,
        "runtime_schedule_claimed": False,
    })
    result["boundary"] = boundary
    return result
