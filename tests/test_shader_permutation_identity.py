import hashlib

from shader_permutation_identity import build_shader_permutation_identity


def _pair():
    from synthetic_fixtures import glass_fxo
    return glass_fxo()

def test_shader_permutation_identity_is_stable_for_same_pair():
    data = _pair()
    from shader_ir import parse_shader_blobs
    blobs = parse_shader_blobs(data)
    vertex = next(blob for blob in blobs if blob.stage == "vertex")
    pixel = next(blob for blob in blobs if blob.stage == "pixel")
    first = build_shader_permutation_identity(data, vertex_offset=vertex.offset, pixel_offset=pixel.offset)
    second = build_shader_permutation_identity(data, vertex_offset=vertex.offset, pixel_offset=pixel.offset)
    assert first == second
    assert first['format'] == 'SHIFT.ShaderPermutationIdentity/1'
    assert len(first['identity_sha256']) == 64
    assert first['pair_byte_sha256'] == hashlib.sha256(
        data[first['vertex_offset']:vertex.end] +
        data[first['pixel_offset']:pixel.end]
    ).hexdigest()


def test_shader_permutation_identity_changes_when_pixel_bytes_change():
    data = bytearray(_pair())
    from shader_ir import parse_shader_blobs
    blobs = parse_shader_blobs(bytes(data))
    vertex = next(blob for blob in blobs if blob.stage == "vertex")
    pixel = next(blob for blob in blobs if blob.stage == "pixel")
    original = build_shader_permutation_identity(bytes(data), vertex_offset=vertex.offset, pixel_offset=pixel.offset)
    name_offset = bytes(data).find(b"diffuseMap", pixel.offset, pixel.end)
    assert name_offset >= 0
    data[name_offset] ^= 1
    changed = build_shader_permutation_identity(bytes(data), vertex_offset=vertex.offset, pixel_offset=pixel.offset)
    assert original['pair_byte_sha256'] != changed['pair_byte_sha256']
    assert original['identity_sha256'] != changed['identity_sha256']