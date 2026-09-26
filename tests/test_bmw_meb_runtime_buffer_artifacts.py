import struct

from bmw_meb_runtime_buffer_artifacts import (
    build_artifact_report,
    pack_interleaved_vertex_bytes,
    pack_uint16_index_buffers,
)
from meb_format import MEBMesh, MEBPrimitive


def _fake_mesh():
    return MEBMesh(
        name="TEST",
        version=1,
        flags=0,
        vertex_count=2,
        vertex_properties=["200", "460"],
        vertices=[],
        normals=[],
        tangents=[],
        tangents2=[],
        uv_layers={},
        colors=[],
        colors2=[],
        bone_weights=[],
        bone_indices=[],
        vertex_index_hints=[],
        indices=[0, 1, 0],
        primitives=[MEBPrimitive(material="mat", first_index=0, index_count=3)],
        property_layouts=[
            {"id": "200", "payload_offset": 16, "stride": 4, "bytes": 8},
            {"id": "460", "payload_offset": 24, "stride": 2, "bytes": 4},
        ],
        property_descriptors=[],
    )


def _tiny_meb() -> bytes:
    blob = bytearray()
    blob += struct.pack(">II", 1, 0)
    blob += b"TINY\0"
    while len(blob) % 4:
        blob += b"\0"
    blob += struct.pack("<III", 2, 2, 1)
    blob += b"\0" * 40
    blob += struct.pack("<III", 2, 0, 0)
    blob += b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18"
    blob += struct.pack("<III", 4, 6, 0)
    blob += b"\x19\x1a\x1b\x1c\x1d\x1e\x1f\x20"
    blob += b"mat\0"
    while len(blob) % 4:
        blob += b"\0"
    blob += b"\0" * 4
    blob += struct.pack("<I", 1)
    blob += struct.pack("<HHH", 0, 1, 0)
    while len(blob) % 4:
        blob += b"\0"
    blob += b"\0" * 4
    blob += b"\0" * 40
    return bytes(blob)


def test_interleave_copies_raw_property_bytes_without_reencoding():
    mesh = _fake_mesh()
    source = b"\0" * 16 + b"\x01\x02\x03\x04\x05\x06\x07\x08" + b"\xaa\xbb\xcc\xdd"
    packed = pack_interleaved_vertex_bytes(source, mesh)
    assert packed == b"\x01\x02\x03\x04\xaa\xbb\x05\x06\x07\x08\xcc\xdd"


def test_index_buffers_preserve_exact_uint16_little_endian_order():
    mesh = _fake_mesh()
    full, primitives = pack_uint16_index_buffers(mesh)
    assert full == struct.pack("<3H", 0, 1, 0)
    assert primitives == [full]


def test_build_artifact_report_is_self_consistent_on_synthetic_meb_layout():
    meb = _tiny_meb()
    report, vertex, indices, primitives = build_artifact_report(
        meb,
        source={"path": "test.meb"},
    )
    assert report["format"] == "SHIFT.BMWM3RuntimeBufferArtifacts/1"
    assert report["claim_boundary"]["raw_d3d9_runtime_bytes"] == "not-proven"
    assert report["mesh"]["vertex_count"] == 2
    assert report["mesh"]["vertex_stride"] == 16
    assert report["vertex"]["byte_size"] == 32
    assert report["index"]["byte_size"] == 6
    assert vertex == (
        b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c"
        b"\x19\x1a\x1b\x1c"
        b"\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18"
        b"\x1d\x1e\x1f\x20"
    )
    assert indices == struct.pack("<3H", 0, 1, 0)
    assert primitives == [indices]
    assert report["index"]["primitives"][0]["byte_size"] == 6
