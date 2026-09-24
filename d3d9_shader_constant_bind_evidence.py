"""Source-backed evidence for floating-point D3D9 shader constant bind wrappers."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.D3D9ShaderConstantBindEvidence/1"
ROWS = {
    'vertex_float': {'function': 'FUN_0084eb80', 'offset': 0x178, 'slot': 94, 'api': 'IDirect3DDevice9::SetVertexShaderConstantF'},
    'pixel_float': {'function': 'FUN_0084eea0', 'offset': 0x1B4, 'slot': 109, 'api': 'IDirect3DDevice9::SetPixelShaderConstantF'},
}

def _body(source: str, function: str) -> tuple[int | None, int | None, str]:
    lines = source.splitlines()
    start = next((i for i, line in enumerate(lines, 1) if re.search(rf'\\b{re.escape(function)}\\(', line)), None)
    if start is None:
        return None, None, ''
    depth = 0; seen = False; body = []
    for index in range(start, len(lines) + 1):
        line = lines[index - 1]; body.append(line)
        depth += line.count('{'); depth -= line.count('}') ; seen |= '{' in line
        if seen and depth == 0: return start, index, '\\n'.join(body)
    return start, None, '\\n'.join(body)

def analyze_d3d9_shader_constant_bind(source: str) -> dict[str, Any]:
    observations = {}
    for key, row in ROWS.items():
        start, end, body = _body(source, row['function'])
        dispatch = f'+ 0x{row["offset"]:x}' in body
        observations[key] = {
            'function': row['function'], 'api': row['api'], 'vtable_slot': row['slot'],
            'vtable_byte_offset': f'0x{row["offset"]:x}',
            'line_start': start, 'line_end': end,
            'dispatch_status': 'observed' if dispatch else 'not-found',
            'argument_count': 3,
            'argument_shape': ['start_register', 'constant_data_pointer', 'vector4f_count'],
        }
    status = 'observed' if all(x['dispatch_status'] == 'observed' for x in observations.values()) else 'not-proven'
    return {
        'format': FORMAT, 'status': status,
        'source': {'kind':'shift-exe-c','bytes':len(source.encode('utf-8')),'line_count':len(source.splitlines()),'sha256':hashlib.sha256(source.encode('utf-8')).hexdigest()},
        'bindings': observations,
        'semantic_links': {
            'float_constant_api_shape': {'status': status, 'detail':'both recovered wrappers forward start register, constant data pointer and Vector4fCount'}
        },
        'evidence_boundary': {'runtime_frame_identity':'not-supplied','constant_values':'not-supplied'},
    }

def analyze_d3d9_shader_constant_bind_file(path: str | Path) -> dict[str, Any]:
    return analyze_d3d9_shader_constant_bind(Path(path).read_text(encoding='utf-8'))