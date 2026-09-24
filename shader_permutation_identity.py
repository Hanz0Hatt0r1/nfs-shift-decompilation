"""Stable identity for one exact D3D9 VS/PS shader permutation."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from shader_asm import parse_program
from shader_ir import parse_shader_blobs

FORMAT = "SHIFT.ShaderPermutationIdentity/1"

def _semantic_rows(rows):
    return [
        {
            'register': row.get('register'),
            'usage': row.get('usage'),
            'index': int(row.get('index', 0)),
        }
        for row in rows or []
    ]

def build_shader_permutation_identity(data: bytes, *, vertex_offset: int, pixel_offset: int) -> dict[str, Any]:
    blobs = parse_shader_blobs(data)
    by_offset = {b.offset: b for b in blobs}
    vb = by_offset.get(vertex_offset)
    pb = by_offset.get(pixel_offset)
    if vb is None or vb.stage != 'vertex':
        raise ValueError(f'vertex shader blob not found at offset {vertex_offset}')
    if pb is None or pb.stage != 'pixel':
        raise ValueError(f'pixel shader blob not found at offset {pixel_offset}')
    vertex = parse_program(data, vb.offset, vb.end, vb.stage, vb.major, vb.minor)
    pixel = parse_program(data, pb.offset, pb.end, pb.stage, pb.major, pb.minor)
    vertex_bytes = data[vb.offset:vb.end]
    pixel_bytes = data[pb.offset:pb.end]
    payload = {
        'version': 1,
        'vertex': {
            'shader_model': [vb.major, vb.minor],
            'byte_sha256': hashlib.sha256(vertex_bytes).hexdigest(),
            'instruction_count': vb.instruction_count,
            'inputs': _semantic_rows(vertex.inputs),
            'outputs': _semantic_rows(vertex.outputs),
            'constants': sorted(int(x) for x in vertex.constants),
            'unsupported_opcodes': list(vertex.unsupported_opcodes),
        },
        'pixel': {
            'shader_model': [pb.major, pb.minor],
            'byte_sha256': hashlib.sha256(pixel_bytes).hexdigest(),
            'instruction_count': pb.instruction_count,
            'inputs': _semantic_rows(pixel.inputs),
            'outputs': _semantic_rows(pixel.outputs),
            'samplers': sorted(int(x) for x in pixel.samplers),
            'sampler_types': {str(k): v for k, v in sorted(pixel.sampler_types.items())},
            'constants': sorted(int(x) for x in pixel.constants),
            'unsupported_opcodes': list(pixel.unsupported_opcodes),
        },
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return {
        'format': FORMAT,
        'identity_sha256': hashlib.sha256(canonical).hexdigest(),
        'vertex_offset': vertex_offset,
        'pixel_offset': pixel_offset,
        'vertex_byte_sha256': payload['vertex']['byte_sha256'],
        'pixel_byte_sha256': payload['pixel']['byte_sha256'],
        'pair_byte_sha256': hashlib.sha256(vertex_bytes + pixel_bytes).hexdigest(),
        'canonical_sha256': hashlib.sha256(canonical).hexdigest(),
        'payload': payload,
    }