"""Materialize the renderer IR directly from offline SHIFT BFF/ZIP inputs.

This is an orchestration wrapper around the existing universal importer.  It
adds ZIP/directory corpus handling and the IMB/IMX extensions required by the
SGB scene path, while deliberately treating the importer's legacy dependency
hints as diagnostics rather than identity/admission proof.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from argparse import Namespace
from pathlib import Path
from typing import Any, Sequence

from offline_resource_pipeline import materialize_bff_inputs
from shift_importer import cmd_build_ir

FORMAT = "SHIFT.OfflineSceneIRMaterialization/1"
SCENE_IR_EXTENSIONS = (
    ".meb",
    ".imb",
    ".imx",
    ".bmt",
    ".dds",
    ".fx",
    ".fxh",
    ".fxo",
    ".sgb",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage_archive(source: Path, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.symlink_to(source.resolve())
        return "symlink"
    except OSError:
        shutil.copy2(source, target)
        return "copy"


def build_scene_ir(
    inputs: Sequence[str | Path],
    output_dir: str | Path,
    *,
    extensions: Sequence[str] = SCENE_IR_EXTENSIONS,
    fail_fast: bool = False,
) -> dict[str, Any]:
    """Run the existing IR importer once over a materialized multi-BFF corpus."""
    normalized_exts = []
    for value in extensions:
        ext = str(value).lower()
        if not ext.startswith("."):
            ext = "." + ext
        if ext not in normalized_exts:
            normalized_exts.append(ext)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    staged_archives: list[dict[str, Any]] = []
    return_code = 1

    with materialize_bff_inputs(inputs) as materialized:
        with tempfile.TemporaryDirectory(prefix="shift-scene-ir-") as temporary:
            staging_root = Path(temporary)
            for index, archive in enumerate(materialized):
                target = staging_root / f"{index:04d}" / archive.path.name
                method = _stage_archive(archive.path, target)
                staged_archives.append({
                    "index": index,
                    "archive_name": archive.path.name,
                    "source": archive.source,
                    "source_member": archive.member,
                    "stage_method": method,
                })

            args = Namespace(
                input=str(staging_root),
                output=str(out),
                ext=list(normalized_exts),
                fail_fast=bool(fail_fast),
            )
            return_code = int(cmd_build_ir(args))

    manifest_path = out / "manifest.json"
    stats_path = out / "stats.json"
    blockers: list[str] = []
    if return_code != 0:
        blockers.append(f"universal-importer-exit:{return_code}")
    if not manifest_path.is_file():
        blockers.append("manifest-missing")
    if not stats_path.is_file():
        blockers.append("stats-missing")

    manifest: list[Any] = []
    stats: dict[str, Any] = {}
    if manifest_path.is_file():
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(value, list):
            manifest = value
        else:
            blockers.append("manifest-not-list")
    if stats_path.is_file():
        value = json.loads(stats_path.read_text(encoding="utf-8"))
        if isinstance(value, dict):
            stats = value
        else:
            blockers.append("stats-not-object")

    failed_rows = [
        row for row in manifest
        if isinstance(row, dict) and row.get("error")
    ]
    if failed_rows:
        blockers.append(f"manifest-resource-errors:{len(failed_rows)}")

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    artifacts: dict[str, dict[str, Any]] = {}
    for name, path in (("manifest", manifest_path), ("stats", stats_path)):
        if path.is_file():
            artifacts[name] = {
                "path": str(path),
                "sha256": _sha256(path),
            }

    report = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "inputs": [str(value) for value in inputs],
        "archive_count": len(staged_archives),
        "staged_archives": staged_archives,
        "extensions": normalized_exts,
        "manifest_resource_count": len(manifest),
        "manifest_error_count": len(failed_rows),
        "importer_stats": stats,
        "artifacts": artifacts,
        "boundary": {
            "universal_importer_reused": True,
            "zip_inputs_materialized_automatically": True,
            "imb_imx_included": ".imb" in normalized_exts and ".imx" in normalized_exts,
            "legacy_manifest_dependency_hints_are_admission_proof": False,
            "legacy_basename_resolution_is_admission_proof": False,
            "resource_identity_admission": "must-be-performed-by-exact-ir-closure",
            "unknown_format_heuristics_added": False,
        },
    }
    report_path = out / "scene_ir_materialization.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
