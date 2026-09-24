"""Source-backed D3D9 shader bind lifecycle evidence for SHIFT.exe."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.D3D9ShaderLifecycleEvidence/1"
FUNCTION = 'FUN_0084f000'

EDGES = {
    'pixel_shader': {'byte_offset': 0x1AC, 'vtable_slot': 107, 'field': 0x1890, 'cache_field': 0x1894, 'api': 'IDirect3DDevice9::SetPixelShader'},
    'vertex_shader': {'byte_offset': 0x170, 'vtable_slot': 92, 'field': 0x1898, 'cache_field': 0x189c, 'api': 'IDirect3DDevice9::SetVertexShader'},
}

def _body(source: str, function: str) -> tuple[int | None, int | None, str]:
    lines = source.splitlines()
    start = next((i for i, line in enumerate(lines, 1) if re.search(rf'\\b{re.escape(function)}\\(', line)), None)
    if start is None:
        return None, None, ''
    depth = 0
    seen = False
    body = []
    for index in range(start, len(lines) + 1):
        line = lines[index - 1]
        body.append(line)
        depth += line.count('{')
        depth -= line.count('}')
        seen |= '{' in line
        if seen and depth == 0:
            return start, index, '\\n'.join(body)
    return start, None, '\\n'.join(body)

def analyze_d3d9_shader_lifecycle(source: str) -> dict[str, Any]:
    start, end, body = _body(source, FUNCTION)
    observations = {}
    for name, edge in EDGES.items():
        dispatch = f'+ 0x{edge["byte_offset"]:x}' in body
        current = f'param_1 + 0x{edge["field"]:x}' in body
        cached = f'param_1 + 0x{edge["cache_field"]:x}' in body
        observations[name] = {
            'api': edge['api'],
            'vtable_slot': edge['vtable_slot'],
            'vtable_byte_offset': f'0x{edge["byte_offset"]:x}',
            'state_field_offset': f'0x{edge["field"]:x}',
            'cache_field_offset': f'0x{edge["cache_field"]:x}',
            'dispatch_status': 'observed' if dispatch else 'not-found',
            'state_status': 'observed' if current else 'not-found',
            'cache_status': 'observed' if cached else 'not-found',
        }
    unified = all(x['dispatch_status'] == 'observed' and x['state_status'] == 'observed' for x in observations.values())
    draw_state = {
        'vertex_declaration': {'vtable_byte_offset': '0x15c', 'api': 'SetVertexDeclaration', 'status': 'observed' if '+ 0x15c' in body else 'not-found'},
        'set_stream_source': {'vtable_byte_offset': '0x190', 'api': 'SetStreamSource', 'status': 'observed' if '+ 400)' in body or '+400)' in body else 'not-found'},
        'set_indices': {'vtable_byte_offset': '0x1a0', 'api': 'SetIndices', 'status': 'observed' if '+ 0x1a0' in body else 'not-found'},
    }
    return {
        'format': FORMAT,
        'status': 'observed' if unified else 'not-proven',
        'source': {'kind': 'shift-exe-c', 'bytes': len(source.encode('utf-8')), 'line_count': len(source.splitlines()), 'sha256': hashlib.sha256(source.encode('utf-8')).hexdigest()},
        'function': {'name': FUNCTION, 'line_start': start, 'line_end': end},
        'shaders': observations,
        'unified_draw_state': draw_state,
        'semantic_links': {
            'shader_state_to_device': {'status': 'observed' if unified else 'not-proven', 'detail': 'FUN_0084f000 flushes cached pixel/vertex shader state through the D3D9 device wrapper'},
            'shader_and_geometry_state_same_flush': {'status': 'observed' if unified and all(x['status']=='observed' for x in draw_state.values()) else 'not-proven'},
        },
        'evidence_boundary': {'runtime_frame_identity': 'not-supplied', 'specific_shader_object': 'not-proven'},
    }

def analyze_d3d9_shader_lifecycle_file(path: str | Path) -> dict[str, Any]:
    return analyze_d3d9_shader_lifecycle(Path(path).read_text(encoding='utf-8'))