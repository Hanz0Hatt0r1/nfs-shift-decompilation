import json
import struct

import pytest

from imb_format import VERSION_0_4_0_0
from imb_neutral_geometry import (
    FORMAT,
    build_imb_neutral_geometry,
    build_imb_neutral_geometry_file,
)


def _fixture(*, include_position=True, duplicate_position=False):
    data = bytearray(struct.pack("<IHH", VERSION_0_4_0_0, 0, 0))
    data += b"mesh\x00\xaa\xbb\xcc"
    base = len(data)

    stream_count = 5 if duplicate_position else 4
    data += struct.pack(
        "<III10f",
        3,
        stream_count,
        1,
        0.0, 0.0, 0.0, 2.0,
        -1.0, -1.0, -1.0,
        1.0, 1.0, 1.0,
    )

    position_usage = 0 if include_position else 7
    data += struct.pack("<III", 2, position_usage, 0)
    data += struct.pack(
        "<9f",
        0.0, 0.0, 0.0,
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
    )

    if duplicate_position:
        data += struct.pack("<III", 2, 0, 0)
        data += struct.pack("<9f", *([0.0] * 9))

    data += struct.pack("<III", 1, 3, 0)
    data += struct.pack(
        "<6f",
        0.0, 0.0,
        1.0, 0.0,
        0.0, 1.0,
    )

    data += struct.pack("<III", 4, 6, 0)
    data += bytes([
        10, 20, 30, 255,
        40, 50, 60, 255,
        70, 80, 90, 255,
    ])

    # Supported Type ordinal, but a still-unmapped Type/Usage/Channel triple.
    data += struct.pack("<III", 8, 7, 0)
    data += struct.pack("<6h", 1, 2, 3, 4, 5, 6)

    encoded = b"paint\x00"
    data += encoded + b"\xdd" * ((-len(encoded)) % 4)
    data += struct.pack("<II", 0x12345678, 1)
    data += struct.pack("<3H", 0, 1, 2)
    data += b"\xff\xff"
    data += struct.pack(
        "<HH10f",
        0,
        2,
        0.0, 0.0, 0.0, 2.0,
        -1.0, -1.0, -1.0,
        1.0, 1.0, 1.0,
    )
    return bytes(data), base


def test_adapter_materializes_neutral_fields_and_primitive_ranges():
    data, _ = _fixture()
    report = build_imb_neutral_geometry(data)

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["blocking_reasons"] == []
    assert report["decoded_properties"] == ["200", "130", "460"]
    assert report["deferred_stream_count"] == 1
    assert report["deferred_streams"][0]["property_id"] == "870"

    mesh = report["mesh"]
    assert mesh["format"] == "SHIFT.NeutralMesh/1"
    assert mesh["vertex_count"] == 3
    assert mesh["triangle_count"] == 1
    assert mesh["vertex_properties"] == ["200", "130", "460"]
    assert [row["id"] for row in mesh["property_layouts"]] == [
        "200", "130", "460",
    ]
    assert mesh["vertices"] == [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ]
    assert mesh["uv_layers"]["130"] == [
        [0.0, 0.0],
        [1.0, 0.0],
        [0.0, 1.0],
    ]
    assert mesh["colors"] == [
        [10, 20, 30, 255],
        [40, 50, 60, 255],
        [70, 80, 90, 255],
    ]
    assert mesh["indices"] == [0, 1, 2]
    assert mesh["primitives"][0]["material"] == "paint"
    assert mesh["primitives"][0]["first_index"] == 0
    assert mesh["primitives"][0]["index_count"] == 3
    assert mesh["vertex_layout"]["runtime_interleaved_stride"] == 28

    assert report["primitive_count"] == 1
    primitive = report["primitives"][0]
    assert primitive["material"] == "paint"
    assert primitive["first_index"] == 0
    assert primitive["index_count"] == 3
    assert primitive["triangle_count"] == 1
    assert primitive["vertex_range_u16"] == [0, 2]
    assert primitive["bone_palette_u16"] == []


def test_adapter_preserves_unknown_stream_without_guessing_semantics():
    data, _ = _fixture()
    report = build_imb_neutral_geometry(data)
    row = report["deferred_streams"][0]

    assert row["status"] == "deferred-unmapped"
    assert row["type_ordinal"] == 8
    assert row["usage_ordinal"] == 7
    assert row["channel"] == 0
    assert row["raw_hex"] == struct.pack("<6h", 1, 2, 3, 4, 5, 6).hex()
    assert report["boundary"]["unknown_stream_policy"] == "preserve-raw-and-defer"
    assert report["boundary"]["meb_container_equivalence"] is False


def test_missing_position_blocks_geometry_without_discarding_payload():
    data, _ = _fixture(include_position=False)
    report = build_imb_neutral_geometry(data)

    assert report["ready"] is False
    assert report["status"] == "blocked"
    assert report["blocking_reasons"] == ["position-stream-200-missing"]
    assert report["mesh"]["indices"] == [0, 1, 2]
    assert report["deferred_stream_count"] == 2


def test_duplicate_type_usage_channel_is_rejected():
    data, _ = _fixture(duplicate_position=True)
    with pytest.raises(ValueError, match="duplicate IMB Type/Usage/Channel"):
        build_imb_neutral_geometry(data)


def test_file_adapter_writes_stable_json(tmp_path):
    data, _ = _fixture()
    source = tmp_path / "mesh.imb"
    output = tmp_path / "mesh-neutral.json"
    source.write_bytes(data)

    report = build_imb_neutral_geometry_file(source, output)

    assert report["ready"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["format"] == FORMAT
    assert written["mesh"]["indices"] == [0, 1, 2]
    assert written["primitives"][0]["material"] == "paint"
