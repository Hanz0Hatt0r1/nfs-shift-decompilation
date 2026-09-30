import struct

import pytest

from flat_runtime import FLATRuntimeDecodeError, parse_flat_runtime


def _leaf(
    index: int,
    object_handle: int = 0,
    *,
    include=(0, 0),
    exclude=(0, 0),
    sphere=(0.0, 0.0, 0.0, 0.0),
    unresolved=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
) -> bytes:
    words = [0] * 16
    words[0:2] = list(include)
    words[2:4] = list(exclude)
    for i, value in enumerate(sphere):
        words[4 + i] = struct.unpack("<I", struct.pack("<f", value))[0]
    for i, value in enumerate(unresolved):
        words[8 + i] = struct.unpack("<I", struct.pack("<f", value))[0]
    words[14] = object_handle
    words[15] = index
    return struct.pack("<16I", *words)


def _node(
    leaves: list[bytes],
    children: list[bytes] | None = None,
    marker: int = 1,
    *,
    aabb=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
) -> bytes:
    children = children or []
    body = b"".join(leaves) + b"".join(children)
    span = 0x20 + len(body)
    header = struct.pack("<6fI", *aabb, len(leaves))
    header += struct.pack("<I", (marker << 24) | span)
    return header + body


def _serialized_terminal_node(
    leaves: list[bytes],
    children: list[bytes] | None = None,
) -> bytes:
    children = children or []
    body = b"".join(leaves) + b"".join(children)
    span = 0x20 + len(body)
    header = struct.pack("<7I", 0, 0, 0, 0, 0, 0, len(leaves))
    header += struct.pack("<i", -span)
    return header + body


def test_flat_header_and_leaf_layout():
    data = _node([_leaf(7)], marker=1)
    report = parse_flat_runtime(data)
    assert report["ready"] is True
    assert report["root"]["direct_record_count"] == 1
    assert report["root"]["records"][0]["runtime_index"] == 7
    assert report["root"]["span_bytes"] == 0x60


def test_flat_leaf_exposes_object_handle_and_child_index():
    data = _node([_leaf(11, 0x12345678)], marker=1)
    record = parse_flat_runtime(data)["root"]["records"][0]
    assert record["object_handle"] == 0x12345678
    assert record["child_index"] == 11
    assert record["runtime_index"] == 11
    assert record["index_word"] == 11
    assert record["direct_object_pointer_word"] == 0x12345678
    consumer = record["runtime_consumer_metadata"]
    assert consumer["direct_object_pointer_offset"] == 0x38
    assert consumer["runtime_index_offset"] == 0x3C
    assert consumer["dispatch"]["function"] == "FUN_006af5a0"
    assert consumer["dispatch"]["secondary_table_vfunc_offset"] == 0x08
    assert consumer["recursive_lookup"]["function"] == (
        "FUN_006af640 -> FUN_006b0440"
    )
    assert consumer["recursive_lookup"]["tree_order"] == (
        "child-nodes-before-direct-records"
    )
    assert consumer["teardown"]["function"] == "FUN_006af830"
    assert consumer["teardown"]["fallback_direct_pointer"]["refcount_offset"] == 0x20
    assert consumer["teardown"]["fallback_direct_pointer"]["destroy_vfunc_offset"] == 0x10


def test_flat_leaf_decodes_source_backed_filter_masks_and_sphere():
    data = _node([
        _leaf(
            5,
            include=(0x00000001, 0x80000000),
            exclude=(0x00000010, 0x00000020),
            sphere=(1.25, -2.5, 3.75, 9.5),
            unresolved=(-1.0, -2.0, -3.0, 4.0, 5.0, 6.0),
        )
    ])
    leaf = parse_flat_runtime(data)["root"]["records"][0]

    assert leaf["filter_masks"]["include_words"] == [
        0x00000001,
        0x80000000,
    ]
    assert leaf["filter_masks"]["exclude_words"] == [
        0x00000010,
        0x00000020,
    ]
    assert leaf["filter_masks"]["include_offset"] == 0x00
    assert leaf["filter_masks"]["exclude_offset"] == 0x08
    assert leaf["bounding_sphere"]["center_xyz"] == pytest.approx(
        [1.25, -2.5, 3.75]
    )
    assert leaf["bounding_sphere"]["radius"] == pytest.approx(9.5)
    assert leaf["bounding_sphere"]["source_offset"] == 0x10
    assert leaf["unresolved_spatial_words_20_34"]["semantic_status"] == (
        "unresolved"
    )
    assert leaf["unresolved_spatial_words_20_34"]["float_view"] == pytest.approx(
        [-1.0, -2.0, -3.0, 4.0, 5.0, 6.0]
    )

    consumer = leaf["runtime_consumer_metadata"]
    assert consumer["filter_mask_query"]["include_offsets"] == [0x00, 0x04]
    assert consumer["filter_mask_query"]["exclude_offsets"] == [0x08, 0x0C]
    assert consumer["bounding_sphere_query"]["center_offsets"] == [
        0x10,
        0x14,
        0x18,
    ]
    assert consumer["bounding_sphere_query"]["radius_offset"] == 0x1C


def test_flat_node_decodes_source_backed_aabb():
    report = parse_flat_runtime(
        _node(
            [_leaf(0)],
            aabb=(-10.0, -20.0, -30.0, 40.0, 50.0, 60.0),
        )
    )
    aabb = report["root"]["aabbox"]

    assert aabb["min_xyz"] == pytest.approx([-10.0, -20.0, -30.0])
    assert aabb["max_xyz"] == pytest.approx([40.0, 50.0, 60.0])
    assert aabb["source_offsets"] == {
        "min_xyz": 0x00,
        "max_xyz": 0x0C,
    }
    assert aabb["source"]["runtime_builder"] == "FUN_00689db0"


def test_flat_leaf_exposes_runtime_index_table_geometry():
    data = _node([_leaf(11, 0x12345678)], marker=1)
    links = parse_flat_runtime(data)["root"]["records"][0]["runtime_link_metadata"]
    assert links["index_word_offset"] == 0x3C
    assert links["index"] == 11
    assert links["primary_table"]["stride"] == 0x28
    assert links["primary_table"]["value_offset"] == 0x20
    assert links["primary_table"]["slot_offset"] == 0x20 + 11 * 0x28
    assert links["secondary_table"]["stride"] == 0x40
    assert links["secondary_table"]["node_pointer_offset"] == 0x30
    assert links["secondary_table"]["record_pointer_offset"] == 0x34
    assert links["secondary_table"]["primary_slot_pointer_offset"] == 0x38
    assert links["secondary_table"]["slot_offset"] == 11 * 0x40


def test_nested_flat_nodes_follow_low24_span():
    child = _node([_leaf(9)], marker=1)
    root = _node([], [child], marker=1)
    report = parse_flat_runtime(root)
    assert report["stats"]["tree_nodes"] == 2
    assert report["stats"]["leaf_records"] == 1
    assert report["stats"]["max_depth"] == 1


def test_invalid_span_is_rejected():
    data = struct.pack("<8I", 0, 0, 0, 0, 0, 0, 2, 0x100)
    with pytest.raises(FLATRuntimeDecodeError):
        parse_flat_runtime(data)


def test_non_strict_returns_blocker():
    result = parse_flat_runtime(b"\\0" * 8, strict=False)
    assert result["ready"] is False
    assert result["status"] == "blocked"
    assert result["blockers"]



def test_serialized_negative_terminal_span_is_normalized_like_runtime():
    data = _serialized_terminal_node([_leaf(3)])
    report = parse_flat_runtime(data)
    root = report["root"]

    assert report["ready"] is True
    assert root["serialized_span_signed"] == -len(data)
    assert root["serialized_terminal_encoding"] is True
    assert root["span_normalization_applied"] is True
    assert root["span_bytes"] == len(data)
    assert root["depth_marker"] == 1
    assert root["normalized_span_word"] == 0x01000000 | len(data)


def test_nested_serialized_terminal_markers_match_fun_006af6c0_depth_delta():
    child = _serialized_terminal_node([_leaf(4)])
    root = _serialized_terminal_node([], [child])
    report = parse_flat_runtime(root)

    assert report["stats"]["tree_nodes"] == 2
    assert report["root"]["depth_marker"] == 1
    assert report["root"]["children"][0]["depth_marker"] == 2
    assert report["root"]["children"][0]["serialized_terminal_encoding"] is True


def test_negative_serialized_span_blocks_when_normalization_disabled():
    data = _serialized_terminal_node([_leaf(3)])
    with pytest.raises(FLATRuntimeDecodeError):
        parse_flat_runtime(
            data,
            normalize_signed_terminal_spans=False,
        )
