"""Join the bootstrap-selected track SGB root to one exact IR raw payload.

This stage removes the manual SGB path from the offline native-scene handoff.
Identity is accepted only when the bootstrap root, catalog row and IR manifest
agree on selected archive, entry index, normalized resource path and decoded
SHA-256.  No basename or similar-path fallback is permitted.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.OfflineSceneRootIRJoin/1"
CATALOG_FORMAT = "SHIFT.OfflineResourceCatalog/1"
BOOTSTRAP_FORMAT = "SHIFT.SceneVehicleBootstrap/1"


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip().lower().lstrip("./")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_scene_root_ir_join(
    catalog: Mapping[str, Any],
    bootstrap: Mapping[str, Any],
    ir_root: str | Path,
) -> dict[str, Any]:
    if catalog.get("format") != CATALOG_FORMAT:
        raise ValueError(f"catalog must be {CATALOG_FORMAT}")
    if bootstrap.get("format") != BOOTSTRAP_FORMAT:
        raise ValueError(f"bootstrap must be {BOOTSTRAP_FORMAT}")

    blockers: list[str] = []
    if bootstrap.get("ready") is not True:
        blockers.append("bootstrap-not-ready")

    selected_archives = bootstrap.get("selected_archives") or {}
    selected = (
        selected_archives.get("track_visual")
        if isinstance(selected_archives, Mapping)
        else None
    )
    if not isinstance(selected, Mapping):
        blockers.append("selected-track-visual-archive-missing")
        selected = {}
    selected_archive_id = str(selected.get("id") or "")
    selected_archive_name = str(selected.get("archive_name") or "")
    if not selected_archive_id:
        blockers.append("selected-track-visual-archive-id-missing")
    if not selected_archive_name:
        blockers.append("selected-track-visual-archive-name-missing")

    roots = bootstrap.get("roots") or {}
    track_roots = roots.get("track_visual") if isinstance(roots, Mapping) else None
    root_id = (
        track_roots.get(".sgb")
        if isinstance(track_roots, Mapping)
        else None
    )
    if not isinstance(root_id, str) or not root_id:
        blockers.append("track-visual-sgb-root-missing")
        root_id = None

    resources = [
        row
        for row in (catalog.get("resources") or [])
        if isinstance(row, Mapping)
    ]
    catalog_hits = [row for row in resources if row.get("id") == root_id] if root_id else []
    catalog_row: Mapping[str, Any] | None = None
    if root_id:
        if len(catalog_hits) != 1:
            blockers.append(
                "catalog-sgb-root-"
                + ("missing" if not catalog_hits else f"ambiguous:{len(catalog_hits)}")
            )
        else:
            catalog_row = catalog_hits[0]

    if catalog_row is not None:
        if str(catalog_row.get("archive_id") or "") != selected_archive_id:
            blockers.append("catalog-root-selected-archive-id-mismatch")
        if (
            selected_archive_name
            and str(catalog_row.get("archive_name") or "").lower()
            != selected_archive_name.lower()
        ):
            blockers.append("catalog-root-selected-archive-name-mismatch")
        if str(catalog_row.get("extension") or "").lower() != ".sgb":
            blockers.append("catalog-root-not-sgb")

    root = Path(ir_root)
    manifest_path = root / "manifest.json"
    manifest: list[Mapping[str, Any]] = []
    if not manifest_path.is_file():
        blockers.append("ir-manifest-missing")
    else:
        try:
            value = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            blockers.append(f"ir-manifest-read-error:{type(exc).__name__}")
            value = None
        if isinstance(value, list):
            manifest = [
                row
                for row in value
                if isinstance(row, Mapping) and "error" not in row
            ]
        elif value is not None:
            blockers.append("ir-manifest-not-list")

    ir_row: Mapping[str, Any] | None = None
    raw_path: Path | None = None
    if catalog_row is not None and manifest:
        try:
            expected_index = int(catalog_row.get("index"))
        except (TypeError, ValueError):
            expected_index = -1
            blockers.append("catalog-root-entry-index-invalid")
        expected_path = _norm(
            catalog_row.get("normalized_path") or catalog_row.get("path")
        )
        structural_hits: list[Mapping[str, Any]] = []
        for row in manifest:
            try:
                row_index = int(row.get("entry_index"))
            except (TypeError, ValueError):
                continue
            if (
                str(row.get("archive") or "").lower()
                == selected_archive_name.lower()
                and row_index == expected_index
                and _norm(row.get("path")) == expected_path
            ):
                structural_hits.append(row)
        if len(structural_hits) != 1:
            blockers.append(
                "ir-sgb-root-"
                + (
                    "missing"
                    if not structural_hits
                    else f"ambiguous:{len(structural_hits)}"
                )
            )
        else:
            ir_row = structural_hits[0]
            ir_sha = str(ir_row.get("sha256") or "").lower()
            catalog_sha = str(catalog_row.get("decoded_sha256") or "").lower()
            if not ir_sha:
                blockers.append("ir-sgb-root-sha256-missing")
            if catalog_sha and ir_sha and catalog_sha != ir_sha:
                blockers.append("ir-sgb-root-decoded-sha256-mismatch")

            raw_relative = ir_row.get("raw")
            if not raw_relative:
                blockers.append("ir-sgb-root-raw-reference-missing")
            else:
                raw_path = root / str(raw_relative)
                if not raw_path.is_file():
                    blockers.append("ir-sgb-root-raw-payload-missing")
                else:
                    raw_sha = _sha256(raw_path)
                    if ir_sha and raw_sha != ir_sha:
                        blockers.append("ir-sgb-root-raw-sha256-mismatch")
                    if catalog_sha and raw_sha != catalog_sha:
                        blockers.append("catalog-sgb-root-raw-sha256-mismatch")

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "root_resource_id": root_id,
        "selected_archive": {
            "id": selected_archive_id or None,
            "archive_name": selected_archive_name or None,
        },
        "catalog_resource": (
            {
                "id": catalog_row.get("id"),
                "archive_id": catalog_row.get("archive_id"),
                "archive_name": catalog_row.get("archive_name"),
                "index": catalog_row.get("index"),
                "path": catalog_row.get("path"),
                "normalized_path": catalog_row.get("normalized_path"),
                "decoded_sha256": catalog_row.get("decoded_sha256"),
            }
            if catalog_row is not None
            else None
        ),
        "ir_resource": (
            {
                "archive": ir_row.get("archive"),
                "entry_index": ir_row.get("entry_index"),
                "path": ir_row.get("path"),
                "sha256": ir_row.get("sha256"),
                "raw": ir_row.get("raw"),
                "output": ir_row.get("output"),
            }
            if ir_row is not None
            else None
        ),
        "raw_sgb_path": str(raw_path) if raw_path is not None else None,
        "boundary": {
            "bootstrap_root_identity": "selected archive id + exact catalog resource id",
            "ir_identity": "archive filename + entry index + normalized path + decoded SHA-256",
            "raw_payload_sha256_revalidated": True,
            "basename_fallback": False,
            "similar_path_fallback": False,
            "first_duplicate_wins": False,
            "missing_resource_synthesis": False,
        },
    }
