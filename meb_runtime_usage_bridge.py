"""Derive a D3D9 Usage-byte map only from exact same-resource runtime declaration evidence."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

FORMAT = "SHIFT.MEBRuntimeUsageOrdinalBridge/1"

def _norm(value: Any) -> str:
    return str(value or '').replace('\\','/').strip('/').lower()

def _descriptor_rows(material_slice: Mapping[str, Any]) -> list[dict[str, Any]]:
    mesh=material_slice.get('mesh') or {}
    return [dict(x) for x in mesh.get('property_descriptors') or [] if isinstance(x, Mapping)]

def build_usage_ordinal_bridge(material_slice: Mapping[str, Any], runtime_report: Mapping[str, Any]) -> dict[str, Any]:
    if material_slice.get('format') != 'SHIFT.BMWMaterialSlice/1':
        raise ValueError('input is not SHIFT.BMWMaterialSlice/1')
    if runtime_report.get('format') != 'SHIFT.D3D9RuntimeBindingEvidence/1':
        raise ValueError('input is not SHIFT.D3D9RuntimeBindingEvidence/1')
    golden=material_slice.get('golden_identity') or {}
    expected_sha=str(golden.get('resource_sha256') or '')
    expected_path=_norm(golden.get('resource'))
    declarations={str(x.get('pointer')):x for x in runtime_report.get('declarations') or [] if x.get('pointer')}
    observations: dict[int, list[int]]={}
    evidence_rows=[]
    for frame in runtime_report.get('frames') or []:
        binding=frame.get('vertex_declaration') or {}
        same=False
        if expected_sha and binding.get('resource_sha256'):
            same=str(binding.get('resource_sha256'))==expected_sha
        elif expected_path and binding.get('resource_path'):
            same=_norm(binding.get('resource_path'))==expected_path
        if not same:
            continue
        decl=declarations.get(str(binding.get('declaration_ptr')))
        records=list((((decl or {}).get('decoded') or {}).get('records')) or [])
        for descriptor in _descriptor_rows(material_slice):
            words=descriptor.get('words')
            if not isinstance(words,list) or len(words)<3:
                continue
            type_ordinal, usage_ordinal, channel=(int(words[0]),int(words[1]),int(words[2]))
            matches=[r for r in records if r.get('type')==type_ordinal and r.get('usage_index')==channel]
            usages=sorted({int(r.get('usage')) for r in matches if r.get('usage') is not None})
            row={'frame':frame.get('frame'),'property_id':str(descriptor.get('id')),'type_ordinal':type_ordinal,'usage_ordinal':usage_ordinal,'channel':channel,'declaration_ptr':binding.get('declaration_ptr'),'candidate_runtime_usages':usages,'status':'match' if len(usages)==1 else ('ambiguous' if len(usages)>1 else 'not-found')}
            evidence_rows.append(row)
            if len(usages)==1:
                observations.setdefault(usage_ordinal,[]).append(usages[0])
            elif len(usages)>1:
                conflicts.append({'usage_ordinal':usage_ordinal,'runtime_usages':usages})
    mapping={}; conflicts=[]; unmapped=[]
    for ordinal, usages in sorted(observations.items()):
        unique=sorted(set(usages))
        if len(unique)==1:
            mapping[str(ordinal)]=unique[0]
        else:
            conflicts.append({'usage_ordinal':ordinal,'runtime_usages':unique})
    conflicts_by_ordinal={}
    for conflict in conflicts:
        conflicts_by_ordinal.setdefault(conflict['usage_ordinal'], set()).update(conflict['runtime_usages'])
    conflicts=[{'usage_ordinal':k,'runtime_usages':sorted(v)} for k,v in sorted(conflicts_by_ordinal.items())]

    descriptor_ordinals=sorted({int(d['words'][1]) for d in _descriptor_rows(material_slice) if isinstance(d.get('words'),list) and len(d['words'])>=3})
    for ordinal in descriptor_ordinals:
        if str(ordinal) not in mapping and not any(x['usage_ordinal']==ordinal for x in conflicts):
            unmapped.append(ordinal)
    status='observed' if mapping and not conflicts and not unmapped else ('ambiguous' if conflicts else ('partial' if mapping else 'not-proven'))
    return {'format':FORMAT,'status':status,'ready':bool(mapping and not conflicts and not unmapped),'usage_map':mapping,'observations':evidence_rows,'conflicts':conflicts,'unmapped_usage_ordinals':unmapped,'evidence_boundary':{'requires_same_resource_identity':True,'runtime_capture_authenticity':'not-verified'}}