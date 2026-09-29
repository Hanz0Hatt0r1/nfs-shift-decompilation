import struct

import pytest

from sgb_runtime import SGBRuntimeDecodeError, parse_sgb_runtime


def _chunk(tag: str, payload: bytes) -> bytes:
    return tag[::-1].encode("ascii") + struct.pack("<I", 8 + len(payload)) + payload


def _header(flags: int = 0) -> bytes:
    return b" \x42\x47\x53" + struct.pack("<III", 0x10, flags, 0)


def test_header_and_end_chunk():
    report = parse_sgb_runtime(_header() + _chunk("END ", b""))
    assert report["ready"] is True
    assert report["header"]["word_1"] == 0x10
    assert report["chunks"][0]["tag"] == "END "


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
    record = struct.pack("<IIIIIIII", 32, 0, 32, 0, 0, 2, 0, 0)
    data = _header() + _chunk("NODE", struct.pack("<I", 1) + record) + _chunk("END ", b"")
    row = parse_sgb_runtime(data)["chunks"][0]["records"][0]
    assert row["stride"] == 32
    assert row["instances"] == 2
    assert row["flags"]["raw"] == 0
    assert row["flags"]["bit0"] is False
    assert row["flags"]["bit1"] is False
    assert row["flags"]["bit2"] is False
    assert row["variation_index"] == 0

def test_node_runtime_wrapper_mapping_is_source_backed():
    record = struct.pack("<IIIIIIII", 32, 0, 32, 0x100, 0x120, 0x140, 3, 0x180)
    data = _header() + _chunk("NODE", struct.pack("<I", 1) + record) + _chunk("END ", b"")
    row = parse_sgb_runtime(data, strict=False)["chunks"][0]["records"][0]
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


def test_summ_and_occl_fixed_record_shape():
    # Two zero relative offsets plus four vec3 values.
    record = struct.pack("<14I", 0, 0, *([0] * 12))
    for tag in ("SUMM", "OCCL"):
        data = _header() + _chunk(tag, struct.pack("<I", 1) + record) + _chunk("END ", b"")
        row = parse_sgb_runtime(data)["chunks"][0]["records"][0]
        assert row["record_bytes"] == 56


def test_summ_runtime_wrapper_mapping_is_source_backed():
    record = struct.pack(
        "<14I",
        56, 0, 64, 72, 80, 3, 7, 0x030201, 0, 0, 0, 0, 0, 0
    )
    data = _header() + _chunk(
        "SUMM", struct.pack("<I", 1) + record
    ) + _chunk("END ", b"")
    row = parse_sgb_runtime(data)["chunks"][0]["records"][0]
    wrapper = row["runtime_wrapper"]
    assert wrapper["vtable"] == 0x00AF78EC
    assert wrapper["instance_bytes"] == 0x38
    assert wrapper["source_field_offsets"] == {
        "name": 0x08,
        "resource": 0x0C,
        "variation_palette": 0x10,
        "instances": 0x14,
        "flags": 0x18,
        "variation_index": 0x1A,
        "object_payload": 0x1C,
    }
    assert wrapper["runtime_field_offsets"]["payload"] == 0x08
    assert wrapper["runtime_field_offsets"]["resource"] == 0x18
    assert wrapper["runtime_field_offsets"]["variation_palette"] == 0x1C
    assert wrapper["runtime_field_offsets"]["variation_index"] == 0x20
    assert wrapper["runtime_field_offsets"]["instances"] == 0x24
    assert wrapper["runtime_field_offsets"]["flag_bit0"] == 0x15
    assert wrapper["runtime_field_offsets"]["flag_bit1"] == 0x16
    assert wrapper["runtime_field_offsets"]["flag_bit2"] == 0x17
    assert wrapper["runtime_field_offsets"]["name_hash_lo"] == 0x28
    assert wrapper["runtime_field_offsets"]["name_hash_hi"] == 0x2C
    assert wrapper["name_hash_producer"] == "FUN_0064eba0"
    assert wrapper["name_hash_resolved"] is False


def test_truncated_chunk_blocks_non_strict():
    data = _header() + b"EDNE" + struct.pack("<I", 64)
    result = parse_sgb_runtime(data, strict=False)
    assert result["ready"] is False
    assert any(x.startswith("chunk-truncated") for x in result["blockers"])


def test_invalid_magic_rejected():
    with pytest.raises(SGBRuntimeDecodeError):
        parse_sgb_runtime(b"not-sgb")


def test_node_object_payload_is_decoded_when_bounded():
    object_header = struct.pack("<9I", 40, 48, 56, 0, 0, 0, 0, 0, 0)
    object_data = object_header + b"\0\0\0\0" + b"OBJECT\0SOURCE\0AUX\0"
    node_record = struct.pack("<IIIIIIII", 32, 0, 48, 0, 0, 1, 0, 44)
    payload = struct.pack("<I", 1) + node_record + object_data
    data = _header() + _chunk("NODE", payload) + _chunk("END ", b"")
    row = parse_sgb_runtime(data)["chunks"][0]["records"][0]
    assert row["object_payload"]["decoded"] is True
    assert row["object_payload"]["report"]["kind"]["text"] == "OBJECT"


def test_flat_chunk_decodes_embedded_runtime_tree():
    leaf = struct.pack("<15I", *([0] * 15)) + struct.pack("<I", 5)
    flat_body = struct.pack("<7I", 0, 0, 0, 0, 0, 0, 1)
    flat_body += struct.pack("<I", 0x1000000 | (0x20 + 0x40)) + leaf
    data = _header() + _chunk("FLAT", struct.pack("<I", 1) + flat_body) + _chunk("END ", b"")
    flat = parse_sgb_runtime(data)["chunks"][0]["flat_runtime"]
    assert flat["ready"] is True
    assert flat["stats"]["leaf_records"] == 1
    assert flat["root"]["records"][0]["index_word"] == 5



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
