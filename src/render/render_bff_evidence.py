"""Generate evidence for the real BMW M3 split render/shader archives.

The report deliberately records hashes, counts, resource identities, sampler
contracts and linker selection results, but never writes raw BFF/FXO payloads.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from bmw_material_from_bff import TARGET_BMT, TARGET_MEB
from material_linker import link_material
from meb_format import read_meb, mesh_summary
from resource_formats import parse_bmt_material
from shift_importer import BFF


FORMAT = "SHIFT.BMWRenderBFFEvidence/1"
EXPECTED_PAINT_SAMPLERS = {
    "diffuseMap",
    "specularMap",
    "environmentMap",
    "sShadowMap_f1_0",
    "scratchControlMap",
}


def _norm(path: str) -> str:
    return str(path or "").replace("\\", "/").strip("/").lower()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _exact(entries: list[Any], path: str, label: str) -> Any:
    target = _norm(path)
    hits = [entry for entry in entries if _norm(entry.path) == target]
    if len(hits) != 1:
        raise ValueError(
            f"{label}: expected exactly one {path!r}, found {len(hits)}"
        )
    return hits[0]


def _archive_manifest(path: Path) -> dict[str, Any]:
    with BFF(path) as archive:
        entries = list(archive.entries)
        return {
            "path": str(path),
            "name": path.name,
            "sha256": _file_sha256(path),
            "size": path.stat().st_size,
            "entry_count": len(entries),
            "extension_counts": _extension_counts(entries),
        }


def _extension_counts(entries: list[Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for entry in entries:
        lower = _norm(entry.path)
        if "." not in lower.rsplit("/", 1)[-1]:
            key = "<none>"
        else:
            key = lower.rsplit(".", 1)[-1]
        result[key] = result.get(key, 0) + 1
    return dict(sorted(result.items()))


def _bodywork_inventory(render_bff: Path) -> dict[str, Any]:
    with BFF(render_bff) as archive:
        fx_entry = _exact(
            list(archive.entries),
            "render/shaders/bodywork.fx",
            "shader-source",
        )
        fx_bytes = archive.extract_entry(fx_entry)
        bodywork_fxo = [
            entry
            for entry in archive.entries
            if _norm(entry.path).startswith("render/shaders/cache/render_shaders_bodywork_")
            and _norm(entry.path).endswith(".fxo")
        ]
        candidates = []
        for entry in bodywork_fxo:
            data = archive.extract_entry(entry)
            from shader_ir import parse_shader_blobs

            for blob in parse_shader_blobs(data):
                if blob.stage != "pixel":
                    continue
                samplers = {
                    item["name"]
                    for item in blob.ctab_samplers
                }
                constants = sorted(
                    item["name"]
                    for item in blob.ctab_constants
                    if item.get("register_set") == 2
                )
                if not samplers.intersection(EXPECTED_PAINT_SAMPLERS):
                    continue
                candidates.append({
                    "file": entry.path,
                    "pixel_offset": blob.offset,
                    "pixel_end": blob.end,
                    "instruction_count": blob.instruction_count,
                    "samplers": sorted(
                        {
                            item["name"]: int(item["register"])
                            for item in blob.ctab_samplers
                        }.items()
                    ),
                    "sampler_score": len(samplers & EXPECTED_PAINT_SAMPLERS),
                    "material_constant_names": constants,
                    "pixel_sha256": _sha256(data[blob.offset:blob.end]),
                })
        candidates.sort(
            key=lambda row: (
                -int(row["sampler_score"]),
                -int(row["instruction_count"]),
                row["file"],
                int(row["pixel_offset"]),
            )
        )
        return {
            "fx_source": {
                "archive": render_bff.name,
                "path": fx_entry.path,
                "index": fx_entry.index,
                "sha256": _sha256(fx_bytes),
                "size": len(fx_bytes),
            },
            "bodywork_fxo_count": len(bodywork_fxo),
            "bodywork_pixel_program_count": len(candidates),
            "expected_paint_samplers": sorted(EXPECTED_PAINT_SAMPLERS),
            "full_paint_sampler_program_count": sum(
                int(row["sampler_score"]) == len(EXPECTED_PAINT_SAMPLERS)
                for row in candidates
            ),
            "full_sampler_candidates": [
                row
                for row in candidates
                if int(row["sampler_score"]) == len(EXPECTED_PAINT_SAMPLERS)
            ][:32],
        }


def build_evidence(
    primary: str | Path,
    render_bff: str | Path,
    *,
    supplemental_bffs: list[str | Path] | None = None,
) -> dict[str, Any]:
    primary_path = Path(primary)
    render_path = Path(render_bff)
    supplemental_paths = [Path(x) for x in (supplemental_bffs or [])]
    all_paths = [primary_path, render_path, *supplemental_paths]
    if any(not path.is_file() for path in all_paths):
        missing = [str(path) for path in all_paths if not path.is_file()]
        raise FileNotFoundError(", ".join(missing))

    with BFF(primary_path) as primary_archive:
        primary_entries = list(primary_archive.entries)
        bmt_entry = _exact(primary_entries, TARGET_BMT, "material")
        meb_entry = _exact(primary_entries, TARGET_MEB, "mesh")
        bmt_bytes = primary_archive.extract_entry(bmt_entry)
        meb_bytes = primary_archive.extract_entry(meb_entry)
        material = parse_bmt_material(bmt_bytes).get("material") or {}
        mesh = read_meb(meb_bytes)
        mesh_summary_data = mesh_summary(mesh)
        fxo_archive_counts = len(primary_entries)

    with BFF(render_path) as render_archive:
        fx_entries = [
            entry for entry in render_archive.entries
            if _norm(entry.path).endswith(".fx")
        ]
        fxo_entries = [
            entry for entry in render_archive.entries
            if _norm(entry.path).endswith(".fxo")
        ]

    shader_result = None
    try:
        with BFF(primary_path) as primary_archive, BFF(render_path) as render_archive:
            bmt_source = primary_archive.extract_entry(bmt_entry)
            fx_entry = _exact(
                list(render_archive.entries),
                str(material.get("shader") or "render/shaders/bodywork.fx"),
                "shader-source",
            )
            fx_bytes = render_archive.extract_entry(fx_entry)
            candidates = []
            for entry in render_archive.entries:
                if _norm(entry.path).endswith(".fxo"):
                    candidates.append(
                        (
                            f"{render_path.name}::{entry.path}",
                            render_archive.extract_entry(entry),
                        )
                    )
            dds_paths = sorted(
                _norm(entry.path)
                for entry in primary_archive.entries
                if _norm(entry.path).endswith(".dds")
            )
            shader_result = link_material(
                material,
                fx_bytes,
                fxo_candidates=candidates,
                texture_paths=dds_paths,
                vertex_properties=mesh.vertex_properties,
            )
            shader_result = {
                "status": shader_result.get("selection_status"),
                "selected_fxo": shader_result.get("selected_fxo"),
                "selected_permutation_identity": shader_result.get("permutation_identity"),
                "shader_pair_selection_status": (
                    shader_result.get("shader_pair") or {}
                ).get("selection_status"),
                "linked_shader_pair_present": shader_result.get("linked_shader_pair") is not None,
                "linked_shader_error": shader_result.get("linked_shader_error"),
                "unresolved_textures": shader_result.get("unresolved_textures") or [],
            }
    except Exception as exc:
        shader_result = {
            "status": "probe-error",
            "error": f"{type(exc).__name__}: {exc}",
        }

    return {
        "format": FORMAT,
        "status": "observed",
        "archives": [
            _archive_manifest(path)
            for path in all_paths
        ],
        "targets": {
            "bmt": {
                "path": TARGET_BMT,
                "archive": primary_path.name,
                "entry_index": bmt_entry.index,
                "sha256": _sha256(bmt_bytes),
                "size": len(bmt_bytes),
                "material_name": material.get("name"),
                "shader": material.get("shader"),
                "shaderparams": [
                    {
                        "name": row.get("name"),
                        "type": row.get("type") or row.get("resource_type"),
                        "value": row.get("value"),
                    }
                    for row in material.get("shaderparams", []) or []
                    if row.get("name")
                ],
            },
            "meb": {
                "path": TARGET_MEB,
                "archive": primary_path.name,
                "entry_index": meb_entry.index,
                "sha256": _sha256(meb_bytes),
                "size": len(meb_bytes),
                "name": mesh.name,
                "vertex_count": mesh.vertex_count,
                "triangle_count": mesh.triangle_count,
                "vertex_properties": list(mesh.vertex_properties),
                "summary": mesh_summary_data,
            },
        },
        "render_archive": {
            "fx_count": len(fx_entries),
            "fxo_count": len(fxo_entries),
            "bodywork": _bodywork_inventory(render_path),
        },
        "shader_probe": shader_result,
        "boundary": {
            "raw_binaries_committed": False,
            "runtime_draw_identity": "not-supplied",
            "environment_cube_identity": "not-supplied",
            "shadow_map_identity": "not-supplied",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build evidence for BMW M3 BMT/MEB plus RENDER.bff shader inputs"
    )
    parser.add_argument("primary", type=Path)
    parser.add_argument("render_bff", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--supplemental-bff", action="append", default=[])
    args = parser.parse_args(argv)
    report = build_evidence(
        args.primary,
        args.render_bff,
        supplemental_bffs=args.supplemental_bff,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "bmt": report["targets"]["bmt"]["path"],
        "meb_vertex_count": report["targets"]["meb"]["vertex_count"],
        "meb_triangle_count": report["targets"]["meb"]["triangle_count"],
        "render_fxo_count": report["render_archive"]["fxo_count"],
        "bodywork_fxo_count": report["render_archive"]["bodywork"]["bodywork_fxo_count"],
        "full_paint_sampler_program_count": report["render_archive"]["bodywork"]["full_paint_sampler_program_count"],
        "shader_selection_status": report["shader_probe"].get("status"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
