"""Build a real BMW M3 MaterialBinding directly from retail BFF archives."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

from bmw_m3_paint_contract import validate_material_binding
from bmw_m3_paint_shader_gate import validate_bmw_paint_shader_gate
from material_linker import link_material
from meb_format import read_meb
from resource_formats import parse_bmt_material
from shift_importer import BFF

FORMAT = "SHIFT.RealBMWMaterialBindingEvidence/1"
TARGET_BMT = 'vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt'
TARGET_MEB = 'vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb'

def _norm(value: Any) -> str:
    return str(value or '').replace('\\','/').strip('/').lower()

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _archive_sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): digest.update(chunk)
    return digest.hexdigest()

def _entry_rows(archives: Iterable[BFF]) -> list[tuple[BFF, Any]]:
    rows=[]
    for archive in archives:
        rows.extend((archive, entry) for entry in archive.entries)
    return rows

def _find_exact(rows: list[tuple[BFF, Any]], path: str, *, label: str) -> tuple[BFF, Any]:
    target=_norm(path)
    hits=[(a,e) for a,e in rows if _norm(e.path)==target]
    if len(hits)!=1:
        raise ValueError(f'{label}: expected exactly one entry {path!r}, found {len(hits)}')
    return hits[0]

def _find_shader_source(rows: list[tuple[BFF, Any]], shader_ref: str) -> tuple[BFF, Any]:
    target=_norm(shader_ref)
    exact=[(a,e) for a,e in rows if _norm(e.path)==target]
    if len(exact)==1: return exact[0]
    base=target.rsplit('/',1)[-1]
    hits=[(a,e) for a,e in rows if _norm(e.path).rsplit('/',1)[-1]==base]
    if len(hits)!=1:
        raise ValueError(f'shader-source: expected one {shader_ref!r}, found {len(hits)} exact/basename matches')
    return hits[0]

def build_real_bmw_material_binding(bff_path: str | Path, *, supplemental_bffs: Iterable[str | Path] = ()) -> dict[str, Any]:
    primary=Path(bff_path)
    paths=[primary, *[Path(x) for x in supplemental_bffs]]
    if any(not p.is_file() for p in paths):
        missing=[str(p) for p in paths if not p.is_file()]
        raise FileNotFoundError(', '.join(missing))
    archive_objects: list[BFF]=[]
    try:
        archive_objects=[BFF(p) for p in paths]
        rows=_entry_rows(archive_objects)
        bff, bmt_entry=_find_exact(rows,TARGET_BMT,label='material')
        meb_archive, meb_entry=_find_exact(rows,TARGET_MEB,label='mesh')
        bmt_bytes=bff.extract_entry(bmt_entry)
        meb_bytes=meb_archive.extract_entry(meb_entry)
        parsed_bmt=parse_bmt_material(bmt_bytes)
        material=parsed_bmt.get('material') or {}
        mesh=read_meb(meb_bytes)
        shader_ref=str(material.get('shader') or '')
        if not shader_ref: raise ValueError('material:shader-reference-missing')
        fx_archive,fx_entry=_find_shader_source(rows,shader_ref)
        fx_bytes=fx_archive.extract_entry(fx_entry)
        fxo_rows=[(a,e) for a,e in rows if _norm(e.path).endswith('.fxo')]
        fxo_candidates=[(f'{a.path.name}::{e.path}',a.extract_entry(e)) for a,e in fxo_rows]
        dds_paths=sorted({_norm(e.path) for _,e in rows if _norm(e.path).endswith('.dds')})
        binding=link_material(material,fx_bytes,fxo_candidates=fxo_candidates,texture_paths=dds_paths,vertex_properties=mesh.vertex_properties)
        contract=validate_material_binding(binding)
        shader_gate=validate_bmw_paint_shader_gate(binding)
        reasons=list(contract.get('blocking_reasons') or [])+list(shader_gate.get('blocking_reasons') or [])
        ready=bool(binding.get('selection_status')=='unique' and contract.get('ready') and shader_gate.get('ready') and not reasons)
        return {
            'format':FORMAT,
            'status':'ready' if ready else 'blocked',
            'ready':ready,
            'blocking_reasons':list(dict.fromkeys(reasons)),
            'material_binding':binding,
            'paint_contract':contract,
            'paint_shader_gate':shader_gate,
            'provenance':{
                'primary_bff':{'path':str(primary),'sha256':_archive_sha256(primary),'size':primary.stat().st_size},
                'supplemental_bffs':[{'path':str(p),'sha256':_archive_sha256(p),'size':p.stat().st_size} for p in paths[1:]],
                'material_entry':{'archive':bff.path.name,'path':bmt_entry.path,'index':bmt_entry.index,'sha256':_sha256(bmt_bytes),'size':len(bmt_bytes)},
                'mesh_entry':{'archive':meb_archive.path.name,'path':meb_entry.path,'index':meb_entry.index,'sha256':_sha256(meb_bytes),'size':len(meb_bytes)},
                'shader_source_entry':{'archive':fx_archive.path.name,'path':fx_entry.path,'index':fx_entry.index,'sha256':_sha256(fx_bytes),'size':len(fx_bytes)},
                'fxo_candidate_count':len(fxo_candidates),
                'dds_path_count':len(dds_paths),
            },
            'boundary':{'runtime_instance_attribution':'not-proven','capture_authenticity':'not-applicable','raw_binaries_committed':False},
        }
    finally:
        for archive in archive_objects:
            archive.close()