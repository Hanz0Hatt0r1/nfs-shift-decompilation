"""Correlate one exact BMW material primitive with a runtime D3D9 indexed draw."""
from __future__ import annotations

from typing import Any, Mapping

from bmw_runtime_shader_join import _runtime_draw_states

FORMAT = "SHIFT.BMWRuntimeDrawCorrelation/1"

def correlate_runtime_draw(material_slice: Mapping[str, Any], runtime_report: Mapping[str, Any]) -> dict[str, Any]:
    if material_slice.get('format') != 'SHIFT.BMWMaterialSlice/1':
        raise ValueError('input is not SHIFT.BMWMaterialSlice/1')
    if runtime_report.get('format') != 'SHIFT.D3D9RuntimeBindingEvidence/1':
        raise ValueError('input is not SHIFT.D3D9RuntimeBindingEvidence/1')
    reasons: list[str] = []
    primitive_index = material_slice.get('primitive_index')
    if primitive_index is None:
        submeshes = (material_slice.get('render_command') or {}).get('submeshes') or []
        if len(submeshes) == 1:
            # Older single-primitive slices predate the explicit primitive_index field.
            primitive_index = 0
        else:
            reasons.append('material:primitive-index-invalid')
            primitive_index = 0
    else:
        try:
            primitive_index = int(primitive_index)
        except (TypeError, ValueError):
            reasons.append('material:primitive-index-invalid')
            primitive_index = 0
    command = material_slice.get('render_command') or {}
    submeshes = command.get('submeshes') or []
    if primitive_index < 0:
        reasons.append('material:primitive-index-invalid')
        expected = {}
    else:
        indexed = [
            row for row in submeshes
            if isinstance(row, Mapping) and int(row.get('index', -1)) == primitive_index
        ]
        if indexed:
            if len(indexed) > 1:
                reasons.append('material:primitive-ambiguous')
                expected = {}
            else:
                expected = indexed[0] or {}
        elif primitive_index < len(submeshes):
            # Backward-compatible fallback for older slices without explicit index.
            expected = submeshes[primitive_index] or {}
        else:
            reasons.append('material:primitive-not-found')
            expected = {}
    try:
        expected_first = int(expected.get('first_index'))
        expected_count = int(expected.get('index_count'))
    except (TypeError, ValueError):
        reasons.append('material:index-range-invalid')
        expected_first = -1; expected_count = -1
    expected_primitive_count = expected_count // 3 if expected_count >= 0 and expected_count % 3 == 0 else None
    if expected_count >= 0 and expected_primitive_count is None:
        reasons.append('material:index-range-not-triangle-list')
    matched: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for frame, state, source in _runtime_draw_states(runtime_report):
        if source == 'draw-snapshot':
            draw_rows = [(state.get('draw_index'), state.get('draw'))]
        else:
            draw_rows = list(enumerate(state.get('draws') or []))
        for draw_index, draw in draw_rows:
            if not isinstance(draw, Mapping):
                continue
            try:
                start_index = int(draw.get('start_index'))
                primitive_count = int(draw.get('primitive_count'))
            except (TypeError, ValueError):
                continue
            row = {
                'frame': frame.get('frame'),
                'draw_index': draw_index,
                'source': source,
                'start_index': start_index,
                'primitive_count': primitive_count,
                'base_vertex_index': draw.get('base_vertex_index'),
                'start_index_match': start_index == expected_first,
                'primitive_count_match': expected_primitive_count is not None and primitive_count == expected_primitive_count,
            }
            candidates.append(row)
            if row['start_index_match'] and row['primitive_count_match']:
                matched.append(row)
    if not candidates:
        reasons.append('runtime:draw-not-captured')
    elif not matched:
        reasons.append('runtime:draw-range-not-found')
    elif len(matched) > 1:
        reasons.append('runtime:multiple-draws-match-primitive')
    ready = not reasons and len(matched) == 1
    return {
        'format': FORMAT,
        'status': 'match' if ready else ('partial' if candidates else 'not-found'),
        'ready': ready,
        'blocking_reasons': list(dict.fromkeys(reasons)),
        'primitive_index': primitive_index,
        'expected': {
            'first_index': expected_first,
            'index_count': expected_count,
            'primitive_count': expected_primitive_count,
        },
        'candidates': candidates,
        'matches': matched,
    }