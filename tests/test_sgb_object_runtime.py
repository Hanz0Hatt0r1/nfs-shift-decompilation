import struct

import pytest

from sgb_object_runtime import (
    SGBObjectDecodeError,
    parse_matrix_records,
    parse_sgb_object_payload,
)


def _append_string(buf: bytearray, text: str) -> int:
    offset = len(buf)
    buf += text.encode("utf-8") + b"\0"
    return offset


def _matrix(
    *,
    offset=(1.0, 2.0, 3.0),
    orientation=(0.1, 0.2, 0.3, 0.4),
    scale=2.0,
    parent=-1,
) -> bytes:
    return struct.pack(
        "<8fi",
        *offset,
        *orientation,
        scale,
        parent,
    )


def _object_payload(*, matrix_number=0) -> tuple[bytes, int]:
    fixed = 0x48 if matrix_number == -1 else 0x28
    buf = bytearray(b"\0" * fixed)
    kind = _append_string(buf, "OBJECT")
    source = _append_string(buf, "SOURCE")
    resource = _append_string(buf, "tracks/test/object.meb")

    struct.pack_into("<III", buf, 0, kind, source, resource)
    struct.pack_into("<I", buf, 0x0C, 3)
    struct.pack_into("<4f", buf, 0x10, 4.0, 5.0, 6.0, 7.0)
    struct.pack_into("<bBBB", buf, 0x20, matrix_number, 0, 0, 0)
    struct.pack_into("<I", buf, 0x24, 0x110)

    if matrix_number == -1:
        struct.pack_into("<3f", buf, 0x28, 10.0, 11.0, 12.0)
        struct.pack_into("<4f", buf, 0x34, 0.2, 0.3, 0.4, 0.5)
        struct.pack_into("<f", buf, 0x44, 1.5)
    return bytes(buf), fixed


def _hierarchy_payload() -> tuple[bytes, int]:
    matrix_count = 2
    subobject_count = 2
    fixed = 0x24 + matrix_count * 0x24 + subobject_count * 4
    child0 = fixed
    child1 = child0 + 0x28
    record_end = child1 + 0x28

    buf = bytearray(b"\0" * record_end)
    kind = _append_string(buf, "HIERARCHY")
    source = _append_string(buf, "ROOT")
    object_kind = _append_string(buf, "OBJECT")
    child0_name = _append_string(buf, "CHILD_A")
    child1_name = _append_string(buf, "CHILD_B")
    resource = _append_string(buf, "tracks/test/child.meb")

    struct.pack_into("<II", buf, 0, kind, source)
    struct.pack_into("<I", buf, 0x0C, 1)
    struct.pack_into("<4f", buf, 0x10, 0.0, 0.0, 0.0, 20.0)
    struct.pack_into("<bBBB", buf, 0x20, 0, 0, matrix_count, subobject_count)
    buf[0x24:0x48] = _matrix(parent=-1)
    buf[0x48:0x6C] = _matrix(
        offset=(0.0, 0.0, 0.0),
        orientation=(0.0, 0.0, 0.0, 1.0),
        scale=1.0,
        parent=0,
    )
    struct.pack_into("<II", buf, 0x6C, child0, child1)

    for off, name in ((child0, child0_name), (child1, child1_name)):
        struct.pack_into("<III", buf, off, object_kind, name, resource)
        struct.pack_into("<I", buf, off + 0x0C, 1)
        struct.pack_into("<4f", buf, off + 0x10, 0.0, 0.0, 0.0, 1.0)
        struct.pack_into("<bBBB", buf, off + 0x20, 0, 0, 0, 0)
        struct.pack_into("<I", buf, off + 0x24, 0)

    return bytes(buf), record_end


def _lod_payload() -> tuple[bytes, int]:
    matrix_count = 1
    subobject_count = 2
    fixed = 0x24 + 0x24 + 8 + 8
    child0 = fixed
    child1 = child0 + 0x28
    record_end = child1 + 0x28

    buf = bytearray(b"\0" * record_end)
    kind = _append_string(buf, "LOD")
    source = _append_string(buf, "LOD_ROOT")
    object_kind = _append_string(buf, "OBJECT")
    child0_name = _append_string(buf, "LODA")
    child1_name = _append_string(buf, "LODB")
    resource = _append_string(buf, "tracks/test/lod.meb")

    struct.pack_into("<II", buf, 0, kind, source)
    struct.pack_into("<I", buf, 0x0C, 2)
    struct.pack_into("<4f", buf, 0x10, 0.0, 2.0, 3.0, 10.0)
    struct.pack_into("<bBBB", buf, 0x20, -1, 0, matrix_count, subobject_count)
    buf[0x24:0x48] = _matrix(parent=-1)
    struct.pack_into("<2f", buf, 0x48, 100.0, 200.0)
    struct.pack_into("<II", buf, 0x50, child0, child1)

    for off, name in ((child0, child0_name), (child1, child1_name)):
        struct.pack_into("<III", buf, off, object_kind, name, resource)
        struct.pack_into("<I", buf, off + 0x0C, 1)
        struct.pack_into("<4f", buf, off + 0x10, 0.0, 0.0, 0.0, 1.0)
        struct.pack_into("<bBBB", buf, off + 0x20, 0, 0, 0, 0)
        struct.pack_into("<I", buf, off + 0x24, 0)

    return bytes(buf), record_end


def test_object_kind_dispatch_and_runtime_wrapper_are_source_backed():
    payload, end = _object_payload()
    result = parse_sgb_object_payload(payload, end_offset=end)

    assert result["kind"]["text"] == "OBJECT"
    assert result["decoded"] is True
    assert result["instances"] == 3
    assert result["sphere"]["center_xyz"] == [4.0, 5.0, 6.0]
    assert result["sphere"]["radius"] == 7.0
    assert result["matrix_number"] == 0
    assert result["userflags"] == 0x110
    assert result["resource_filename"]["text"] == "tracks/test/object.meb"

    wrapper = result["runtime_wrapper"]
    assert wrapper["constructor"] == "FUN_00698dc0"
    assert wrapper["initializer"] == "FUN_00698dd0"
    assert wrapper["vtable"] == 0x00AF86B0
    assert wrapper["proven_fields"]["resource_object"] == 0x80
    assert wrapper["proven_fields"]["matrix_number"] == 0x84


def test_object_embedded_matrix_maps_xml_offset_orientation_scale():
    payload, end = _object_payload(matrix_number=-1)
    result = parse_sgb_object_payload(payload, end_offset=end)
    matrix = result["embedded_matrix"]

    assert matrix["offset_xyz"] == [10.0, 11.0, 12.0]
    assert matrix["orientation_xyzw"] == pytest.approx([0.2, 0.3, 0.4, 0.5])
    assert matrix["scale"] == 1.5
    assert matrix["runtime_offsets"] == {
        "orientation_wxyz": 0x88,
        "offset_xyz": 0x98,
        "scale": 0xA4,
    }


def test_matrix_record_semantics_and_runtime_copy_layout():
    record = _matrix()
    child = parse_matrix_records(record, 0, len(record), 1)[0]

    assert child["record_bytes"] == 0x24
    assert child["runtime_element_bytes"] == 0x28
    assert child["offset_xyz"] == [1.0, 2.0, 3.0]
    assert child["orientation_xyzw"] == pytest.approx([0.1, 0.2, 0.3, 0.4])
    assert child["scale"] == 2.0
    assert child["parent"] == -1
    assert child["runtime_destination_word_offsets"] == {
        "0x00": 6,
        "0x04": 3,
        "0x08": 4,
        "0x0c": 5,
        "0x10": 0,
        "0x14": 1,
        "0x18": 2,
        "0x1c": 7,
        "0x20": 8,
    }


def test_hierarchy_uses_matrix_and_subobject_counts_not_old_type_names():
    payload, end = _hierarchy_payload()
    result = parse_sgb_object_payload(payload, end_offset=end)

    assert result["kind"]["text"] == "HIERARCHY"
    assert result["matrix_number"] == 0
    assert result["matrix_count"] == 2
    assert result["subobject_count"] == 2
    assert len(result["matrix_records"]) == 2
    assert result["matrix_records"][1]["parent"] == 0
    assert result["subobject_absolute_offsets"] == [0x74, 0x9C]
    assert [row["report"]["kind"]["text"] for row in result["subobjects"]] == [
        "OBJECT",
        "OBJECT",
    ]

    wrapper = result["runtime_wrapper"]
    assert wrapper["constructor"] == "FUN_00698a20"
    assert wrapper["vtable"] == 0x00AF8620
    assert wrapper["proven_fields"]["subobject_count"] == 0x80
    assert wrapper["proven_fields"]["matrix_count"] == 0x84
    assert wrapper["proven_fields"]["runtime_matrix_array"] == 0x88
    assert wrapper["proven_fields"]["runtime_subobject_array"] == 0x8C
    assert wrapper["proven_fields"]["matrix_number"] == 0x94


def test_lod_kind_has_distances_and_recursive_subobjects():
    payload, end = _lod_payload()
    result = parse_sgb_object_payload(payload, end_offset=end)

    assert result["kind"]["text"] == "LOD"
    assert result["matrix_number"] == -1
    assert result["matrix_count"] == 1
    assert result["subobject_count"] == 2
    assert result["lod_distances"] == [100.0, 200.0]
    assert [row["report"]["kind"]["text"] for row in result["subobjects"]] == [
        "OBJECT",
        "OBJECT",
    ]

    wrapper = result["runtime_wrapper"]
    assert wrapper["constructor"] == "FUN_00698a90"
    assert wrapper["vtable"] == 0x00AF8660
    assert wrapper["proven_fields"]["lod_distances"] == 0x98


def test_relative_strings_use_explicit_sgb_base_not_payload_base():
    prefix = bytearray(b"X" * 64)
    payload, fixed_end = _object_payload()
    combined = prefix + payload

    # Rewrite the three relative strings to stay relative to the complete
    # combined SGB base rather than the object payload start.
    kind_rel = struct.unpack_from("<I", combined, 64)[0] + 64
    source_rel = struct.unpack_from("<I", combined, 68)[0] + 64
    resource_rel = struct.unpack_from("<I", combined, 72)[0] + 64
    struct.pack_into("<III", combined, 64, kind_rel, source_rel, resource_rel)

    result = parse_sgb_object_payload(
        bytes(combined),
        base_offset=64,
        end_offset=64 + fixed_end,
        relative_base=0,
    )
    assert result["kind"]["text"] == "OBJECT"
    assert result["source_string"]["text"] == "SOURCE"


def test_unknown_byte_21_stays_raw():
    payload, end = _object_payload()
    raw = bytearray(payload)
    raw[0x21] = 0x7A
    result = parse_sgb_object_payload(bytes(raw), end_offset=end)
    assert result["unknown_byte_21"] == 0x7A


def test_truncated_matrix_table_blocks_non_strict():
    payload, end = _hierarchy_payload()
    result = parse_sgb_object_payload(
        payload,
        end_offset=0x24 + 0x24,
        strict=False,
    )
    assert result["decoded"] is False
    assert result["status"] == "blocked"
    assert result["blockers"]


def test_invalid_bounds_raise():
    with pytest.raises(SGBObjectDecodeError):
        parse_sgb_object_payload(b"\0" * 20)
