"""Fail-closed selected retail archive admission for the playable Linux slice."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from retail_archive_identity import (
    RetailArchiveIdentity,
    track_archive_identity,
    vehicle_archive_identity,
)

FORMAT = "SHIFT.RetailArchiveIdentityAdmission/1"


def _catalog_archives(catalog: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        row
        for row in (catalog.get("archives") or [])
        if isinstance(row, Mapping)
    ]


def _exact_hits(
    catalog: Mapping[str, Any],
    identity: RetailArchiveIdentity,
) -> list[Mapping[str, Any]]:
    return [
        row
        for row in _catalog_archives(catalog)
        if str(row.get("archive_name") or "").casefold() == identity.archive_name.casefold()
        and str(row.get("sha256") or "").casefold() == identity.sha256.casefold()
    ]


def _admit_role(
    *,
    catalog: Mapping[str, Any],
    selected_archives: Mapping[str, Any],
    selected_key: str,
    role: str,
    identity: RetailArchiveIdentity | None,
    required: bool,
) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    if identity is None:
        return ({
            "role": role,
            "required": required,
            "ready": False,
            "expected_identity": None,
            "selected_archive": None,
            "catalog_exact_occurrences": 0,
        }, [f"retail-archive-identity-unavailable:{role}"] if required else [])

    selected = selected_archives.get(selected_key)
    selected_row = dict(selected) if isinstance(selected, Mapping) else None
    hits = _exact_hits(catalog, identity)

    if selected_row is None:
        if required:
            blockers.append(f"retail-archive-selected-missing:{role}")
    else:
        if str(selected_row.get("archive_name") or "").casefold() != identity.archive_name.casefold():
            blockers.append(
                f"retail-archive-name-mismatch:{role}:"
                f"{selected_row.get('archive_name')}!={identity.archive_name}"
            )
        if str(selected_row.get("sha256") or "").casefold() != identity.sha256.casefold():
            blockers.append(
                f"retail-archive-sha256-mismatch:{role}:"
                f"{selected_row.get('sha256')}!={identity.sha256}"
            )

    if len(hits) != 1:
        blockers.append(
            f"retail-archive-exact-occurrence-"
            + ("missing" if not hits else f"ambiguous:{len(hits)}")
            + f":{role}:{identity.archive_name}"
        )
    elif selected_row is not None and str(selected_row.get("id") or "") != str(hits[0].get("id") or ""):
        blockers.append(
            f"retail-archive-selected-occurrence-mismatch:{role}:"
            f"{selected_row.get('id')}!={hits[0].get('id')}"
        )

    ready = not blockers and selected_row is not None and len(hits) == 1
    occurrence = dict(hits[0]) if len(hits) == 1 else None
    return ({
        "role": role,
        "required": required,
        "ready": ready,
        "expected_identity": identity.as_dict(),
        "selected_archive": selected_row,
        "catalog_exact_occurrences": len(hits),
        "admitted_occurrence": occurrence,
    }, blockers)


def build_retail_archive_identity_admission(
    catalog: Mapping[str, Any],
    bootstrap: Mapping[str, Any],
    *,
    track: str,
    vehicle: str,
) -> dict[str, Any]:
    """Require exact current-target retail archive identity before native handoff."""
    selected = bootstrap.get("selected_archives") or {}
    if not isinstance(selected, Mapping):
        selected = {}

    requirements: Sequence[tuple[str, str, RetailArchiveIdentity | None, bool]] = (
        (
            "track_visual",
            "track_visual",
            track_archive_identity(track, "visual"),
            True,
        ),
        (
            "track_physics",
            "track_physics",
            track_archive_identity(track, "physics"),
            True,
        ),
        (
            "vehicle_primary",
            "vehicle",
            vehicle_archive_identity(vehicle, "primary"),
            True,
        ),
        (
            "vehicle_cockpit",
            "vehicle_cockpit",
            vehicle_archive_identity(vehicle, "cockpit"),
            True,
        ),
    )

    roles: dict[str, Any] = {}
    blockers: list[str] = []
    if bootstrap.get("ready") is not True:
        blockers.extend(
            "resource-bootstrap:" + str(reason)
            for reason in (bootstrap.get("blocking_reasons") or ["not-ready"])
        )

    for role, selected_key, identity, required in requirements:
        row, reasons = _admit_role(
            catalog=catalog,
            selected_archives=selected,
            selected_key=selected_key,
            role=role,
            identity=identity,
            required=required,
        )
        roles[role] = row
        blockers.extend(reasons)

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers and all(row.get("ready") is True for row in roles.values())
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "track": track,
        "vehicle": vehicle,
        "roles": roles,
        "blocking_reasons": blockers,
        "boundary": {
            "archive_basename_is_identity_proof": False,
            "archive_order_is_identity_proof": False,
            "retail_sha256_required": True,
            "unique_catalog_occurrence_required": True,
            "byte_identical_duplicate_collapse_allowed": False,
            "unknown_target_identity_fallback_allowed": False,
        },
    }
