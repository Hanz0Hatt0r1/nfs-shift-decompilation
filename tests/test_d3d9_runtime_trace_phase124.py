import json
import struct

from d3d9_runtime_trace import build_runtime_binding_evidence, load_events


def _shader(stage_version):
    header = 28
    info = 20
    typ = 20
    name = b'diffuseMap\\x00'
    payload = bytearray(b'CTAB')
    payload += struct.pack('<7I', header, 0, stage_version, 1, header, 0, 0)
    payload += struct.pack('<IHHHHII', header + info + typ, 3, 0, 1, 0, header + info, 0)
    payload += struct.pack('<HHHHHHII', 4, 12, 1, 1, 1, 0, 0, 0)
    payload += name
    payload += b'\\x00' * ((-len(payload)) % 4)
    blob = bytearray(struct.pack('<I', stage_version))
    blob += struct.pack('<I', ((len(payload) // 4) << 16) | 0xFFFE)
    blob += payload
    blob += struct.pack('<I', 0xFFFF)
    return bytes(blob)


def test_runtime_trace_tracks_shader_objects_and_pair_identity(tmp_path):
    vs = _shader(0xFFFE0300)
    ps = _shader(0xFFFF0300)
    trace = tmp_path / 'trace.jsonl'
    rows = [
        {'event': 'create_vertex_shader', 'frame': 4, 'shader_ptr': '0x10', 'bytes_hex': vs.hex()},
        {'event': 'create_pixel_shader', 'frame': 4, 'shader_ptr': '0x20', 'bytes_hex': ps.hex()},
        {'event': 'set_vertex_shader', 'frame': 4, 'shader_ptr': '0x10'},
        {'event': 'set_pixel_shader', 'frame': 4, 'shader_ptr': '0x20'},
        {'event': 'draw_indexed_primitive', 'frame': 4, 'primitive_count': 1, 'start_index': 0, 'base_vertex_index': 0},
    ]
    trace.write_text('\\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    report = build_runtime_binding_evidence(load_events(trace))
    assert report['trace']['shader_object_count'] == 2
    assert report['trace']['decoded_shader_count'] == 2
    identity = report['frames'][0]['shader_permutation_identity']
    assert identity is not None
    assert identity['format'] == 'SHIFT.ShaderPermutationIdentity/1'
    assert len(identity['identity_sha256']) == 64


def test_runtime_trace_rejects_multi_blob_shader_create():
    blob = _shader(0xFFFE0300)
    rows = [{'event': 'create_vertex_shader', 'frame': 1, 'shader_ptr': '0x1', 'bytes_hex': (blob + blob).hex()}]
    try:
        build_runtime_binding_evidence(rows)
    except ValueError as exc:
        assert 'expected exactly one shader blob' in str(exc)
    else:
        raise AssertionError('expected ValueError')