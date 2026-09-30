from sgb_part_flat_bridge import (
    FORMAT,
    build_scene_wrapper_catalog,
    build_sgb_part_flat_bridge,
)


def _node_record(index, kind="OBJECT"):
    return {
        "index": index,
        "offset": 0x100 + index * 0x40,
        "runtime_wrapper": {"vtable": 0x00AF78EC},
        "object_payload": {
            "report": {
                "kind": {"text": kind},
            }
        },
    }


def _occl_record(index, *, batched=False):
    return {
        "index": index,
        "offset": 0x40 + index * 0x38,
        "runtime_admission": {
            "mode": (
                "batched-object-registration"
                if batched
                else "per-record-wrapper"
            ),
            "wrapper": (
                None if batched else {"vtable": 0x00AF78EC}
            ),
        },
    }


def _part(
    index,
    partition_id,
    *,
    children=(0, 0, 0, 0),
    objects=(),
):
    return {
        "index": index,
        "partition_id": partition_id,
        "aabbox_min": [-1.0, -2.0, -3.0],
        "aabbox_max": [1.0, 2.0, 3.0],
        "child_partition_ids": list(children),
        "child_partition_table_present": bool(children[0]),
        "child_object_indices": list(objects),
    }


def _base(chunks):
    return {
        "format": "SHIFT.SGBRuntime/1",
        "ready": True,
        "chunks": chunks,
    }


def test_wrapper_catalog_matches_pre_part_loader_list_order():
    report = _base([
        {
            "tag": "OCCL",
            "records": [
                _occl_record(0),
                _occl_record(1, batched=True),
            ],
        },
        {
            "tag": "NODE",
            "records": [
                _node_record(0, "LOD"),
                _node_record(1, "OBJECT"),
            ],
        },
        {
            "tag": "SUMM",
            "records": [_node_record(0, "OBJECT")],
        },
        {
            "tag": "PART",
            "records": [_part(0, 10, objects=(1, 2, 3))],
        },
    ])

    catalog = build_scene_wrapper_catalog(
        report,
        before_chunk_index=3,
    )

    assert [row["source_id_one_based"] for row in catalog] == [1, 2, 3]
    assert [row["chunk_tag"] for row in catalog] == [
        "OCCL",
        "NODE",
        "NODE",
    ]
    assert [row["payload_kind"] for row in catalog] == [
        "OCCL",
        "LOD",
        "OBJECT",
    ]


def test_prebuilt_flat_skips_part_conversion():
    report = _base([
        {
            "tag": "NODE",
            "records": [_node_record(0)],
        },
        {
            "tag": "FLAT",
            "offset": 0x200,
            "size": 0x1000,
            "flat_runtime": {
                "ready": True,
                "stats": {
                    "tree_nodes": 5,
                    "leaf_records": 12,
                    "max_depth": 3,
                },
            },
        },
    ])

    bridge = build_sgb_part_flat_bridge(report)

    assert bridge["format"] == FORMAT
    assert bridge["ready"] is True
    assert bridge["mode"] == "prebuilt-flat"
    assert bridge["conversion_required"] is False
    assert bridge["prebuilt_flat"]["tree_nodes"] == 5
    assert bridge["prebuilt_flat"]["direct_records"] == 12
    assert bridge["generated_flat"] is None


def test_part_fallback_builds_exact_flat_and_runtime_table_geometry():
    report = _base([
        {
            "tag": "OCCL",
            "records": [_occl_record(0)],
        },
        {
            "tag": "NODE",
            "records": [
                _node_record(0, "LOD"),
                _node_record(1, "OBJECT"),
            ],
        },
        {
            "tag": "PART",
            "records": [
                _part(
                    0,
                    10,
                    children=(20, 0, 0, 0),
                    objects=(1, 2),
                ),
                _part(1, 20, objects=(3,)),
            ],
        },
    ])

    bridge = build_sgb_part_flat_bridge(report)

    assert bridge["ready"] is True
    assert bridge["mode"] == "part-to-flat"
    assert bridge["conversion_required"] is True
    assert bridge["wrapper_catalog_count"] == 3

    generated = bridge["generated_flat"]
    assert generated["summary"] == {
        "part_record_count": 2,
        "reachable_partition_count": 2,
        "direct_record_count": 3,
        "generated_flat_bytes": 0x100,
        "counting_rule": (
            "0x20 per PART node + 0x40 per direct scene wrapper"
        ),
        "primary_table_bytes": 3 * 0x28,
        "secondary_table_bytes": 3 * 0x40,
        "runtime_index_min": 0,
        "runtime_index_max": 2,
    }

    root = generated["root"]
    assert root["flat_node_offset"] == 0
    assert [row["flat_runtime_index"] for row in root["direct_records"]] == [0, 1]
    assert [row["flat_record_offset"] for row in root["direct_records"]] == [
        0x20,
        0x60,
    ]

    child = root["children"][0]["node"]
    assert child["flat_node_offset"] == 0xA0
    assert child["direct_records"][0]["flat_runtime_index"] == 2
    assert child["direct_records"][0]["flat_record_offset"] == 0xC0
    assert child["subtree_bytes"] == 0x60
    assert root["subtree_bytes"] == 0x100

    direct = generated["direct_records"][2]
    assert direct["primary_table"]["entry_offset"] == 2 * 0x28
    assert direct["primary_table"]["record_pointer_field_offset"] == 0x20
    assert direct["secondary_table"]["entry_offset"] == 2 * 0x40
    assert direct["secondary_table"]["node_pointer_field_offset"] == 0x30
    assert direct["secondary_table"]["record_pointer_field_offset"] == 0x34
    assert direct["secondary_table"]["primary_pointer_field_offset"] == 0x38
    assert direct["direct_object_pointer"]["destination_offset"] == 0x38
    assert direct["runtime_index_field"] == {
        "destination_offset": 0x3C,
        "value": 2,
        "producer": "FUN_00689db0",
    }


def test_part_wrapper_id_zero_fails_closed():
    report = _base([
        {
            "tag": "NODE",
            "records": [_node_record(0)],
        },
        {
            "tag": "PART",
            "records": [_part(0, 10, objects=(0,))],
        },
    ])

    bridge = build_sgb_part_flat_bridge(report)

    assert bridge["ready"] is False
    assert bridge["status"] == "generated-flat-blocked"
    assert (
        "part-flat:partition-10:wrapper-id-out-of-range:0"
        in bridge["blocking_reasons"]
    )


def test_unresolved_partition_child_fails_closed():
    report = _base([
        {
            "tag": "NODE",
            "records": [_node_record(0)],
        },
        {
            "tag": "PART",
            "records": [
                _part(
                    0,
                    10,
                    children=(99, 0, 0, 0),
                    objects=(1,),
                )
            ],
        },
    ])

    bridge = build_sgb_part_flat_bridge(report)

    assert bridge["ready"] is False
    assert (
        "part-flat:partition-10:child-partition-unresolved:99"
        in bridge["blocking_reasons"]
    )


def test_duplicate_partition_ids_fail_closed():
    report = _base([
        {
            "tag": "NODE",
            "records": [_node_record(0)],
        },
        {
            "tag": "PART",
            "records": [
                _part(0, 10, objects=(1,)),
                _part(1, 10),
            ],
        },
    ])

    bridge = build_sgb_part_flat_bridge(report)

    assert bridge["ready"] is False
    assert "part-flat:partition-id-duplicate:10" in bridge["blocking_reasons"]


def test_missing_flat_and_part_is_explicitly_blocked():
    bridge = build_sgb_part_flat_bridge(
        _base([{"tag": "NODE", "records": [_node_record(0)]}])
    )
    assert bridge["ready"] is False
    assert bridge["mode"] == "none"
    assert bridge["blocking_reasons"] == [
        "part-flat:neither-prebuilt-flat-nor-part"
    ]
