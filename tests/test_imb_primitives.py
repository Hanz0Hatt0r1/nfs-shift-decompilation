import json
import struct

import pytest

from imb_format import VERSION_0_4_0_0, main, parse_imb_binary_mesh
from shift_importer import build_parser


def _fixture(*, bone_count=0, bone_header=False, names=('paint', 'x')):
    data = bytearray(struct.pack('<IHH', VERSION_0_4_0_0, int(bone_header or bone_count > 0), 0))
    data += b'mesh\x00\xaa\xbb\xcc'
    base = len(data)
    data += struct.pack('<III10f', 4, 1, 2, *range(10))
    if bone_header or bone_count:
        # An odd name region deliberately makes the section cursor unaligned.
        bone_names = b'root\x00' * bone_count
        data += struct.pack('<II', bone_count, len(bone_names)) + bone_names
        data += struct.pack('<12f', *range(12)) * bone_count
    data += struct.pack('<III12f', 2, 0, 0, *range(12))
    offsets = []
    for number, name in enumerate(names):
        start = len(data)
        encoded = name.encode() + b'\x00'
        data += encoded + b'\xdd' * ((-len(encoded)) % 4)
        count_offset = len(data) + 4
        triangles = number + 1
        data += struct.pack('<II', 0x12345678 + number, triangles)
        palette_count_offset = None
        if bone_count:
            palette_count_offset = len(data)
            palette = list(range(number + 1))
            data += struct.pack('<I', len(palette))
            data += struct.pack('<' + 'H' * len(palette), *palette)
            data += b'\xee\xee' if len(palette) % 2 else b''
        index_offset = len(data)
        indices = [0, 1, 2] if number == 0 else [3, 2, 1, 0, 2, 3]
        data += struct.pack('<' + 'H' * len(indices), *indices)
        data += b'\xff\xff' if triangles % 2 else b''
        trailer = len(data)
        data += struct.pack('<HH10f', 0, 2 + number, *range(10 + number, 20 + number))
        offsets.append((start, count_offset, palette_count_offset, index_offset, trailer))
    return data, base, offsets


@pytest.mark.parametrize('bone_count,bone_header', [(0, False), (0, True), (2, True)])
def test_v04_two_primitive_records_preserve_layout(bone_count, bone_header):
    data, _, offsets = _fixture(bone_count=bone_count, bone_header=bone_header)
    report = parse_imb_binary_mesh(bytes(data) + b'tail', decode_primitives=True)
    primitives = report['primitives']
    assert primitives['source_end_offset'] == len(data)
    assert primitives['trailing_bytes'] == 4
    assert report['boundary']['primitive_source_decode'] == 'source-backed-v0.4'
    first, second = primitives['records']
    assert first['material_name'] == 'paint'
    assert first['material_name_storage_bytes'] == 8
    assert second['material_name'] == 'x'
    assert second['material_name_storage_bytes'] == 4
    assert first['material_opaque_word'] == 0x12345678
    assert second['material_opaque_word'] == 0x12345679
    assert first['indices_u16'] == [0, 1, 2]
    assert second['indices_u16'] == [3, 2, 1, 0, 2, 3]
    for number, record in enumerate(primitives['records']):
        start, _, _, indices, trailer = offsets[number]
        assert record['source_offset'] == start
        assert record['indices_offset'] == indices
        assert record['trailer_offset'] == trailer
        assert record['bone_palette_u16'] == (list(range(number + 1)) if bone_count else [])
        assert record['bounding_sphere'] == {'center_xyz': [10.0 + number, 11.0 + number, 12.0 + number], 'radius': 13.0 + number}
        assert record['aabb'] == {'min_xyz': [14.0 + number, 15.0 + number, 16.0 + number], 'max_xyz': [17.0 + number, 18.0 + number, 19.0 + number]}
        assert record['vertex_range_u16'] == [0, 2 + number]
    assert first['source_offset'] + first['source_size'] == second['source_offset']


@pytest.mark.parametrize('bone_count', [0, 2])
def test_every_primitive_payload_truncation_is_rejected(bone_count):
    data, _, _ = _fixture(bone_count=bone_count)
    for length in range(len(data)):
        with pytest.raises(ValueError):
            parse_imb_binary_mesh(bytes(data[:length]), decode_primitives=True)


@pytest.mark.parametrize('field', ['primitive_count', 'triangle_count', 'palette_count', 'index'])
def test_invalid_primitive_counts_and_indices(field):
    data, base, offsets = _fixture(bone_count=2)
    if field == 'primitive_count':
        offset, fmt, value, error = base + 8, '<I', 0xFFFFFFFF, 'primitive records'
    elif field == 'triangle_count':
        offset, fmt, value, error = offsets[0][1], '<I', 0xFFFFFFFF, 'primitive indices'
    elif field == 'palette_count':
        offset, fmt, value, error = offsets[0][2], '<I', 0xFFFFFFFF, 'bone palette'
    else:
        offset, fmt, value, error = offsets[0][3], '<H', 4, 'vertex count'
    struct.pack_into(fmt, data, offset, value)
    with pytest.raises(ValueError, match=error):
        parse_imb_binary_mesh(bytes(data), decode_primitives=True)


def test_unterminated_material_name_fails():
    data, _, offsets = _fixture()
    data[offsets[0][0]:] = b'A' * (len(data) - offsets[0][0])
    with pytest.raises(ValueError, match='material name'):
        parse_imb_binary_mesh(bytes(data), decode_primitives=True)


def test_primitive_decode_requires_proven_version():
    data, _, _ = _fixture()
    struct.pack_into('<I', data, 0, 0x00C00000)
    with pytest.raises(ValueError, match='requires version 0.4.0.0'):
        parse_imb_binary_mesh(bytes(data), decode_primitives=True)


def test_both_cli_paths_decode_primitives(tmp_path):
    data, _, _ = _fixture(bone_count=2)
    source, output = tmp_path / 'mesh.imb', tmp_path / 'mesh.json'
    source.write_bytes(data)
    assert main([str(source), str(output), '--decode-primitives']) == 0
    assert len(json.loads(output.read_text())['primitives']['records']) == 2
    parser = build_parser()
    args = parser.parse_args(['imb-binary-schema', str(source), str(output), '--decode-primitives'])
    assert args.fn(args) == 0
    assert len(json.loads(output.read_text())['primitives']['records']) == 2
    args = parser.parse_args(['imb-binary-schema', str(source), str(output), '--decode-primitives', '--header-offset', '16'])
    with pytest.raises(ValueError, match='automatic version/prefix'):
        args.fn(args)
    with pytest.raises(SystemExit):
        main([str(source), str(output), '--decode-primitives', '--header-offset', '16'])
