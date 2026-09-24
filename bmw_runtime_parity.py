"""Validate shader constants and D3D9 declaration parity for an exact BMW runtime join."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping

from bmw_runtime_shader_join import join_runtime_shader
from d3d9_declaration_instance import decode_d3d9_declaration_records

FORMAT = "SHIFT.BMWRuntimeParity/1"

TYPE_BY_PROPERTY = {
    '130': 1, '131': 1, '132': 1, '133': 1, '134': 1,
    '200': 2, '220': 2, '230': 2, '231': 2, '232': 2, '233': 2, '234': 2,
    '240': 2, '250': 2, '310': 3, '460': 4, '580': 5,
}
USAGE_ORDINAL_BY_PROPERTY = {
    '200': 0, '310': 1, '220': 2, '240': 4, '250': 5, '460': 6, '580': 8,
}

def _stage_constants(identity: Mapping[str, Any], stage: str) -> set[int]:
    rows = ((identity.get('payload') or {}).get(stage) or {}).get('constants') or []
    return {int(x) for x in rows}

def _constant_requirements(material_slice: Mapping[str, Any]) -> list[dict[str, Any]]:
    binding = material_slice.get('uniform_binding') or ((material_slice.get('material') or {}).get('uniform_binding')) or {}
    out=[]
    for row in binding.get('bindings') or []:
        if row.get('register_set') != 2 or row.get('register_index') is None:
            continue
        start=int(row['register_index']); count=max(1,int(row.get('register_count') or 1))
        stage=str(row.get('stage') or 'pixel').lower()
        out.append({'name':row.get('name'),'stage':stage,'register_index':start,'register_count':count,'registers':list(range(start,start+count)),'value':row.get('value')})
    return out

def _declaration_expectations(material_slice: Mapping[str, Any]) -> list[dict[str, Any]]:
    mesh=material_slice.get('mesh') or {}
    layout=((mesh.get('vertex_layout') or {}).get('attributes') if isinstance(mesh.get('vertex_layout'), Mapping) else None) or []
    out=[]
    for row in layout:
        pid=str(row.get('property_id'))
        if pid not in TYPE_BY_PROPERTY or row.get('usage') is None:
            continue
        ordinal=USAGE_ORDINAL_BY_PROPERTY.get(pid)
        if ordinal is None:
            continue
        out.append({'property_id':pid,'type':TYPE_BY_PROPERTY[pid],'usage_ordinal':ordinal,'usage_index':int(row.get('usage_index',0)),'name':row.get('name')})
    return out

def validate_runtime_parity(material_slice: Mapping[str, Any], runtime_report: Mapping[str, Any], *, usage_map: Mapping[int,int] | None = None, require_constant_values: bool = False) -> dict[str, Any]:
    join=join_runtime_shader(material_slice,runtime_report)
    reasons=list(join.get('blocking_reasons') or [])
    if not join.get('matched_frame_count'):
        return {'format':FORMAT,'status':'not-found','ready':False,'blocking_reasons':list(dict.fromkeys(reasons)),'shader_join':join,'constant_parity':{'status':'not-proven'},'declaration_parity':{'status':'not-proven'}}
    frame=join['candidate_frames'][0]
    runtime_frame=next((f for f in runtime_report.get('frames') or [] if f.get('frame')==frame.get('frame')), None) or {}
    identity=runtime_frame.get('shader_permutation_identity') or {}

    constant_rows=_constant_requirements(material_slice)
    constant_checks=[]
    for req in constant_rows:
        available=_stage_constants(identity, req['stage'])
        missing=[r for r in req['registers'] if r not in available]
        constant_checks.append({**req,'missing_registers':missing,'status':'match' if not missing else 'mismatch'})
        if missing: reasons.append(f"constant:{req['stage']}:{req['name'] or req['register_index']}:missing")
    constant_status='match' if not any(x['status']=='mismatch' for x in constant_checks) else 'mismatch'
    constant_value_checks = []
    writes_by_stage: dict[str, dict[int, list[float]]] = {'vertex': {}, 'pixel': {}}
    for write in runtime_frame.get('constant_writes') or []:
        stage = str(write.get('stage') or '').lower()
        start = write.get('start_register')
        values = write.get('values') or []
        count = int(write.get('vector4f_count') or 0)
        if stage not in writes_by_stage or not isinstance(start, int) or count <= 0:
            continue
        for offset in range(count):
            chunk = [float(x) for x in values[offset * 4:(offset + 1) * 4]]
            if len(chunk) == 4:
                writes_by_stage[stage][start + offset] = chunk
    for req in constant_rows:
        flat = req.get('value')
        expected_values = []
        if isinstance(flat, (int, float)):
            expected_values = [float(flat)]
        elif isinstance(flat, list):
            for item in flat:
                if isinstance(item, list):
                    expected_values.extend(float(x) for x in item)
                elif isinstance(item, (int, float)):
                    expected_values.append(float(item))
                else:
                    expected_values = []
                    break
        capacity = req['register_count'] * 4
        expected_values += [0.0] * max(0, capacity - len(expected_values))
        observed_values = []
        missing_values = []
        for register in req['registers']:
            observed = writes_by_stage.get(req['stage'], {}).get(register)
            if observed is None:
                missing_values.append(register)
            else:
                observed_values.extend(observed)
        mismatched_values = []
        if not missing_values and expected_values:
            for register_offset, register in enumerate(req['registers']):
                expected_chunk = expected_values[register_offset * 4:(register_offset + 1) * 4]
                observed_chunk = writes_by_stage[req['stage']][register]
                if any(not math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-6) for a, b in zip(expected_chunk, observed_chunk)):
                    mismatched_values.append(register)
        status = 'match'
        if missing_values:
            status = 'not-captured'
        elif mismatched_values:
            status = 'mismatch'
        constant_value_checks.append({
            'name': req.get('name'),
            'stage': req['stage'],
            'registers': req['registers'],
            'missing_registers': missing_values,
            'mismatched_registers': mismatched_values,
            'status': status,
        })
        if require_constant_values and missing_values:
            reasons.append(f"constant-values:{req['stage']}:{req['name'] or req['register_index']}:not-captured")
        if mismatched_values:
            reasons.append(f"constant-values:{req['stage']}:{req['name'] or req['register_index']}:mismatch")
    constant_value_status = (
        'not-required' if not require_constant_values and not (runtime_frame.get('constant_writes') or [])
        else ('match' if constant_value_checks and not any(x['status'] != 'match' for x in constant_value_checks)
              else ('not-captured' if any(x['status'] == 'not-captured' for x in constant_value_checks) else 'mismatch'))
    )

    declaration=runtime_frame.get('vertex_declaration') or {}
    declaration_ptr=declaration.get('declaration_ptr')
    declarations=runtime_report.get('declarations') or []
    object_row=next((x for x in declarations if x.get('pointer')==declaration_ptr), None)
    declaration_checks=[]
    decl_status='not-proven'
    if object_row and object_row.get('decoded') and usage_map is not None:
        decoded=object_row['decoded']
        records=decoded.get('records') or []
        for req in _declaration_expectations(material_slice):
            runtime_usage=usage_map.get(req['usage_ordinal'])
            candidates=[r for r in records if r.get('type')==req['type'] and r.get('usage_index')==req['usage_index'] and r.get('usage')==runtime_usage]
            row={**req,'runtime_usage':runtime_usage,'status':'match' if candidates else 'not-found','matches':candidates[:4]}
            declaration_checks.append(row)
            if not candidates: reasons.append(f"declaration:{req['property_id']}:not-found")
        decl_status='match' if declaration_checks and not any(x['status']!='match' for x in declaration_checks) else ('mismatch' if declaration_checks else 'not-proven')
    elif object_row:
        decl_status='partial'
        reasons.append('declaration:usage-map-missing')
    else:
        reasons.append('declaration:instance-missing')

    ready=join.get('ready') is True and constant_status=='match' and decl_status=='match' and not reasons
    return {
        'format':FORMAT,
        'status':'match' if ready else ('partial' if join.get('matched_frame_count') else 'not-found'),
        'ready':ready,
        'blocking_reasons':list(dict.fromkeys(reasons)),
        'shader_join':join,
        'constant_parity':{'status':constant_status,'requirements':constant_rows,'checks':constant_checks,'value_status':constant_value_status,'value_checks':constant_value_checks,'require_values':require_constant_values},
        'declaration_parity':{'status':decl_status,'checks':declaration_checks,'declaration_ptr':declaration_ptr},
    }

def validate_files(material_path: str | Path, runtime_path: str | Path, *, usage_map_path: str | Path | None = None, require_constant_values: bool = False) -> dict[str, Any]:
    material=json.loads(Path(material_path).read_text(encoding='utf-8'))
    runtime=json.loads(Path(runtime_path).read_text(encoding='utf-8'))
    raw=json.loads(Path(usage_map_path).read_text(encoding='utf-8')) if usage_map_path else None
    if isinstance(raw, dict) and isinstance(raw.get('usage_map'), dict):
        raw = raw.get('usage_map')
    usage_map={int(k):int(v) for k,v in raw.items()} if isinstance(raw,dict) else None
    return validate_runtime_parity(material,runtime,usage_map=usage_map,require_constant_values=require_constant_values)

def main() -> int:
    ap=argparse.ArgumentParser(description='Validate BMW runtime shader, constant and D3D9 declaration parity')
    ap.add_argument('material_slice'); ap.add_argument('runtime_report'); ap.add_argument('output'); ap.add_argument('--usage-map'); ap.add_argument('--require-constant-values', action='store_true')
    args=ap.parse_args(); report=validate_files(args.material_slice,args.runtime_report,usage_map_path=args.usage_map,require_constant_values=args.require_constant_values)
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'format':report['format'],'status':report['status'],'ready':report['ready'],'blocking_reasons':report['blocking_reasons']},ensure_ascii=False,indent=2))
    return 0 if report['ready'] else 2

if __name__=='__main__': raise SystemExit(main())