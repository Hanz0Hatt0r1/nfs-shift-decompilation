"""Build the real BMW M3 paint MaterialBinding directly from a BFF archive."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

from bmw_m3_paint_contract import validate_material_binding
from material_linker import link_material
from meb_format import mesh_summary, read_meb
from resource_formats import parse_bmt_material

FORMAT = "SHIFT.BMWPaintPipelineResult/1"
DEFAULT_BMT = "vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt"
DEFAULT_MEB = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"


def _norm(value: str | None) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _find_exact(entries: Iterable[Any], target: str) -> list[Any]:
    wanted = _norm(target)
    return [e for e in entries if _norm(getattr(e, "path", None)) == wanted]


def _find_basename(entries: Iterable[Any], target: str) -> list[Any]:
    wanted = Path(_norm(target)).name
    return [e for e in entries if Path(_norm(getattr(e, "path", None))).name == wanted]


def _select_shader(entries: Iterable[Any], shader_ref: str) -> tuple[Any | None, str]:
    exact = _find_exact(entries, shader_ref)
    if len(exact) == 1:
        return exact[0], "exact"
    base = _find_basename(entries, shader_ref)
    if len(base) == 1:
        return base[0], "basename"
    return None, "ambiguous" if base else "missing"


def _fxo_candidates(entries: Iterable[Any], family: str) -> list[Any]:
    wanted = _norm(family).rsplit("/", 1)[-1]
    return [
        e
        for e in entries
        if _norm(getattr(e, "path", None)).endswith(".fxo")
        and wanted in Path(_norm(e.path)).stem
    ]


def build_bmw_paint_pipeline_result(
    archive_path: str | Path,
    *,
    bmt_path: str = DEFAULT_BMT,
    meb_path: str = DEFAULT_MEB,
) -> dict[str, Any]:
    from shift_importer import BFF

    archive = Path(archive_path)
    with BFF(archive) as bff:
        bmt_matches = _find_exact(bff.entries, bmt_path)
        if len(bmt_matches) == 1:
            bmt_entry = bmt_matches[0]
            bmt_resolution = "exact"
        else:
            base = _find_basename(bff.entries, bmt_path)
            if len(base) != 1:
                raise ValueError(f"BMW paint BMT must resolve uniquely: {bmt_path}")
            bmt_entry = base[0]
            bmt_resolution = "basename"

        bmt_bytes = bff.extract_entry(bmt_entry, type2="lzx")
        parsed = parse_bmt_material(bmt_bytes)
        material = parsed.get("material") or {}

        shader_ref = str(material.get("shader") or "")
        shader_entry, shader_resolution = _select_shader(bff.entries, shader_ref)
        if shader_entry is None:
            raise ValueError(f"BMW paint shader must resolve uniquely: {shader_ref}")
        fx_bytes = bff.extract_entry(shader_entry, type2="lzx")

        meb_matches = _find_exact(bff.entries, meb_path)
        if len(meb_matches) == 1:
            meb_entry = meb_matches[0]
        else:
            base = _find_basename(bff.entries, meb_path)
            if len(base) != 1:
                raise ValueError(f"BMW golden MEB must resolve uniquely: {meb_path}")
            meb_entry = base[0]
        meb_bytes = bff.extract_entry(meb_entry, type2="lzx")
        mesh = read_meb(meb_bytes)

        vertex_properties = [
            str(x.get("id"))
            for x in getattr(mesh, "property_layouts", [])
            if isinstance(x, dict) and x.get("id") is not None
        ]

        fxo_entries = _fxo_candidates(bff.entries, Path(shader_ref).stem or "bodywork")
        fxo_candidates = [
            (entry.path, bff.extract_entry(entry, type2="lzx"))
            for entry in fxo_entries
        ]
        texture_paths = [
            str(e.path)
            for e in bff.entries
            if _norm(getattr(e, "path", None)).endswith(".dds")
        ]

        binding = link_material(
            material,
            fx_bytes,
            fxo_candidates=fxo_candidates,
            texture_paths=texture_paths,
            vertex_properties=vertex_properties,
        )
        contract = validate_material_binding({
            "shader": shader_ref,
            "specializations": (binding.get("selected_fxo") or {}).get("specialization_matched") or material.get("specializations") or [],
            "textures": binding.get("bindings") or [],
            "external_samplers": [
                b for b in binding.get("bindings") or []
                if b.get("binding") == "external-or-specialised"
            ],
        })

        ready = binding.get("selection_status") == "unique" and contract.get("ready") is True
        reasons = ([] if binding.get("selection_status") == "unique" else [f"shader-selection:{binding.get('selection_status')}"])
        reasons.extend(contract.get("blocking_reasons") or [])
        return {
            "format": FORMAT,
            "status": "ready" if ready else "blocked",
            "ready": ready,
            "blocking_reasons": list(dict.fromkeys(reasons)),
            "archive": {
                "path": str(archive),
                "size": archive.stat().st_size if archive.exists() else None,
                "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest() if archive.exists() else None,
            },
            "bmt": {
                "path": bmt_entry.path,
                "resolution": bmt_resolution,
                "resource_sha256": hashlib.sha256(bmt_bytes).hexdigest(),
                "material": material,
            },
            "shader": {
                "path": shader_entry.path,
                "resolution": shader_resolution,
                "resource_sha256": hashlib.sha256(fx_bytes).hexdigest(),
            },
            "meb": {
                "path": meb_entry.path,
                "resource_sha256": hashlib.sha256(meb_bytes).hexdigest(),
                "vertex_count": mesh.vertex_count,
                "triangle_count": mesh_summary(mesh).get("triangle_count"),
                "vertex_properties": vertex_properties,
            },
            "material_binding": binding,
            "paint_contract": contract,
        }