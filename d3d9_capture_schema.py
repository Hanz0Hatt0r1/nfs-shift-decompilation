"""Versioned validator for external SHIFT D3D9 runtime capture events."""
from __future__ import annotations

import re
from typing import Any, Mapping

FORMAT = "SHIFT.D3D9RuntimeCaptureSchema/1"
EVENT_SPECS = {
    'create_vertex_declaration': {'pointer':'declaration_ptr'},
    'set_vertex_declaration': {'pointer':'declaration_ptr'},
    'set_stream_source': {'pointer':'vertex_buffer_ptr'},
    'set_indices': {'pointer':'index_buffer_ptr'},
    'set_texture': {'pointer':'texture_ptr', 'allow_null': True},
    'create_texture': {'pointer':'texture_ptr'},
    'create_cube_texture': {'pointer':'texture_ptr'},
    'create_vertex_buffer': {'pointer':'vertex_buffer_ptr'},
    'create_index_buffer': {'pointer':'index_buffer_ptr'},
    'buffer_payload': {'pointer':'buffer_ptr'},
    'texture_payload': {'pointer':'texture_ptr'},
    'present_screenshot': {},
    'present_screenshot_failed': {},
    'create_vertex_shader': {'pointer':'shader_ptr'},
    'create_pixel_shader': {'pointer':'shader_ptr'},
    'set_vertex_shader': {'pointer':'shader_ptr'},
    'set_pixel_shader': {'pointer':'shader_ptr'},
    'draw_indexed_primitive': {'pointer': None},
    'set_vertex_shader_constant_f': {'pointer':None},
    'set_pixel_shader_constant_f': {'pointer':None},
}
_HEX_RE = re.compile(r'^[0-9a-fA-F]*$')

def validate_capture_event(row: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    event = row.get('event')
    if event not in EVENT_SPECS:
        return ['event:unsupported']
    if 'frame' not in row:
        reasons.append('frame:missing')
    if 'event_index' in row and not isinstance(row.get('event_index'), int):
        reasons.append('event-index:invalid')
    pointer_key = EVENT_SPECS[event].get('pointer')
    if pointer_key:
        value = row.get(pointer_key)
        allow_null = bool(EVENT_SPECS[event].get('allow_null'))
        if value in (None, '') and not (allow_null and value is None):
            reasons.append(f'{pointer_key}:missing')
    if event == 'create_vertex_declaration' and row.get('bytes_hex') is not None:
        raw = row.get('bytes_hex')
        if not isinstance(raw, str) or len(raw) % 2 or not _HEX_RE.fullmatch(raw):
            reasons.append('declaration-bytes:invalid-hex')
    if event in {'create_vertex_shader','create_pixel_shader'} and row.get('bytes_hex') is not None:
        raw = row.get('bytes_hex')
        if not isinstance(raw, str) or len(raw) % 2 or not _HEX_RE.fullmatch(raw):
            reasons.append('shader-bytes:invalid-hex')
    if event == 'create_texture':
        for key in ('width', 'height', 'levels', 'usage', 'format', 'pool'):
            if not isinstance(row.get(key), int):
                reasons.append(f'create-texture:{key}-invalid')
        if isinstance(row.get('width'), int) and row['width'] <= 0:
            reasons.append('create-texture:width-invalid')
        if isinstance(row.get('height'), int) and row['height'] <= 0:
            reasons.append('create-texture:height-invalid')
        if isinstance(row.get('levels'), int) and row['levels'] <= 0:
            reasons.append('create-texture:levels-invalid')
    if event == 'create_cube_texture':
        for key in ('edge_length', 'levels', 'usage', 'format', 'pool'):
            if not isinstance(row.get(key), int):
                reasons.append(f'create-cube-texture:{key}-invalid')
        if isinstance(row.get('edge_length'), int) and row['edge_length'] <= 0:
            reasons.append('create-cube-texture:edge-length-invalid')
        if isinstance(row.get('levels'), int) and row['levels'] <= 0:
            reasons.append('create-cube-texture:levels-invalid')
    if event == 'create_vertex_buffer':
        for key in ('length', 'usage', 'fvf', 'pool'):
            if not isinstance(row.get(key), int):
                reasons.append(f'create-vertex-buffer:{key}-invalid')
        if isinstance(row.get('length'), int) and row['length'] <= 0:
            reasons.append('create-vertex-buffer:length-invalid')
    if event == 'create_index_buffer':
        for key in ('length', 'usage', 'format', 'pool'):
            if not isinstance(row.get(key), int):
                reasons.append(f'create-index-buffer:{key}-invalid')
        if isinstance(row.get('length'), int) and row['length'] <= 0:
            reasons.append('create-index-buffer:length-invalid')
    if event == 'buffer_payload':
        if row.get('resource_type_name') not in {'vertex_buffer', 'index_buffer'}:
            reasons.append('buffer-payload:resource-type-invalid')
        for key in ('offset', 'requested_size', 'buffer_length', 'captured_byte_size', 'flags'):
            if not isinstance(row.get(key), int):
                reasons.append(f'buffer-payload:{key}-invalid')
        for key in ('offset', 'requested_size', 'buffer_length', 'captured_byte_size'):
            if isinstance(row.get(key), int) and row[key] < 0:
                reasons.append(f'buffer-payload:{key}-negative')
        if isinstance(row.get('buffer_length'), int) and row['buffer_length'] <= 0:
            reasons.append('buffer-payload:buffer-length-invalid')
        if isinstance(row.get('captured_byte_size'), int) and row['captured_byte_size'] <= 0:
            reasons.append('buffer-payload:byte-size-invalid')
        if row.get('snapshot_status') not in {'captured', 'capture-failed'}:
            reasons.append('buffer-payload:status-invalid')
        if row.get('payload_path') is not None and not isinstance(row.get('payload_path'), str):
            reasons.append('buffer-payload:path-invalid')
    if event == 'texture_payload':
        resource_type_name = row.get('resource_type_name')
        if resource_type_name == 'cube_texture' and row.get('face') is None:
            reasons.append('texture-payload:cube-face-missing')
        if row.get('face') is not None and (not isinstance(row.get('face'), int) or row.get('face') < 0 or row.get('face') > 5):
            reasons.append('texture-payload:face-invalid')
        if row.get('face_name') is not None and not isinstance(row.get('face_name'), str):
            reasons.append('texture-payload:face-name-invalid')
        if resource_type_name == 'texture2d' and row.get('face') is not None:
            reasons.append('texture-payload:2d-face-unexpected')
        for key in ('level', 'width', 'height', 'pitch', 'format', 'pool', 'byte_size'):
            if not isinstance(row.get(key), int):
                reasons.append(f'texture-payload:{key}-invalid')
        if isinstance(row.get('level'), int) and row['level'] < 0:
            reasons.append('texture-payload:level-invalid')
        if isinstance(row.get('width'), int) and row['width'] <= 0:
            reasons.append('texture-payload:width-invalid')
        if isinstance(row.get('height'), int) and row['height'] <= 0:
            reasons.append('texture-payload:height-invalid')
        if isinstance(row.get('pitch'), int) and row['pitch'] <= 0:
            reasons.append('texture-payload:pitch-invalid')
        if isinstance(row.get('byte_size'), int) and row['byte_size'] <= 0:
            reasons.append('texture-payload:byte-size-invalid')
        if row.get('payload_path') is not None and not isinstance(row.get('payload_path'), str):
            reasons.append('texture-payload:path-invalid')
        if row.get('snapshot_status') is not None and row.get('snapshot_status') not in {'captured', 'capture-failed'}:
            reasons.append('texture-payload:status-invalid')
    if event == 'set_texture':
        if not isinstance(row.get('stage'), int) or int(row.get('stage')) < 0:
            reasons.append('texture:stage-invalid')
    if event == 'present_screenshot':
        if row.get('path') is not None and not isinstance(row.get('path'), str):
            reasons.append('screenshot:path-invalid')
    if event == 'present_screenshot_failed':
        if row.get('reason') is not None and not isinstance(row.get('reason'), str):
            reasons.append('screenshot:reason-invalid')
        if row.get('texture_ptr') not in (None, ''):
            status = row.get('resource_descriptor_status')
            if status is not None and status not in {'observed', 'type-only', 'null'}:
                reasons.append('texture:descriptor-status-invalid')
            for key in ('resource_type', 'width', 'height', 'format', 'pool', 'level_count', 'depth'):
                if row.get(key) is not None and not isinstance(row.get(key), int):
                    reasons.append(f'texture:{key}-invalid')
            if isinstance(row.get('width'), int) and row['width'] < 0:
                reasons.append('texture:width-invalid')
            if isinstance(row.get('height'), int) and row['height'] < 0:
                reasons.append('texture:height-invalid')
            if isinstance(row.get('depth'), int) and row['depth'] < 0:
                reasons.append('texture:depth-invalid')
            if isinstance(row.get('level_count'), int) and row['level_count'] <= 0:
                reasons.append('texture:level-count-invalid')
    if event in {'set_stream_source'}:
        if not isinstance(row.get('stream'), int) or int(row.get('stream')) < 0:
            reasons.append('stream:invalid')
        if not isinstance(row.get('offset_in_bytes'), int) or int(row.get('offset_in_bytes')) < 0:
            reasons.append('stream-offset:invalid')
        if not isinstance(row.get('stride'), int) or int(row.get('stride')) <= 0:
            reasons.append('stream-stride:invalid')
    if event == 'draw_indexed_primitive':
        for key in ('primitive_count','start_index','base_vertex_index'):
            if key in row and not isinstance(row.get(key), int):
                reasons.append(f'draw:{key}:invalid')
        if isinstance(row.get('primitive_count'), int) and row['primitive_count'] < 0:
            reasons.append('draw:primitive-count-negative')
    if event in {'set_vertex_shader_constant_f','set_pixel_shader_constant_f'}:
        start=row.get('start_register')
        count=row.get('vector4f_count', row.get('register_count'))
        values=row.get('values')
        if not isinstance(start, int) or start < 0:
            reasons.append('constant:start-register-invalid')
        if not isinstance(count, int) or count <= 0:
            reasons.append('constant:vector-count-invalid')
        if not isinstance(values, list) or not all(isinstance(x,(int,float)) for x in values):
            reasons.append('constant:values-invalid')
        elif isinstance(count,int) and count > 0 and len(values) != count*4:
            reasons.append('constant:values-length-mismatch')
    if event in {'set_vertex_declaration','create_vertex_declaration'}:
        if row.get('resource_sha256') is not None and not isinstance(row.get('resource_sha256'), str):
            reasons.append('resource-sha256:invalid')
        if row.get('resource_path') is not None and not isinstance(row.get('resource_path'), str):
            reasons.append('resource-path:invalid')
    return list(dict.fromkeys(reasons))

def validate_capture_events(events: list[Mapping[str, Any]]) -> dict[str, Any]:
    rows=[]
    blockers=[]
    for idx,row in enumerate(events):
        reasons=validate_capture_event(row)
        rows.append({'event_index':idx,'event':row.get('event'),'status':'valid' if not reasons else 'invalid','blocking_reasons':reasons})
        blockers.extend({'event_index':idx,'reason':x} for x in reasons)
    return {'format':FORMAT,'status':'valid' if not blockers else 'invalid','ready':not blockers,'event_count':len(events),'events':rows,'blocking_reasons':blockers}