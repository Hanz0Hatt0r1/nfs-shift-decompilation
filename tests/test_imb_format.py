import struct

import pytest
import imb_format

from imb_format import (
    COMMON_HEADER_SIZE,
    FORMAT,
    VERSION_0_2_0_0,
    VERSION_0_4_0_0,
    locate_imb_mesh_header,
    pack_imb_version,
    parse_imb_binary_mesh,
    parse_imb_binary_mesh_schema,
    unpack_imb_version,
)


def _pack_common(
    data,
    base,
    *,
    vertex_count=3,
    stream_count=2,
    primitive_count=1,
):
    struct.pack_into(
        "<III10f",
        data,
        base,
        vertex_count,
        stream_count,
        primitive_count,
        1.0,
        2.0,
        3.0,
        4.0,
        -1.0,
        -2.0,
        -3.0,
        5.0,
        6.0,
        7.0,
    )


def _build_prefix(version, control, name, *, extra_v04=0):
    data = bytearray(struct.pack("<I", version))
    if version == VERSION_0_2_0_0:
        data += bytes([control & 0xFF])
    else:
        data += struct.pack("<H", control & 0xFFFF)
    if version >= VERSION_0_4_0_0:
        data += struct.pack("<H", extra_v04)
    name_bytes = name.encode("utf-8") + b"\x00"
    data += name_bytes
    if version >= VERSION_0_4_0_0:
        storage = (len(name_bytes) + 3) & ~3
        data += b"\x00" * (storage - len(name_bytes))
    return data


def test_retail_version_pack_is_4_6_11_11_bits():
    assert VERSION_0_2_0_0 == 0x00800000
    assert VERSION_0_4_0_0 == 0x01000000
    packed = pack_imb_version(3, 17, 1025, 511)
    assert unpack_imb_version(packed) == {
        "major": 3,
        "minor": 17,
        "patch": 1025,
        "build": 511,
    }


def test_v02_prefix_uses_one_control_byte_and_forced_runtime_mode():
    data = _build_prefix(VERSION_0_2_0_0, 1, "mesh")
    data += b"\x00" * 0x80
    prefix = locate_imb_mesh_header(bytes(data))

    assert prefix["control_width"] == 1
    assert prefix["resource_name_offset"] == 5
    assert prefix["resource_name"] == "mesh"
    assert prefix["header_offset"] == 10
    assert prefix["has_bone_block"] is True
    assert prefix["runtime_field_0x04_source"] == 1
    assert prefix["runtime_field_0x04_value"] == 1


def test_v04_prefix_uses_extra_word_and_aligns_name_storage():
    data = _build_prefix(
        VERSION_0_4_0_0,
        0x0200,
        "abcd",
        extra_v04=0x1234,
    )
    data += b"\x00" * 0x80
    prefix = locate_imb_mesh_header(bytes(data))

    assert prefix["control_width"] == 2
    assert prefix["resource_name_offset"] == 8
    assert prefix["resource_name_bytes_with_nul"] == 5
    assert prefix["resource_name_storage_bytes"] == 8
    assert prefix["header_offset"] == 16
    assert prefix["extra_v0_4_u16"] == 0x1234
    assert prefix["has_bone_block"] is False
    assert prefix["runtime_field_0x04_source"] == 2
    assert prefix["runtime_field_0x04_value"] == 2


def test_auto_parser_uses_retail_prefix_boundary():
    data = _build_prefix(VERSION_0_4_0_0, 0, "mesh")
    base = len(data)
    data += b"\x00" * 0x100
    _pack_common(data, base, stream_count=1)
    struct.pack_into("<III", data, base + 0x34, 4, 6, 0)

    report = parse_imb_binary_mesh(bytes(data))

    assert report["source"]["prefix_auto_detection"] is True
    assert report["source"]["resource_name"] == "mesh"
    assert report["source"]["header_offset"] == base
    assert report["prefix"]["version_text"] == "0.4.0.0"
    assert report["boundary"]["variable_prefix"] == "source-backed"
    assert report["streams"]["records"][0]["type_ordinal"] == 4


def test_version_newer_than_retail_maximum_is_rejected():
    data = _build_prefix(pack_imb_version(0, 5, 0, 0), 0, "mesh")
    data += b"\x00" * 0x80
    with pytest.raises(ValueError, match="newer than retail loader maximum"):
        locate_imb_mesh_header(bytes(data))


def test_fixed_header_without_bone_block_decodes_stream_triples():
    data = bytearray(0x100)
    base = 0x10
    _pack_common(data, base)
    streams = base + 0x34
    struct.pack_into("<III", data, streams + 0x00, 4, 6, 0)
    # First descriptor is followed immediately by three packed color values.
    struct.pack_into("<3I", data, streams + 0x0C, 0xFF112233, 0xFF445566, 0xFF778899)
    struct.pack_into("<III", data, streams + 0x18, 2, 5, 1)
    struct.pack_into("<9f", data, streams + 0x24, *range(9))

    report = parse_imb_binary_mesh_schema(
        bytes(data),
        header_offset=base,
        has_bone_block=False,
    )

    assert report["format"] == FORMAT
    assert report["header"]["vertex_count"] == 3
    assert report["header"]["stream_count"] == 2
    assert report["header"]["primitive_count"] == 1
    assert report["header"]["bounding_sphere"] == {
        "center_xyz": [1.0, 2.0, 3.0],
        "radius": 4.0,
    }
    assert report["header"]["aabb"] == {
        "min_xyz": [-1.0, -2.0, -3.0],
        "max_xyz": [5.0, 6.0, 7.0],
    }
    assert report["bones"]["present"] is False
    assert report["streams"]["offset"] == streams
    assert report["streams"]["records"][0]["type_ordinal"] == 4
    assert report["streams"]["records"][0]["usage_ordinal"] == 6
    assert report["streams"]["records"][0]["channel"] == 0
    assert report["streams"]["records"][1]["channel"] == 1
    assert report["vertex_payload_offset"] == streams + 0x0C
    assert report["streams"]["records"][1]["source_offset"] == streams + 0x18
    assert report["streams"]["runtime_vertex_stride"] == 16
    assert report["primitives"]["source_section_offset"] == streams + 0x48


def test_bone_block_decodes_names_and_expands_12_float_matrix():
    data = bytearray(0x180)
    base = 0
    _pack_common(
        data,
        base,
        vertex_count=2,
        stream_count=1,
        primitive_count=1,
    )
    names = base + 0x3C
    name = b"root\x00"
    data[names:names + len(name)] = name
    matrices = names + len(name)
    struct.pack_into("<II", data, base + 0x34, 1, len(name))
    matrix_values = [float(i) for i in range(1, 13)]
    struct.pack_into("<12f", data, matrices, *matrix_values)
    streams = matrices + 0x30
    struct.pack_into("<III", data, streams, 4, 6, 0)

    report = parse_imb_binary_mesh_schema(
        bytes(data),
        header_offset=base,
        has_bone_block=True,
    )

    assert report["bones"]["count"] == 1
    assert report["bones"]["names"] == ["root"]
    bone = report["bones"]["matrices"][0]
    assert bone["source_values"] == matrix_values
    assert bone["runtime_matrix_4x4"] == [
        1.0, 2.0, 3.0, 0.0,
        4.0, 5.0, 6.0, 0.0,
        7.0, 8.0, 9.0, 0.0,
        10.0, 11.0, 12.0, 1.0,
    ]
    assert report["streams"]["offset"] == streams
    assert report["vertex_payload_offset"] == streams + 0x0C
    assert report["bones"]["runtime_matrix_array_offset"] == 0x68
    assert report["bones"]["runtime_inverse_matrix_array_offset"] == 0x6C


def test_truncated_stream_table_fails_closed():
    data = bytearray(0x34)
    _pack_common(data, 0, stream_count=1)
    with pytest.raises(ValueError, match="stream descriptor table"):
        parse_imb_binary_mesh_schema(
            bytes(data),
            header_offset=0,
            has_bone_block=False,
        )


def test_bone_name_must_terminate_before_matrix_block():
    data = bytearray(0x100)
    _pack_common(data, 0, stream_count=0)
    struct.pack_into("<II", data, 0x34, 1, 4)
    data[0x3C:0x40] = b"root"
    with pytest.raises(ValueError, match="unterminated IMB bone name"):
        parse_imb_binary_mesh_schema(
            bytes(data),
            header_offset=0,
            has_bone_block=True,
        )


@pytest.mark.parametrize("bone_count,matrix_relative", [
    (1, 0), (2, 1), (0xFFFFFFFF, 4),
])
def test_bone_count_is_bounded_before_reading_names(
    monkeypatch, bone_count, matrix_relative,
):
    data = bytearray(0x40)
    _pack_common(data, 0, stream_count=0)
    struct.pack_into("<II", data, 0x34, bone_count, matrix_relative)

    def unexpected_name_read(*args):
        pytest.fail("invalid bone count reached the name reader")

    monkeypatch.setattr(imb_format, "_read_cstring", unexpected_name_read)
    with pytest.raises(ValueError, match="bone-name block capacity"):
        parse_imb_binary_mesh_schema(
            bytes(data), header_offset=0, has_bone_block=True,
        )


def test_truncated_matrices_are_rejected_before_reading_names(monkeypatch):
    data = bytearray(0x40)
    _pack_common(data, 0, stream_count=0)
    struct.pack_into("<II", data, 0x34, 1, 4)
    data[0x3C:0x40] = b"bad!"

    def unexpected_name_read(*args):
        pytest.fail("truncated matrix block reached the name reader")

    monkeypatch.setattr(imb_format, "_read_cstring", unexpected_name_read)
    with pytest.raises(ValueError, match="IMB bone matrices"):
        parse_imb_binary_mesh_schema(
            bytes(data), header_offset=0, has_bone_block=True,
        )


@pytest.mark.parametrize("version,control,has_bones", [
    (pack_imb_version(0, 1, 0, 0), 0x0201, False),
    (VERSION_0_2_0_0, 1, True),
    (pack_imb_version(0, 3, 0, 0), 0x0200, False),
    (VERSION_0_4_0_0, 0x0201, True),
])
def test_every_schema_truncation_fails_closed(version, control, has_bones):
    data = _build_prefix(version, control, "mesh")
    base = len(data)
    data += b"\x00" * COMMON_HEADER_SIZE
    _pack_common(data, base, vertex_count=0, stream_count=1, primitive_count=0)
    if has_bones:
        # Empty bone names are structurally valid NUL-terminated strings.
        data += struct.pack("<II", 2, 2) + b"\x00\x00"
        data += struct.pack("<24f", *range(24))
    data += struct.pack("<III", 4, 6, 0)

    report = parse_imb_binary_mesh(bytes(data))
    assert report["vertex_payload_offset"] == len(data)
    assert report["bones"]["present"] is has_bones
    assert report["bones"]["count"] == (2 if has_bones else 0)
    assert report["boundary"]["bone_block"] == (
        "source-backed with automatic version/control gate"
    )
    for length in range(len(data)):
        with pytest.raises(ValueError):
            parse_imb_binary_mesh(bytes(data[:length]))


@pytest.mark.parametrize("type_ordinal,element_size", [
    (0, 4), (1, 8), (2, 12), (3, 16), (4, 4), (5, 4), (8, 4),
])
def test_binary_stream_consumes_exact_source_bytes(type_ordinal, element_size):
    data = bytearray(COMMON_HEADER_SIZE)
    _pack_common(data, 0, vertex_count=2, stream_count=1, primitive_count=0)
    data += struct.pack("<III", type_ordinal, 0, 3)
    payload = bytes(range(element_size * 2))
    data += payload
    report = parse_imb_binary_mesh_schema(
        bytes(data), header_offset=0, has_bone_block=False,
    )
    stream = report["streams"]["records"][0]
    assert stream["vertex_payload_hex"] == payload.hex()
    assert stream["vertex_payload_size"] == len(payload)
    assert stream["runtime_element_offset"] == 0
    assert report["primitives"]["source_section_offset"] == len(data)
    with pytest.raises(ValueError, match="stream vertex payload"):
        parse_imb_binary_mesh_schema(
            bytes(data[:-1]), header_offset=0, has_bone_block=False,
        )


@pytest.mark.parametrize("type_ordinal", [6, 7, 9, 15, 16, 17, 0xFFFFFFFF])
def test_unsupported_binary_types_do_not_guess_primitive_offset(type_ordinal):
    data = bytearray(COMMON_HEADER_SIZE)
    _pack_common(data, 0, vertex_count=1, stream_count=1, primitive_count=0)
    data += struct.pack("<III", type_ordinal, 0, 0) + b"\x00" * 64
    with pytest.raises(ValueError, match="unsupported IMB binary Type"):
        parse_imb_binary_mesh_schema(
            bytes(data), header_offset=0, has_bone_block=False,
        )
