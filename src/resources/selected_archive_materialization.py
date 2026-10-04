"""Bridge an exact catalog/bootstrap archive occurrence to persistent BFF bytes."""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

from retail_archive_materialization import (
    ADMISSION_FORMAT,
    materialize_admitted_archive_role,
)

CATALOG_FORMAT = "SHIFT.OfflineResourceCatalog/1"
BOOTSTRAP_FORMAT = "SHIFT.SceneVehicleBootstrap/1"


def materialize_selected_archive(
    catalog: Mapping[str, object],
    bootstrap: Mapping[str, object],
    *,
    selected_key: str,
    role: str,
    output_dir: str | Path,
) -> dict[str, object] | None:
    """Materialize one exact selected archive when source provenance is present.

    Returns ``None`` only for legacy/test catalogs that predate archive rows or
    whose selected occurrence has incomplete source provenance. Real
    offline-pipeline catalogs always carry archive rows plus both ``source`` and
    ``source_kind`` and therefore take the strict path.
    """
    if catalog.get("format") != CATALOG_FORMAT:
        raise ValueError(f"catalog must be {CATALOG_FORMAT}")
    if bootstrap.get("format") != BOOTSTRAP_FORMAT:
        raise ValueError(f"bootstrap must be {BOOTSTRAP_FORMAT}")

    selected_archives = bootstrap.get("selected_archives") or {}
    selected = (
        selected_archives.get(selected_key)
        if isinstance(selected_archives, Mapping)
        else None
    )
    if not isinstance(selected, Mapping):
        raise ValueError(f"selected archive missing:{selected_key}")

    selected_id = str(selected.get("id") or "").strip()
    if not selected_id:
        raise ValueError(f"selected archive id missing:{selected_key}")

    raw_archives = catalog.get("archives")
    if raw_archives is None:
        return None
    if not isinstance(raw_archives, list):
        raise ValueError("catalog archives must be a list")

    hits = [
        row
        for row in raw_archives
        if isinstance(row, Mapping) and str(row.get("id") or "") == selected_id
    ]
    if len(hits) != 1:
        raise ValueError(
            "selected catalog archive occurrence "
            + ("missing" if not hits else f"ambiguous:{len(hits)}")
        )
    occurrence = dict(hits[0])

    # Older synthetic fixtures predate archive source provenance. Keep direct
    # unit-level callers compatible; real pipeline catalogs always have both.
    if not occurrence.get("source") or not occurrence.get("source_kind"):
        return None

    for field in ("archive_name", "sha256"):
        if str(selected.get(field) or "").casefold() != str(occurrence.get(field) or "").casefold():
            raise ValueError(f"selected/catalog {field} mismatch")

    admission = {
        "format": ADMISSION_FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "roles": {
            role: {
                "role": role,
                "ready": True,
                "expected_identity": {
                    "archive_name": occurrence.get("archive_name"),
                    "sha256": occurrence.get("sha256"),
                },
                "admitted_occurrence": occurrence,
            },
        },
    }
    report = materialize_admitted_archive_role(
        admission,
        role=role,
        output_dir=output_dir,
    )
    boundary = dict(report.get("boundary") or {})
    boundary.update({
        "catalog_selected_occurrence_join_required": True,
        "canonical_retail_identity_claimed_here": False,
        "canonical_retail_identity_is_separate_admission_gate": True,
    })
    report["boundary"] = boundary
    return report
