"""Validate the exact BMW M3 golden MEB -> paint-material asset relationship."""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.BMWM3PaintAssetContract/1"
PAINT_MTX = "vehicles/bmw_m3_e36/bmw_m3_e36_paint.mtx"
PAINT_BMT = "vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt"
EXPECTED_RESOURCE_SHA256 = "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"

def _norm(value: Any) -> str:
    return str(value or '').replace('\\','/').strip('/').lower()

def _alias(path: str) -> str:
    p=_norm(path)
    if p.endswith('.mtx'): return p[:-4]+'.bmt'
    if p.endswith('.bmt'): return p[:-4]+'.mtx'
    return p

def validate_bmw_paint_asset(golden: Mapping[str, Any]) -> dict[str, Any]:
    reasons=[]; checks=[]
    fmt=golden.get('format')
    if fmt!='SHIFT.BMWGoldenAssetManifest/1': reasons.append('golden:invalid-format')
    meta=golden.get('golden') or {}; mesh=golden.get('mesh') or {}
    resource=_norm(meta.get('resource'))
    if resource!='vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb': reasons.append('asset:resource-mismatch')
    if not meta.get('resource_sha256'): reasons.append('asset:resource-sha256-missing')
    elif str(meta.get('resource_sha256')).lower()!=EXPECTED_RESOURCE_SHA256: reasons.append('asset:resource-sha256-mismatch')
    color=(mesh.get('color460_descriptor') or {}).get('words')
    if color!=[4,6,0]: reasons.append('asset:color460-proof-missing')
    primitives=list(mesh.get('primitives') or [])
    paint=[(i,p) for i,p in enumerate(primitives) if _norm(p.get('material'))==PAINT_MTX]
    if not paint: reasons.append('asset:paint-material-missing')
    expected={1:(150,6294),2:(6444,7386)}
    for index, (first,count) in expected.items():
        row=next((p for i,p in paint if i==index),None)
        ok=bool(row and int(row.get('first_index',-1))==first and int(row.get('index_count',-1))==count)
        checks.append({'primitive_index':index,'material':PAINT_MTX,'first_index':row.get('first_index') if row else None,'index_count':row.get('index_count') if row else None,'status':'match' if ok else 'mismatch'})
        if not ok: reasons.append(f'asset:paint-primitive-mismatch:{index}')
    aliases={_alias(p.get('material')) for p in primitives if p.get('material')}
    if _alias(PAINT_BMT) not in aliases: reasons.append('asset:paint-bmt-alias-not-present')
    skin=mesh.get('skinning') or {}
    if skin.get('skinned') is not False: reasons.append('asset:skinning-not-static')
    ready=not reasons
    return {'format':FORMAT,'status':'match' if ready else 'mismatch','ready':ready,'blocking_reasons':list(dict.fromkeys(reasons)),'golden_identity':{'resource':meta.get('resource'),'resource_sha256':meta.get('resource_sha256')},'paint_material':{'mtx':PAINT_MTX,'bmt':PAINT_BMT,'bmt_mtx_alias_match':_alias(PAINT_BMT)==_alias(PAINT_MTX)},'checks':checks}