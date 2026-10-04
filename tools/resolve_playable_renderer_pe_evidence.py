#!/usr/bin/env python3
"""Resolve exact PE renderer evidence from renderer report bundle(s).

This helper reuses the Phase 628 bundle index.  Selection authority is only the
embedded report format plus canonical JSON payload identity.  ZIP entry names,
archive order and occurrence frequency are never used to choose PE evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from index_silverstone_renderer_report_bundle import index_report_bundles

PE_FORMAT = "SHIFT.PEImageEvidence/1"
RESOLVED_STATUSES = {
    "exact-single-occurrence",
    "content-equivalent-multiple-occurrences",
}


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def resolve_renderer_pe_evidence_from_bundles(
    bundles: list[str | Path],
    *,
    output_dir: str | Path,
    max_json_bytes: int = 128 * 1024 * 1024,
) -> dict[str, Any]:
    """Return one canonical PE evidence artifact or fail closed.

    Unrelated bundle-index blockers do not change PE selection.  The existing
    renderer pipeline remains responsible for evaluating its other reports.
    """
    if not bundles:
        raise ValueError("renderer PE bundle resolution requires at least one bundle")

    out = Path(output_dir)
    manifest = index_report_bundles(
        list(bundles),
        output_dir=out,
        max_json_bytes=max_json_bytes,
    )
    rows = {
        str(row.get("key")): row
        for row in manifest.get("reports") or []
        if isinstance(row, Mapping)
    }
    row = rows.get("pe_evidence")
    if not isinstance(row, Mapping):
        raise ValueError("renderer bundle index has no PE evidence row")

    status = str(row.get("status") or "")
    if status == "missing":
        raise ValueError("renderer bundles contain no SHIFT.PEImageEvidence/1")
    if status == "ambiguous-distinct-payloads":
        count = row.get("distinct_canonical_payload_count")
        raise ValueError(
            "renderer bundles contain ambiguous distinct PE evidence payloads"
            + (f":{count}" if count is not None else "")
        )
    if status not in RESOLVED_STATUSES:
        raise ValueError(f"renderer PE evidence is not exactly resolved:{status}")

    normalized = manifest.get("normalized_outputs")
    normalized = normalized if isinstance(normalized, Mapping) else {}
    raw_path = normalized.get("pe_evidence")
    if not raw_path:
        raise ValueError("resolved renderer PE evidence has no normalized output")
    path = Path(str(raw_path)).resolve()
    if not path.is_file():
        raise ValueError(f"normalized renderer PE evidence is missing:{path}")

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("normalized renderer PE evidence is not a JSON object")
    if value.get("format") != PE_FORMAT:
        raise ValueError(
            f"normalized renderer PE evidence format mismatch:{value.get('format')!r}"
        )

    canonical_sha = _canonical_sha256(value)
    recorded_sha = str(row.get("canonical_sha256") or "")
    if not recorded_sha or canonical_sha != recorded_sha:
        raise ValueError("normalized renderer PE evidence canonical SHA-256 drift")

    index_path = (out / "silverstone_renderer_report_bundle_index.json").resolve()
    return {
        "status": "ready",
        "ready": True,
        "path": str(path),
        "format": PE_FORMAT,
        "canonical_sha256": canonical_sha,
        "occurrence_count": int(row.get("occurrence_count") or 0),
        "resolution_status": status,
        "bundle_index": str(index_path),
        "selection_key": (
            (manifest.get("boundary") or {}).get("selection_key")
            if isinstance(manifest.get("boundary"), Mapping)
            else None
        ),
        "boundary": {
            "filename_used_for_selection": False,
            "archive_order_used_for_selection": False,
            "frequency_used_for_selection": False,
            "content_equivalent_duplicates_are_one_payload_identity": True,
            "distinct_payloads_are_ambiguous": True,
            "pe_image_execution_claimed": False,
            "renderer_admission_claimed": False,
        },
    }
