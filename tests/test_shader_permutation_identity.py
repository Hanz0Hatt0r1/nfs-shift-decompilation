import hashlib

from shader_permutation_identity import build_shader_permutation_identity


def _pair():
    import struct

    def ctab(name: bytes, stage_version: int, register: int) -> bytes:
        header = 28
        info = 20
        typ = 20
        name_off = header + info + typ
        payload = bytearray(b"CTAB")
        payload += struct.pack("<7I", header, 0, stage_version, 1, header, 0, 0)
        payload += struct.pack("<IHHHHII", name_off, 3, register, 1, 0, header + info, 0)
        payload += struct.pack("<HHHHHHII", 4, 12, 1, 1, 1, 0, 0, 0)
        payload += name
        payload += b"\x00" * ((-len(payload)) % 4)
        return struct.pack("<I", stage_version) + struct.pack(
            "<I", ((len(payload) // 4) << 16) | 0xFFFE
        ) + payload

    vs_version = 0xFFFE0300
    ps_version = 0xFFFF0300
    dcl = (2 << 24) | 31
    vs = bytearray(ctab(b"diffuseMap\\x00", vs_version, 0))
    vs += struct.pack("<III", dcl, 0, 0x80000000 | 0 | (15 << 16) | (1 << 28))
    vs += struct.pack("<III", dcl, 5 | (5 << 16), 0x80000000 | 1 | (15 << 16) | (6 << 28))
    vs += struct.pack("<I", 0xFFFF)

    ps = bytearray(ctab(b"diffuseMap\\x00", ps_version, 0))
    ps += struct.pack("<III", dcl, 5 | (5 << 16), 0x80000000 | 0 | (15 << 16) | (1 << 28))
    ps += struct.pack("<I", 0xFFFF)
    return bytes(vs + ps)


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