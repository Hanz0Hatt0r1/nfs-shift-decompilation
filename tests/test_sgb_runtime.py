import struct

import pytest

from sgb_runtime import SGBRuntimeDecodeError, parse_sgb_runtime


def _chunk(tag: str, payload: bytes) -> bytes:
    return tag[::-1].encode("ascii") + struct.pack("<I", 8 + len(payload)) + payload


def _header(flags: int = 0) -> bytes:
    return b" \x42\x47\x53" + struct.pack("<III", 0x10, flags, 0)


def _node_sgb() -> bytes:
    # One retail-layout NODE record: 0x1c metadata followed by an inline
    # 0x28-byte OBJECT payload. Strings live after the END chunk and all
    # relative offsets are from the complete SGB base.
    stride = 0x1C + 0x28
    node_payload = struct.pack("<I", 1) + b"\0" * stride
    buf = bytearray(
        _header()
        + _chunk("NODE", node_payload)
        + _chunk("END ", b"")
    )

    def add(text: str) -> int:
        offset = len(buf)
        buf.extend(text.encode("utf-8") + b"\0")
        return offset

    node_name = add("NODE_NAME")
    node_resource = add("NODE_RESOURCE")
    palette = add("PALETTE")
    kind = add("OBJECT")
    source = add("OBJECT_SOURCE")
    meb = add("tracks/test/object.meb")

    record = 16 + 8 + 4
    obj = record + 0x1C
    struct.pack_into("<I", buf, record + 0x00, stride)
    struct.pack_into("<I", buf, record + 0x04, 0)
    struct.pack_into("<I", buf, record + 0x08, node_name)
    struct.pack_into("<I", buf, record + 0x0C, node_resource)
    struct.pack_into("<I", buf, record + 0x10, palette)
    struct.pack_into("<I", buf, record + 0x14, 2)
    buf[record + 0x18] = 7
    struct.pack_into("<h", buf, record + 0x1A, 3)

    struct.pack_into("<III", buf, obj, kind, source, meb)
    struct.pack_into("<I", buf, obj + 0x0C, 2)
    struct.pack_into("<4f", buf, obj + 0x10, 0.0, 1.0, 2.0, 3.0)
    struct.pack_into("<bBBB", buf, obj + 0x20, 0, 0, 0, 0)
    struct.pack_into("<I", buf, obj + 0x24, 0x110)
    return bytes(buf)


def _summ_sgb() -> bytes:
    stride = 0x1C + 0x28
    payload = struct.pack("<I", 1) + b"\0" * stride
    buf = bytearray(
        _header()
        + _chunk("SUMM", payload)
        + _chunk("END ", b"")
    )

    def add(text: str) -> int:
        offset = len(buf)
        buf.extend(text.encode("utf-8") + b"\0")
        return offset

    wrapper_name = add("SUMM_NAME")
    wrapper_resource = add("SUMM_RESOURCE")
    palette = add("SUMM_PALETTE")
    kind = add("OBJECT")
    source = add("SUMM_OBJECT")
    meb = add("tracks/test/summ_object.meb")

    record = 16 + 8 + 4
    obj = record + 0x1C
    struct.pack_into("<I", buf, record + 0x00, stride)
    struct.pack_into("<I", buf, record + 0x04, 0)
    struct.pack_into("<I", buf, record + 0x08, wrapper_name)
    struct.pack_into("<I", buf, record + 0x0C, wrapper_resource)
    struct.pack_into("<I", buf, record + 0x10, palette)
    struct.pack_into("<I", buf, record + 0x14, 3)
    buf[record + 0x18] = 5
    struct.pack_into("<h", buf, record + 0x1A, -2)

    struct.pack_into("<III", buf, obj, kind, source, meb)
    struct.pack_into("<I", buf, obj + 0x0C, 1)
    buf[obj + 0x20] = 0
    buf[obj + 0x22] = 0
    buf[obj + 0x23] = 0
    struct.pack_into("<I", buf, obj + 0x24, 0x100)
    return bytes(buf)


def test_header_and_end_chunk():
    report = parse_sgb_runtime(_header() + _chunk("END ", b""))
    assert report["ready"] is True
    assert report["header"]["word_1"] == 0x10
    assert report["chunks"][0]["tag"] == "END "
    assert report["post_end_reference_bytes"] == 0


def test_post_end_reference_arena_is_not_mislabeled_as_trailing_garbage():
    data = _header() + _chunk("END ", b"") + b"OBJECT\0RESOURCE\0"
    report = parse_sgb_runtime(data)
    assert report["ready"] is True
    assert report["trailing_bytes"] == 0
    assert report["post_end_reference_bytes"] == len(b"OBJECT\0RESOURCE\0")


def test_part_record_uses_exact_source_layout_and_one_based_child_table():
    record = struct.pack(
        "<I6f5I",
        7,
        -1.0, -2.0, -3.0,
        1.0, 2.0, 3.0,
        10, 11, 12, 13,
        2,
    )
    record += struct.pack("<II", 99, 100)
    payload = struct.pack("<I", 1) + record
    data = _header() + _chunk("PART", payload) + _chunk("END ", b"")
    row = parse_sgb_runtime(data)["chunks"][0]["records"][0]

    assert row["partition_id"] == 7
    assert row["record_bytes_minimum"] == 48
    assert row["aabbox_min"] == [-1.0, -2.0, -3.0]
    assert row["aabbox_max"] == [1.0, 2.0, 3.0]
    assert row["child_partition_ids"] == [10, 11, 12, 13]
    assert row["child_partition_table_present"] is True
    assert row["child_object_count"] == 2
    assert row["child_object_indices"] == [99, 100]
    assert row["child_object_lookup_indices_u32"] == [98, 99]
    assert row["child_object_lookup_transform"] == (
        "(source_id - 1) & 0xffffffff"
    )

    runtime = row["runtime_partition_tree"]
    assert runtime["consumer"] == "FUN_0068a360"
    assert runtime["insert_consumer"] == "FUN_00689a30"
    assert runtime["node_allocator"] == "FUN_00688ef0 -> FUN_006886a0"
    assert runtime["node_vtable"] == 0x00AF7A68
    assert runtime["manager_root_field_offset"] == 0x28
    assert runtime["runtime_node_field_offsets"]["aabbox_min"] == 0x04
    assert runtime["runtime_node_field_offsets"]["aabbox_max"] == 0x10
    assert runtime["runtime_node_field_offsets"]["child_partition_slots"] == [
        0x1C, 0x20, 0x24, 0x28
    ]
    assert runtime["runtime_node_field_offsets"]["child_object_container"] == 0x34
    assert runtime["runtime_node_field_offsets"]["child_partition_id_mask"] == 0x58
    assert runtime["child_partition_mask_initial"] == 0x0F
    assert runtime["child_object_resolution"]["reference_transform"] == (
        "source_id - 1"
    )
    assert runtime["child_object_resolution"]["lookup_argument_type"] == "uint32"
    assert runtime["child_object_resolution"]["resolved_wrapper_partition_bounds_write_offset"] == 0x30


def test_node_header_and_flags():
    row = parse_sgb_runtime(_node_sgb())["chunks"][0]["records"][0]
    assert row["stride"] == 0x44
    assert row["metadata_bytes"] == 0x1C
    assert row["instances"] == 2
    assert row["flags"]["raw"] == 7
    assert row["flags"]["bit0"] is True
    assert row["flags"]["bit1"] is True
    assert row["flags"]["bit2"] is True
    assert row["variation_index"] == 3
    assert row["name"]["text"] == "NODE_NAME"
    assert row["resource"]["text"] == "NODE_RESOURCE"
    assert row["variation_palette_file"]["text"] == "PALETTE"


def test_node_runtime_wrapper_mapping_is_source_backed():
    row = parse_sgb_runtime(_node_sgb())["chunks"][0]["records"][0]
    wrapper = row["runtime_wrapper"]
    assert wrapper["vtable"] == 0x00AF78EC
    assert wrapper["payload_field_offset"] == 0x08
    assert wrapper["resource_field_offset"] == 0x18
    assert wrapper["variation_palette_field_offset"] == 0x1C
    assert wrapper["variation_index_field_offset"] == 0x20
    assert wrapper["instances_field_offset"] == 0x24
    assert wrapper["flag_byte_offsets"] == {"bit0": 0x15, "bit1": 0x16, "bit2": 0x17}
    assert wrapper["name_hash_field_offset"] == 0x28
    assert wrapper["name_hash_field_size"] == 0x08
    assert "record +0x1c inline" in wrapper["source_mapping"]["object_payload"]


def test_occl_fixed_record_shape():
    record = struct.pack("<14I", 0, 0, *([0] * 12))
    data = (
        _header()
        + _chunk("OCCL", struct.pack("<I", 1) + record)
        + _chunk("END ", b"")
    )
    row = parse_sgb_runtime(data)["chunks"][0]["records"][0]
    assert row["record_bytes"] == 56


def test_summ_uses_variable_stride_wrapper_and_inline_object_payload():
    row = parse_sgb_runtime(_summ_sgb())["chunks"][0]["records"][0]

    assert row["stride"] == 0x44
    assert row["metadata_bytes"] == 0x1C
    assert row["name"]["text"] == "SUMM_NAME"
    assert row["resource"]["text"] == "SUMM_RESOURCE"
    assert row["variation_palette_file"]["text"] == "SUMM_PALETTE"
    assert row["instances"] == 3
    assert row["flags"]["raw"] == 5
    assert row["variation_index"] == -2

    payload = row["object_payload"]
    assert payload["layout"] == "inline-after-node-metadata"
    assert payload["inline_offset"] == 0x1C
    assert payload["decoded"] is True
    assert payload["report"]["kind"]["text"] == "OBJECT"
    assert payload["report"]["source_string"]["text"] == "SUMM_OBJECT"
    assert payload["report"]["resource_filename"]["text"] == (
        "tracks/test/summ_object.meb"
    )

    wrapper = row["runtime_wrapper"]
    assert wrapper["vtable"] == 0x00AF78EC
    assert wrapper["instance_bytes"] == 0x38
    assert wrapper["source_field_offsets"]["object_payload"] == 0x1C
    assert wrapper["runtime_field_offsets"]["payload"] == 0x08
    assert wrapper["object_payload_inline_offset"] == 0x1C
    assert wrapper["record_stride_source"] == "record +0x00"


def test_truncated_chunk_blocks_non_strict():
    data = _header() + b"EDNE" + struct.pack("<I", 64)
    result = parse_sgb_runtime(data, strict=False)
    assert result["ready"] is False
    assert any(x.startswith("chunk-truncated") for x in result["blockers"])


def test_invalid_magic_rejected():
    with pytest.raises(SGBRuntimeDecodeError):
        parse_sgb_runtime(b"not-sgb")


def test_node_object_payload_is_inline_and_decoded_against_sgb_base():
    row = parse_sgb_runtime(_node_sgb())["chunks"][0]["records"][0]
    payload = row["object_payload"]
    assert payload["layout"] == "inline-after-node-metadata"
    assert payload["inline_offset"] == 0x1C
    assert payload["decoded"] is True
    assert payload["report"]["kind"]["text"] == "OBJECT"
    assert payload["report"]["source_string"]["text"] == "OBJECT_SOURCE"
    assert payload["report"]["resource_filename"]["text"] == (
        "tracks/test/object.meb"
    )


def test_flat_chunk_decodes_embedded_runtime_tree():
    leaf = struct.pack("<15I", *([0] * 15)) + struct.pack("<I", 5)
    flat_body = struct.pack("<7I", 0, 0, 0, 0, 0, 0, 1)
    flat_body += struct.pack("<I", 0x1000000 | (0x20 + 0x40)) + leaf
    data = _header() + _chunk("FLAT", struct.pack("<I", 1) + flat_body) + _chunk("END ", b"")
    flat = parse_sgb_runtime(data)["chunks"][0]["flat_runtime"]
    assert flat["ready"] is True
    assert flat["stats"]["leaf_records"] == 1
    assert flat["root"]["records"][0]["index_word"] == 5


def test_flat_chunk_normalizes_signed_terminal_span_when_header_bit2_clear():
    leaf = struct.pack("<15I", *([0] * 15)) + struct.pack("<I", 7)
    span = 0x20 + 0x40
    flat_body = struct.pack("<7I", 0, 0, 0, 0, 0, 0, 1)
    flat_body += struct.pack("<i", -span) + leaf
    data = (
        _header(flags=0)
        + _chunk("FLAT", struct.pack("<I", 1) + flat_body)
        + _chunk("END ", b"")
    )
    chunk = parse_sgb_runtime(data)["chunks"][0]
    flat = chunk["flat_runtime"]

    assert chunk["flat_span_normalization"]["header_flag_bit2"] is False
    assert chunk["flat_span_normalization"][
        "normalize_signed_terminal_spans"
    ] is True
    assert flat["root"]["serialized_span_signed"] == -span
    assert flat["root"]["span_bytes"] == span
    assert flat["root"]["depth_marker"] == 1
    assert flat["root"]["records"][0]["runtime_index"] == 7


def test_flat_chunk_bit2_set_uses_pre_normalized_span_without_sign_rewrite():
    leaf = struct.pack("<15I", *([0] * 15)) + struct.pack("<I", 8)
    span = 0x20 + 0x40
    flat_body = struct.pack("<7I", 0, 0, 0, 0, 0, 0, 1)
    flat_body += struct.pack("<I", 0x01000000 | span) + leaf
    data = (
        _header(flags=4)
        + _chunk("FLAT", struct.pack("<I", 1) + flat_body)
        + _chunk("END ", b"")
    )
    chunk = parse_sgb_runtime(data)["chunks"][0]

    assert chunk["flat_span_normalization"]["header_flag_bit2"] is True
    assert chunk["flat_span_normalization"][
        "normalize_signed_terminal_spans"
    ] is False
    assert chunk["flat_runtime"]["root"]["span_normalization_applied"] is False



def test_occl_runtime_object_maps_named_corners_and_wrapper():
    record = struct.pack(
        "<II12f",
        0,
        0,
        1.0, 2.0, 3.0,
        4.0, 5.0, 6.0,
        7.0, 8.0, 9.0,
        10.0, 11.0, 12.0,
    )
    data = (
        _header()
        + _chunk("OCCL", struct.pack("<I", 1) + record)
        + _chunk("END ", b"")
    )
    report = parse_sgb_runtime(data)
    row = report["chunks"][0]["records"][0]

    assert report["header"]["flag_bits"]["bit1"] is False
    assert row["position_tl"] == [1.0, 2.0, 3.0]
    assert row["position_tr"] == [4.0, 5.0, 6.0]
    assert row["position_bl"] == [7.0, 8.0, 9.0]
    assert row["position_br"] == [10.0, 11.0, 12.0]

    runtime = row["runtime_object"]
    assert runtime["constructor"] == "FUN_006b43d0"
    assert runtime["xml_constructor"] == "FUN_006a3c40"
    assert runtime["vtable"] == 0x00AFA2FC
    assert runtime["instance_bytes"] == 0x120
    assert runtime["source_field_offsets"] == {
        "name": 0x00,
        "resource": 0x04,
        "position_tl": 0x08,
        "position_tr": 0x14,
        "position_bl": 0x20,
        "position_br": 0x2C,
    }
    assert runtime["runtime_field_offsets"]["name_resource_descriptor"] == 0x60
    assert runtime["runtime_field_offsets"]["position_tl"] == 0x90
    assert runtime["runtime_field_offsets"]["position_tr"] == 0xA0
    assert runtime["runtime_field_offsets"]["position_bl"] == 0xB0
    assert runtime["runtime_field_offsets"]["position_br"] == 0xC0
    assert runtime["runtime_field_offsets"]["secondary_matrix"] == 0xD0
    assert runtime["runtime_field_offsets"]["flag_byte"] == 0x110
    assert runtime["vector_copy"]["position_tl"] == [1.0, 2.0, 3.0, 1.0]
    assert runtime["vector_copy"]["position_br"] == [10.0, 11.0, 12.0, 1.0]

    admission = row["runtime_admission"]
    assert admission["mode"] == "per-record-wrapper"
    assert admission["header_flag_bit1"] is False
    assert admission["wrapper"]["vtable"] == 0x00AF78EC
    assert admission["wrapper"]["instance_bytes"] == 0x38
    assert admission["wrapper"]["payload_field_offset"] == 0x08
    assert admission["batch_sink"] is None


def test_occl_header_bit1_selects_batched_runtime_admission():
    record = struct.pack("<II12f", 0, 0, *([0.0] * 12))
    data = (
        _header(flags=2)
        + _chunk("OCCL", struct.pack("<I", 1) + record)
        + _chunk("END ", b"")
    )
    report = parse_sgb_runtime(data)
    row = report["chunks"][0]["records"][0]

    assert report["header"]["flag_bits"]["bit1"] is True
    assert row["runtime_admission"] == {
        "header_flag_bit1": True,
        "mode": "batched-object-registration",
        "wrapper": None,
        "batch_sink": "FUN_004f5e60 -> FUN_0068b5a0",
    }


def test_occl_is_not_mislabeled_as_summ_wrapper():
    record = struct.pack("<II12f", 0, 0, *([0.0] * 12))
    data = (
        _header()
        + _chunk("OCCL", struct.pack("<I", 1) + record)
        + _chunk("END ", b"")
    )
    row = parse_sgb_runtime(data)["chunks"][0]["records"][0]
    assert "runtime_wrapper" not in row
    assert row["runtime_object"]["constructor"] == "FUN_006b43d0"



def test_part_subsequent_record_maps_partition_id_to_runtime_child_slot():
    root = struct.pack(
        "<I6f5I",
        1,
        -10.0, -10.0, -10.0,
        10.0, 10.0, 10.0,
        42, 0, 0, 0,
        0,
    )
    child = struct.pack(
        "<I6f5I",
        42,
        -5.0, -5.0, -5.0,
        5.0, 5.0, 5.0,
        0, 0, 0, 0,
        0,
    )
    payload = struct.pack("<I", 2) + root + child
    data = _header() + _chunk("PART", payload) + _chunk("END ", b"")
    rows = parse_sgb_runtime(data)["chunks"][0]["records"]

    assert [row["partition_id"] for row in rows] == [1, 42]
    assert rows[0]["runtime_partition_tree"]["root_record"] is True
    assert rows[0]["runtime_partition_tree"]["root_creation"] == (
        "FUN_0068a360 -> FUN_00688ef0"
    )
    assert rows[1]["runtime_partition_tree"]["root_record"] is False
    assert rows[1]["runtime_partition_tree"]["subsequent_insertion"] == (
        "FUN_0068a360 -> FUN_00689a30"
    )

    slot = rows[0]["runtime_partition_tree"]["child_partition_slots"][0]
    assert slot == {
        "slot": 0,
        "source_partition_id": 42,
        "runtime_field_offset": 0x1C,
        "initial_state": "unresolved-partition-id",
        "mask_bit": 0,
        "insert_consumer": "FUN_00689a30",
        "resolved_state": "runtime-partition-node-pointer",
    }
    assert "replaces the source id with a child-node pointer" in (
        rows[0]["runtime_partition_tree"]["child_partition_resolution"]
    )


def test_part_child_object_reference_zero_preserves_runtime_underflow_lookup():
    record = struct.pack(
        "<I6f5I",
        7,
        -1.0, -1.0, -1.0,
        1.0, 1.0, 1.0,
        0, 0, 0, 0,
        1,
    )
    record += struct.pack("<I", 0)
    data = _header() + _chunk(
        "PART", struct.pack("<I", 1) + record
    ) + _chunk("END ", b"")

    row = parse_sgb_runtime(data)["chunks"][0]["records"][0]
    assert row["child_object_indices"] == [0]
    assert row["child_object_lookup_indices_u32"] == [0xFFFFFFFF]


def test_part_child_object_dispatch_keeps_kind_codes_numeric():
    record = struct.pack(
        "<I6f5I",
        7,
        -1.0, -1.0, -1.0,
        1.0, 1.0, 1.0,
        0, 0, 0, 0,
        1,
    )
    record += struct.pack("<I", 1)
    data = _header() + _chunk(
        "PART", struct.pack("<I", 1) + record
    ) + _chunk("END ", b"")
    row = parse_sgb_runtime(data)["chunks"][0]["records"][0]
    dispatch = row["runtime_partition_tree"][
        "child_object_resolution"
    ]["virtual_kind_dispatch"]

    assert dispatch["vfunc_offset"] == 0x04
    assert dispatch["observed_raw_codes"] == [1, 3, 4]
    assert dispatch["code_3_behavior"] == "append wrapper to manager +0x58"
    assert dispatch["code_4_behavior"] == "append wrapper to partition node +0x34"
