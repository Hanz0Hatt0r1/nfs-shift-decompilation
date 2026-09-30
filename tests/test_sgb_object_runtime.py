import struct

import pytest

from sgb_object_runtime import (
    SGBObjectDecodeError,
    parse_sgb_object_payload,
)


def _append_string(raw: bytearray, text: str) -> int:
    offset = len(raw)
    raw += text.encode("utf-8") + b"\0"
    return offset


def _matrix(
    *,
    offset=(1.0, 2.0, 3.0),
    orientation=(4.0, 5.0, 6.0, 7.0),
    scale=8.0,
    parent=-1,
) -> bytes:
    return struct.pack(
        "<8fi",
        *offset,
        *orientation,
        scale,
        parent,
    )


def _object_payload(
    *,
    kind="OBJECT",
    source="SOURCE",
    aux="RESOURCE.meb",
    matrix_number=0,
    userflags=0x110,
) -> bytes:
    body_size = 0x48 if matrix_number == -1 else 0x28
    raw = bytearray(body_size)
    struct.pack_into("<I", raw, 0x0C, 2)  # instances
    raw[0x20] = matrix_number & 0xFF
    raw[0x22] = 0
    raw[0x23] = 0
    struct.pack_into("<I", raw, 0x24, userflags)
    if matrix_number == -1:
        struct.pack_into(
            "<8f",
            raw,
            0x28,
            10.0,
            11.0,
            12.0,
            1.0,
            2.0,
            3.0,
            4.0,
            0.5,
        )

    kind_offset = _append_string(raw, kind)
    source_offset = _append_string(raw, source)
    aux_offset = _append_string(raw, aux)
    struct.pack_into(
        "<III",
        raw,
        0,
        kind_offset,
        source_offset,
        aux_offset,
    )
    return bytes(raw)


def _hierarchy_payload(matrices=2):
    matrix_bytes = b"".join(
        _matrix(
            offset=(float(i), float(i + 1), float(i + 2)),
            orientation=(0.0, 0.0, 0.0, 1.0),
            scale=1.0,
            parent=-1 if i == 0 else 0,
        )
        for i in range(matrices)
    )
    raw = bytearray(0x24 + len(matrix_bytes))
    raw[0x20] = 0
    raw[0x22] = matrices
    raw[0x23] = 0
    raw[0x24:] = matrix_bytes

    kind_offset = _append_string(raw, "HIERARCHY")
    source_offset = _append_string(raw, "Root")
    aux_offset = _append_string(raw, "AUX")
    struct.pack_into(
        "<III",
        raw,
        0,
        kind_offset,
        source_offset,
        aux_offset,
    )
    return bytes(raw)


def _lod_payload_with_two_objects():
    # Common header + one matrix + two distances + two absolute-reference
    # dwords + two 0x28-byte OBJECT payloads.
    parent_prefix = 0x24 + 0x24 + 8 + 8
    child_size = 0x28
    child_a = parent_prefix
    child_b = child_a + child_size
    raw = bytearray(child_b + child_size)

    raw[0x20] = 0xFF  # MatrixNumber = -1
    raw[0x22] = 1     # matrices
    raw[0x23] = 2     # subobjects
    raw[0x24:0x48] = _matrix(
        offset=(100.0, 200.0, 300.0),
        orientation=(0.1, 0.2, 0.3, 0.4),
        scale=2.0,
        parent=-1,
    )
    struct.pack_into("<2f", raw, 0x48, 0.0, 250.0)
    struct.pack_into("<2I", raw, 0x50, child_a, child_b)

    for child, name in (
        (child_a, "LODA"),
        (child_b, "LODB"),
    ):
        struct.pack_into("<I", raw, child + 0x0C, 1)
        raw[child + 0x20] = 0
        raw[child + 0x22] = 0
        raw[child + 0x23] = 0
        struct.pack_into("<I", raw, child + 0x24, 0x100)

        kind_offset = _append_string(raw, "OBJECT")
        source_offset = _append_string(raw, name)
        aux_offset = _append_string(raw, f"{name}.meb")
        struct.pack_into(
            "<III",
            raw,
            child,
            kind_offset,
            source_offset,
            aux_offset,
        )

    kind_offset = _append_string(raw, "LOD")
    source_offset = _append_string(raw, "LOD0")
    struct.pack_into(
        "<III",
        raw,
        0,
        kind_offset,
        source_offset,
        0,
    )
    return bytes(raw)


def test_object_kind_dispatch_is_reconstructed():
    result = parse_sgb_object_payload(_object_payload())
    assert result["kind"]["text"] == "OBJECT"
    assert result["decoded"] is True
    assert result["kind_status"] == "recognized-binary-kind"


def test_runtime_wrapper_classes_include_binary_lod():
    lod = parse_sgb_object_payload(_lod_payload_with_two_objects())
    assert lod["runtime_wrapper"]["constructor"] == "FUN_00698a90"
    assert lod["runtime_wrapper"]["vtable"] == 0x00AF8660
    assert lod["runtime_wrapper"]["allocation_bytes"] == 0xA0
    assert lod["runtime_wrapper"]["proven_fields"]["subobjects"] == 0x80
    assert lod["runtime_wrapper"]["proven_fields"]["matrices"] == 0x84
    assert lod["runtime_wrapper"]["proven_fields"]["distance_array"] == 0x98

    hierarchy = parse_sgb_object_payload(_hierarchy_payload())
    assert hierarchy["runtime_wrapper"]["constructor"] == "FUN_00698a20"
    assert hierarchy["runtime_wrapper"]["vtable"] == 0x00AF8620
    assert hierarchy["runtime_wrapper"]["proven_fields"] == {
        "subobjects": 0x80,
        "matrices": 0x84,
        "runtime_matrix_array": 0x88,
        "runtime_subobject_array": 0x8C,
        "matrix_number": 0x94,
    }

    obj = parse_sgb_object_payload(_object_payload())
    assert obj["runtime_wrapper"]["constructor"] == "FUN_00698dc0"
    assert obj["runtime_wrapper"]["initializer"] == "FUN_00698dd0"
    assert obj["runtime_wrapper"]["vtable"] == 0x00AF86B0
    assert obj["runtime_wrapper"]["proven_fields"]["resource_object"] == 0x80


def test_damage_is_alternate_runtime_kind_not_binary_node_dispatch():
    result = parse_sgb_object_payload(
        _object_payload(kind="DAMAGE")
    )
    assert result["decoded"] is False
    assert result["kind_status"] == "alternate-runtime-kind-not-binary-node"
    assert result["runtime_wrapper"]["constructor"] == "FUN_00698b00"
    assert result["runtime_wrapper"]["binary_node_dispatch"] is False
    assert result["runtime_wrapper"]["alternate_loader"] == (
        "FUN_00699b10/FUN_0069b1c0"
    )
    assert result["runtime_wrapper"]["proven_fields"] == {
        "matrices": 0x80,
        "runtime_matrix_array": 0x84,
        "runtime_subobject_array": 0x88,
        "matrix_number": 0x90,
    }
    assert result["runtime_wrapper"]["field_evidence"] == {
        "source": "FUN_00699b10/FUN_0069b1c0",
        "path": "XML scene object loader only",
    }


def test_matrix_number_matrices_and_subobjects_use_proven_bytes():
    result = parse_sgb_object_payload(_lod_payload_with_two_objects())
    assert result["matrix_number"] == -1
    assert result["control_byte_21"] == 0
    assert result["control_byte_21_evidence"] == {
        "binary_consumer": "FUN_0069a6c0",
        "binary_consumer_status": "unconsumed",
        "xml_counterpart": None,
        "semantic_name": None,
    }
    assert result["matrices"] == 1
    assert result["subobjects"] == 2


def test_matrix_record_semantics_and_runtime_copy_order_are_source_backed():
    result = parse_sgb_object_payload(_hierarchy_payload(matrices=2))
    first = result["matrix_records"][0]

    assert first["record_bytes"] == 0x24
    assert first["runtime_element_bytes"] == 0x28
    assert first["offset_xyz"] == [0.0, 1.0, 2.0]
    assert first["orientation_serialized"] == [0.0, 0.0, 0.0, 1.0]
    assert first["orientation_runtime_order"] == [1.0, 0.0, 0.0, 0.0]
    assert first["scale"] == 1.0
    assert first["parent"] == -1
    assert first["runtime_copy_order"] == [6, 3, 4, 5, 0, 1, 2, 7, 8]
    assert first["runtime_destination_word_offsets"] == {
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


def test_lod_decodes_distance_table_and_recursive_object_references():
    result = parse_sgb_object_payload(_lod_payload_with_two_objects())

    assert result["lod_distances_serialized"] == [0.0, 250.0]
    assert len(result["subobject_references"]) == 2
    assert all(
        row["decoded"] is True
        for row in result["subobject_references"]
    )
    assert [
        row["report"]["kind"]["text"]
        for row in result["subobject_references"]
    ] == ["OBJECT", "OBJECT"]
    assert [
        row["report"]["source_string"]["text"]
        for row in result["subobject_references"]
    ] == ["LODA", "LODB"]


def test_object_explicit_matrix_is_decoded_when_matrix_number_is_minus_one():
    result = parse_sgb_object_payload(
        _object_payload(matrix_number=-1)
    )
    matrix = result["explicit_matrix"]
    assert matrix["offset_xyz"] == [10.0, 11.0, 12.0]
    assert matrix["orientation_serialized"] == [1.0, 2.0, 3.0, 4.0]
    assert matrix["orientation_runtime_order"] == [4.0, 1.0, 2.0, 3.0]
    assert matrix["scale"] == 0.5
    assert matrix["source"] == "FUN_00698f40/FUN_0069a6c0"


def test_hierarchy_matrix_table_truncation_blocks_non_strict():
    payload = _hierarchy_payload(matrices=2)
    # Keep the complete backing data so the SGB-base kind string still
    # resolves, but bound this object inside the second required matrix.
    result = parse_sgb_object_payload(
        payload,
        end_offset=0x24 + 0x24 + 8,
        reference_base_offset=0,
        strict=False,
    )
    assert result["decoded"] is False
    assert result["status"] == "blocked"
    assert any(
        reason.startswith("matrix-table:")
        for reason in result["blockers"]
    )


def test_invalid_bounds_raise():
    with pytest.raises(SGBObjectDecodeError):
        parse_sgb_object_payload(b"\0" * 20)
