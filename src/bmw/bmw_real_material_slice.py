"""Build a real BMW M3 material/render slice directly from retail BFF data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from bmw_material_from_bff import TARGET_BMT, TARGET_MEB, build_real_bmw_material_binding
from bmw_material_slice_golden_gate import validate_bmw_material_slice_golden
from bmw_m3_paint_asset_contract import validate_bmw_paint_asset
from draw_packets import build_index, compile_material, norm_ref
from meb_format import mesh_summary, mesh_to_jsonable, read_meb
from renderer_resources import build_resource_index
from resource_formats import parse_bmt_material, parse_dds_metadata
from render_command import build_render_command
from vertex_layout import build_layout_from_summary
from shift_importer import BFF
from static_draw import build_static_draw_contract

FORMAT = "SHIFT.BMWMaterialSlice/1"

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _find_exact(rows, path: str, label: str):
    target=norm_ref(path)
    hits=[(a,e) for a,e in rows if norm_ref(e.path)==target]
    if not hits:
        raise ValueError(f'{label}: expected entry {path!r}, found 0')
    if len(hits)==1:
        return hits[0]
    digests=[]
    for archive,entry in hits:
        payload=archive.extract_entry(entry)
        digests.append((_sha256(payload),archive,entry))
    unique={digest for digest,_,_ in digests}
    if len(unique)!=1:
        detail=', '.join(
            f'{archive.path.name}:{entry.index}:{digest[:12]}'
            for digest,archive,entry in digests
        )
        raise ValueError(
            f'{label}: conflicting duplicate entry {path!r}: {detail}'
        )
    return hits[0]

def build_real_bmw_material_slice(
    bff_path: str | Path,
    golden_manifest_path: str | Path,
    *,
    primitive_index: int = 1,
    supplemental_bffs: Iterable[str | Path] = (),
    shader_source_file: str | Path | None = None,
    color_abi_report: str | Path | None = None,
) -> dict[str, Any]:
    golden=json.loads(Path(golden_manifest_path).read_text(encoding='utf-8'))
    color_abi = None
    if color_abi_report is not None:
        color_abi = json.loads(Path(color_abi_report).read_text(encoding="utf-8"))
        if not isinstance(color_abi, dict):
            raise ValueError("color ABI report must be a JSON object")
    reasons=[]
    primary=Path(bff_path)
    paths=[primary,*[Path(x) for x in supplemental_bffs]]
    archives=[]
    try:
        archives=[BFF(p) for p in paths]
        rows=[(a,e) for a in archives for e in a.entries]
        meb_archive,meb_entry=_find_exact(rows,TARGET_MEB,'mesh')
        meb_bytes=meb_archive.extract_entry(meb_entry)
        mesh=read_meb(meb_bytes)
        if primitive_index<0 or primitive_index>=len(mesh.primitives):
            raise IndexError(f'primitive index out of range: 0..{len(mesh.primitives)-1}')
        primitive=mesh.primitives[primitive_index]
        material_ref=norm_ref(primitive.material)
        if not material_ref.endswith('.mtx'):
            raise ValueError(
                f'material-slice: primitive material is not .mtx: {primitive.material}'
            )
        material_bmt=str(primitive.material)[:-4]+'.bmt'
        is_paint=material_ref == norm_ref(TARGET_BMT[:-4]+'.mtx')

        binding_report=build_real_bmw_material_binding(
            bff_path,
            supplemental_bffs=supplemental_bffs,
            shader_source_file=shader_source_file,
            material_bmt=material_bmt,
        )
        reasons.extend(binding_report.get('blocking_reasons') or [])
        asset_contract=validate_bmw_paint_asset(golden) if is_paint else None
        if asset_contract is not None:
            reasons.extend(asset_contract.get('blocking_reasons') or [])

        bmt_archive,bmt_entry=_find_exact(rows,material_bmt,'material')
        bmt_bytes=bmt_archive.extract_entry(bmt_entry)
        parsed=parse_bmt_material(bmt_bytes)
        material=parsed.get('material') or {}
        material_name=str(material.get('name') or '')
        expected_name=material_ref.rsplit('/',1)[-1][:-4]
        if material_name and material_name.lower()!=expected_name.lower():
            reasons.append('material-slice:bmt-name-mismatch')
        shader_ref=str(material.get('shader') or '')
        external_shader = Path(shader_source_file) if shader_source_file is not None else None
        if external_shader is not None:
            if not external_shader.is_file():
                raise FileNotFoundError(str(external_shader))
            expected_shader_name=norm_ref(shader_ref).rsplit('/',1)[-1]
            if norm_ref(external_shader.name) != expected_shader_name:
                raise ValueError(
                    f'shader-source: external basename {external_shader.name!r} '
                    f'does not match material reference {shader_ref!r}'
                )
            fx_bytes=external_shader.read_bytes()
            shader_record={'path':shader_ref,'archive':'external-file','sha256':_sha256(fx_bytes),'size':len(fx_bytes)}
        else:
            fx_archive,fx_entry=_find_shader(rows,shader_ref)
            fx_bytes=fx_archive.extract_entry(fx_entry)
            shader_record={'path':fx_entry.path,'archive':fx_archive.path.name,'sha256':_sha256(fx_bytes),'size':len(fx_bytes)}
        texture_records=[]
        for value in material.get('shaderparams',[]) or []:
            raw=value.get('value')
            vals=raw if isinstance(raw,list) else [raw]
            for ref in vals:
                if not isinstance(ref,str) or not norm_ref(ref).endswith('.dds'): continue
                hits=[(a,e) for a,e in rows if norm_ref(e.path)==norm_ref(ref)]
                if not hits:
                    reasons.append('material-slice:dds-resolution:'+norm_ref(ref)); continue
                if len(hits)>1:
                    payloads=[(_sha256(a.extract_entry(e)),a,e) for a,e in hits]
                    if len({digest for digest,_,_ in payloads})!=1:
                        reasons.append('material-slice:dds-conflict:'+norm_ref(ref)); continue
                a,e=hits[0]; data=a.extract_entry(e)
                texture_records.append({'path':e.path,'archive':a.path.name,'sha256':_sha256(data),'analysis':parse_dds_metadata(data)})
        dedup={norm_ref(x['path']):x for x in texture_records}
        texture_records=list(dedup.values())
        material_record={'path':bmt_entry.path,'archive':bmt_archive.path.name,'analysis':{'format':'SHIFT.BMT','material':material}}
        binding=binding_report['material_binding']
        material_map,all_base=build_index([material_record,*texture_records,shader_record])
        texture_map,_=build_index(texture_records)
        shader_map,_=build_index([shader_record])
        compiled_material=compile_material(material_record,primitive.material,material_map,all_base,texture_map,shader_map,meb_archive.path.name,binding)
        mesh_summary_data=mesh_summary(mesh)
        packet={
            'scene':{'archive':primary.name,'path':'bmw://golden'},
            'node':{'name':mesh.name,'type':'OBJECT','matrix':None},
            'mesh':{
                'ref':TARGET_MEB,
                'resolved':{'path':TARGET_MEB,'archive':meb_archive.path.name,'resource_sha256':_sha256(meb_bytes)},
                'vertex_count':mesh.vertex_count,
                'triangle_count':mesh.triangle_count,
                'vertex_layout':(
                    build_layout_from_summary(mesh_summary_data, color_abi_evidence=color_abi)
                    if color_abi is not None
                    else build_layout_from_summary(mesh_summary_data)
                ),
                'property_descriptors':mesh.property_descriptors,
                'skinning':mesh_summary_data.get('skinning') or {},
            },
            'submeshes':[{'index':primitive_index,'first_index':primitive.first_index,'index_count':primitive.index_count,'material_ref':primitive.material,'material':compiled_material}],
        }
        static_draw=build_static_draw_contract(packet)
        texture_bindings=[dict(x) for x in compiled_material.get('textures') or [] if x.get('binding_source')=='fxo-ctab']
        resources=build_resource_index(texture_records,texture_bindings)
        render_command=build_render_command(static_draw,resources)
        slice_preview = {
            'format': 'SHIFT.BMWMaterialSlice/1',
            'ready': False,
            'primitive_index': primitive_index,
            'material_ref': primitive.material,
            'golden_identity': golden.get('golden') or {},
            'mesh': packet['mesh'],
            'generic_material_gate': binding_report.get('generic_material_gate'),
            'paint_contract': binding_report.get('paint_contract'),
            'paint_shader_gate': binding_report.get('paint_shader_gate'),
            'static_draw': static_draw,
            'render_command': render_command,
        }
        slice_golden_gate = validate_bmw_material_slice_golden(
            golden,
            slice_preview,
            primitive_index=primitive_index,
        )
        reasons.extend(slice_golden_gate.get('blocking_reasons') or [])
        reasons.extend(compiled_material.get('blocking_reasons') or [])
        reasons.extend(static_draw.get('blocking_reasons') or [])
        reasons.extend(render_command.get('blocking_reasons') or [])
        ready=bool(
            binding_report.get('ready')
            and (asset_contract is None or asset_contract.get('ready'))
            and slice_golden_gate.get('ready')
            and static_draw.get('ready')
            and render_command.get('ready')
            and not reasons
        )
        return {
            'format':FORMAT,
            'source_format':'SHIFT.RealBMWMaterialSliceEvidence/1',
            'status':'ready' if ready else 'blocked',
            'ready':ready,
            'blocking_reasons':list(dict.fromkeys(reasons)),
            'primitive_index':primitive_index,
            'material_ref':primitive.material,
            'material_bmt':material_bmt,
            'golden_identity':golden.get('golden') or {},
            'asset_contract':asset_contract,
            'slice_golden_gate':slice_golden_gate,
            'material_binding':binding,
            'generic_material_gate':binding_report.get('generic_material_gate'),
            'paint_contract':binding_report.get('paint_contract'),
            'paint_shader_gate':binding_report.get('paint_shader_gate'),
            'material':compiled_material,
            'shader_selection':compiled_material.get('shader_selection') or {},
            'textures':compiled_material.get('textures') or [],
            'uniform_binding':compiled_material.get('shader_selection',{}).get('uniform_binding') if isinstance(compiled_material.get('shader_selection'),dict) else compiled_material.get('uniform_binding'),
            'mesh':mesh_to_jsonable(mesh),
            'packet':packet,
            'static_draw':static_draw,
            'render_command':render_command,
            'color_abi_evidence':color_abi,
            'resources':resources,
            'provenance':{
                **binding_report.get('provenance',{}),
                'mesh_entry':{
                    'archive':meb_archive.path.name,
                    'path':meb_entry.path,
                    'index':meb_entry.index,
                    'sha256':_sha256(meb_bytes),
                    'size':len(meb_bytes),
                },
                'primitive':{
                    'first_index':primitive.first_index,
                    'index_count':primitive.index_count,
                },
                'dds_sources':[
                    {
                        'archive':row['archive'],
                        'path':row['path'],
                        'sha256':row['sha256'],
                        'analysis':row['analysis'],
                    }
                    for row in texture_records
                ],
            },
            'texture_sources':[
                {
                    'archive':row['archive'],
                    'path':row['path'],
                    'sha256':row['sha256'],
                    'analysis':row['analysis'],
                }
                for row in texture_records
            ],
            'boundary':{'runtime_instance_attribution':'not-proven','raw_binaries_committed':False},
        }
    finally:
        for archive in archives: archive.close()

def _find_shader(rows, shader_ref: str):
    target=norm_ref(shader_ref)
    exact=[(a,e) for a,e in rows if norm_ref(e.path)==target]
    if exact:
        return _find_exact(exact,shader_ref,'shader-source')
    base=target.rsplit('/',1)[-1]
    hits=[(a,e) for a,e in rows if norm_ref(e.path).rsplit('/',1)[-1]==base]
    if not hits:
        raise ValueError(f'shader-source: expected {shader_ref!r}, found 0')
    digests=[]
    for archive,entry in hits:
        payload=archive.extract_entry(entry)
        digests.append((_sha256(payload),archive,entry))
    if len({digest for digest,_,_ in digests})!=1:
        raise ValueError(
            f'shader-source: conflicting basename matches for {shader_ref!r}'
        )
    return hits[0]
