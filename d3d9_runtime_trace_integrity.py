"""Integrity checks for ordered D3D9 runtime capture events."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

FORMAT = "SHIFT.D3D9RuntimeTraceIntegrity/1"

def validate_runtime_trace_integrity(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    created_declarations: dict[str, tuple[str, int]] = {}
    created_shaders: dict[str, tuple[str, int]] = {}
    frame_state: dict[str, dict[str, Any]] = {}
    blockers: list[dict[str, Any]] = []
    event_count = 0
    observed_event_indices: list[int] = []

    for line_index, raw in enumerate(events, 1):
        row = dict(raw); event_count += 1
        if 'event_index' in row and isinstance(row.get('event_index'), int):
            observed_event_indices.append(row['event_index'])
        frame_key = str(row.get('frame', 'unknown'))
        state = frame_state.setdefault(frame_key, {'declaration': False, 'vertex_shader': False, 'pixel_shader': False, 'stream': False, 'indices': False, 'draws': 0})
        event = row.get('event')
        pointer = str(row.get('declaration_ptr') or '')
        shader_ptr = str(row.get('shader_ptr') or '')
        if event == 'create_vertex_declaration':
            if not pointer: blockers.append({'line': row.get('_line', line_index), 'reason': 'declaration-pointer-missing'})
            raw_hex = str(row.get('bytes_hex') or '')
            prior = created_declarations.get(pointer)
            if prior and prior[0] != raw_hex: blockers.append({'line': row.get('_line', line_index), 'reason': 'declaration-pointer-reused-with-different-bytes', 'pointer': pointer})
            elif pointer: created_declarations[pointer] = (raw_hex, row.get('_line', line_index))
        elif event == 'set_vertex_declaration':
            if not pointer or pointer not in created_declarations: blockers.append({'line': row.get('_line', line_index), 'reason': 'declaration-bind-before-create', 'pointer': pointer or None})
            else: state['declaration'] = True
        elif event in {'create_vertex_shader', 'create_pixel_shader'}:
            if not shader_ptr: blockers.append({'line': row.get('_line', line_index), 'reason': 'shader-pointer-missing'})
            raw_hex = str(row.get('bytes_hex') or '')
            prior = created_shaders.get(shader_ptr)
            if prior and prior[0] != raw_hex: blockers.append({'line': row.get('_line', line_index), 'reason': 'shader-pointer-reused-with-different-bytes', 'pointer': shader_ptr})
            elif shader_ptr: created_shaders[shader_ptr] = (raw_hex, row.get('_line', line_index))
        elif event in {'set_vertex_shader', 'set_pixel_shader'}:
            if not shader_ptr or shader_ptr not in created_shaders: blockers.append({'line': row.get('_line', line_index), 'reason': 'shader-bind-before-create', 'pointer': shader_ptr or None})
            else: state['vertex_shader' if event == 'set_vertex_shader' else 'pixel_shader'] = True
        elif event == 'set_stream_source':
            state['stream'] = True
        elif event == 'set_indices':
            state['indices'] = True
        elif event == 'draw_indexed_primitive':
            state['draws'] += 1
            missing = [key for key, present in [('declaration', state['declaration']), ('vertex_shader', state['vertex_shader']), ('pixel_shader', state['pixel_shader']), ('stream', state['stream']), ('indices', state['indices'])] if not present]
            if missing: blockers.append({'line': row.get('_line', line_index), 'reason': 'draw-state-incomplete', 'frame': row.get('frame'), 'missing': missing})

    if observed_event_indices:
        expected_indices = list(range(
            observed_event_indices[0],
            observed_event_indices[0] + len(observed_event_indices),
        ))
        if observed_event_indices != expected_indices:
            blockers.append({
                'line': None,
                'reason': 'event-index-not-contiguous',
                'first': observed_event_indices[0],
                'last': observed_event_indices[-1],
            })

    frames = []
    for frame_key, state in frame_state.items():
        frames.append({'frame': None if frame_key == 'unknown' else frame_key, **state, 'status': 'observed' if state['draws'] and not blockers else 'partial'})
    has_draw = any(item['draws'] for item in frame_state.values())
    return {
        'format': FORMAT,
        'status': 'observed' if has_draw and not blockers else ('partial' if event_count else 'not-supplied'),
        'event_count': event_count,
        'created_declaration_count': len(created_declarations),
        'created_shader_count': len(created_shaders),
        'event_index': {
            'status': (
                'valid' if not observed_event_indices or not any(
                    reason.get('reason') == 'event-index-not-contiguous'
                    for reason in blockers
                    if isinstance(reason, dict)
                ) else 'invalid'
            ),
            'observed_count': len(observed_event_indices),
            'first': observed_event_indices[0] if observed_event_indices else None,
            'last': observed_event_indices[-1] if observed_event_indices else None,
        },
        'frames': sorted(frames, key=lambda row: str(row['frame'])),
        'blocking_reasons': blockers,
    }