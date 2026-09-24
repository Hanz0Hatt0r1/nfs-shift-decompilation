"""Validate BMW vertex semantic parity between runtime D3D9 declaration and target layout."""
from __future__ import annotations

from typing import Any, Mapping

from bmw_runtime_shader_join import join_runtime_shader

FORMAT = "SHIFT.BMWVertexInputParity/1"
TYPE_BY_PROPERTY = {
    '200': 1, '220': 2, '240': 2, '250': 2,
    '130': 1, '131': 1, '132': 1, '133': 1, '134': 1,
    '230': 2, '231': 2, '232': 2, '233': 2, '234': 2,
    '310': 3, '460': 4, '580': 5,
}
USAGE_ORDINAL_BY_PROPERTY = {
    '200': 0, '310': 1, '220': 3, '240': 6, '250': 7, '460': 10, '580': 2,
}

def _layout_attrs(material_slice: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mesh = material_slice.get('mesh') or {}
    layout = mesh.get('vertex_layout') or {}
    return list(layout.get('attributes') or []) if isinstance(layout, Mapping) else []

def _shader_inputs(runtime_frame: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    identity = runtime_frame.get('shader_permutation_identity') or {}
    return list((((identity.get('payload') or {}).get('vertex') or {}).get('inputs')) or [])

def validate_bmw_vertex_input_parity(
    material_slice: Mapping[str, Any],
    runtime_report: Mapping[str, Any],
    *,
    usage_map: Mapping[int, int] | None = None,
) -> dict[str, Any]:
    join = join_runtime_shader(material_slice, runtime_report)
    reasons = list(join.get('blocking_reasons') or [])
    if not join.get('matched_frame_count'):
        return {
            'format': FORMAT, 'status': 'not-found', 'ready': False,
            'blocking_reasons': list(dict.fromkeys(reasons)),
            'shader_join': join, 'checks': [],
            'physical_layout': {'status': 'not-comparable-by-design'},
        }

    frame = join['candidate_frames'][0]
    runtime_frame = next(
        (f for f in runtime_report.get('frames') or [] if f.get('frame') == frame.get('frame')),
        None,
    ) or {}
    declaration = runtime_frame.get('vertex_declaration') or {}
    pointer = declaration.get('declaration_ptr')
    declaration_rows = runtime_report.get('declarations') or []
    declaration_obj = next((x for x in declaration_rows if x.get('pointer') == pointer), None)
    records = list((((declaration_obj or {}).get('decoded') or {}).get('records')) or [])
    attrs = _layout_attrs(material_slice)
    attrs_by_semantic = {
        (str(a.get('usage')).upper(), int(a.get('usage_index', 0))): a
        for a in attrs
        if a.get('usage')
    }
    checks = []
    shader_inputs = _shader_inputs(runtime_frame)
    if not declaration_obj or not records:
        reasons.append('vertex-input:declaration-instance-missing')
    if not shader_inputs:
        reasons.append('vertex-input:shader-input-reflection-missing')
    for shader_input in shader_inputs:
        usage = str(shader_input.get('usage') or '').upper()
        usage_index = int(shader_input.get('index', 0) or 0)
        register_text = str(shader_input.get('register') or '')
        try:
            register = int(register_text.removeprefix('v'))
        except ValueError:
            register = None
        attr = attrs_by_semantic.get((usage, usage_index))
        row = {
            'usage': usage, 'usage_index': usage_index, 'shader_register': register,
            'status': 'match' if attr is not None else 'not-found',
            'property_id': str(attr.get('property_id')) if attr is not None else None,
            'render_location': attr.get('location') if attr is not None else None,
        }
        if attr is None:
            reasons.append(f'vertex-input:layout-semantic-missing:{usage}{usage_index}')
            checks.append(row)
            continue
        pid = str(attr.get('property_id'))
        expected_type = TYPE_BY_PROPERTY.get(pid)
        expected_usage_ordinal = USAGE_ORDINAL_BY_PROPERTY.get(pid)
        runtime_usage = usage_map.get(expected_usage_ordinal) if usage_map is not None and expected_usage_ordinal is not None else None
        matches = [
            r for r in records
            if (expected_type is None or r.get('type') == expected_type)
            and (runtime_usage is None or r.get('usage') == runtime_usage)
            and r.get('usage_index') == usage_index
        ]
        row.update({
            'expected_d3d9_type': expected_type,
            'expected_usage_ordinal': expected_usage_ordinal,
            'runtime_usage': runtime_usage,
            'declaration_status': 'match' if matches and expected_type is not None and runtime_usage is not None else 'not-proven',
            'declaration_matches': matches[:4],
        })
        if expected_type is None or expected_usage_ordinal is None:
            reasons.append(f'vertex-input:property-unmapped:{pid}')
        elif usage_map is None:
            reasons.append(f'vertex-input:usage-map-missing:{pid}')
        elif not matches:
            reasons.append(f'vertex-input:declaration-mismatch:{pid}')
        if register is not None and attr.get('location') is not None and int(attr['location']) != register:
            reasons.append(f'vertex-input:location-mismatch:{pid}')
            row['status'] = 'mismatch'
        checks.append(row)

    target_attrs = []
    for attr in attrs:
        target_attrs.append({
            'property_id': str(attr.get('property_id')),
            'usage': attr.get('usage'),
            'usage_index': int(attr.get('usage_index', 0) or 0),
            'location': attr.get('location'),
            'offset': attr.get('offset'),
            'stride': attr.get('stride'),
            'buffer_index': attr.get('buffer_index', 0),
        })
    physical_layout = {
        'status': 'not-comparable-by-design',
        'reason': 'RenderCommand uses deterministic interleaved repack; runtime D3D9 streams preserve original physical stream/offset values',
        'runtime_records': [
            {'stream': r.get('stream'), 'offset': r.get('offset'), 'type': r.get('type'), 'usage': r.get('usage'), 'usage_index': r.get('usage_index')}
            for r in records
        ],
        'target_attributes': target_attrs,
    }
    ready = bool(join.get('ready') and checks and not reasons)
    return {
        'format': FORMAT,
        'status': 'match' if ready else ('partial' if checks else 'not-found'),
        'ready': ready,
        'blocking_reasons': list(dict.fromkeys(reasons)),
        'shader_join': join,
        'checks': checks,
        'physical_layout': physical_layout,
    }