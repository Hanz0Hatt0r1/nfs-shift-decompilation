from sgb_placement_join import FORMAT, build_sgb_placement_join


def _wrapper(index, name, kind):
    return {
        "index": index,
        "offset": 0x100 + index * 0x40,
        "name": {"text": name},
        "resource": {"text": f"tracks/test/{name.lower()}.meb"},
        "object_payload": {
            "report": {
                "decoded": True,
                "kind": {"text": kind},
            }
        },
    }


def _flat_leaf(runtime_index, *, pointer=0, offset=0x20):
    return {
        "offset": offset,
        "runtime_index": runtime_index,
        "direct_object_pointer_word": pointer,
        "filter_masks": {
            "include_mask_u64": 0,
            "exclude_mask_u64": 0,
        },
        "bounding_sphere": {
            "center_xyz": [1.0, 2.0, 3.0],
            "radius": 4.0,
        },
        "spatial_bounds": {
            "min_xyz": [-3.0, -2.0, -1.0],
            "max_xyz": [5.0, 6.0, 7.0],
            "source_consumer_proven": True,
        },
    }


def _flat_tree(leaves):
    return {
        "offset": 0,
        "depth": 0,
        "aabbox": {
            "min_xyz": [-10.0, -20.0, -30.0],
            "max_xyz": [40.0, 50.0, 60.0],
        },
        "records": leaves,
        "children": [],
    }


def _report(*, with_flat=True, with_summ=True, with_part=False):
    chunks = [
        {
            "tag": "NODE",
            "records": [
                _wrapper(0, "NODE_A", "LOD"),
                _wrapper(1, "NODE_B", "OBJECT"),
            ],
        }
    ]
    if with_flat:
        chunks.append({
            "tag": "FLAT",
            "flat_runtime": {
                "ready": True,
                "root": _flat_tree([
                    _flat_leaf(1, offset=0x20),
                    _flat_leaf(0, offset=0x60),
                ]),
            },
        })
    if with_summ:
        chunks.append({
            "tag": "SUMM",
            "records": [
                _wrapper(0, "SUMM_A", "OBJECT"),
                _wrapper(1, "SUMM_B", "LOD"),
            ],
        })
    if with_part:
        chunks.append({
            "tag": "PART",
            "records": [{
                "index": 0,
                "partition_id": 10,
                "aabbox_min": [-10.0, -20.0, -30.0],
                "aabbox_max": [40.0, 50.0, 60.0],
                "child_object_indices": [2, 1],
            }],
        })
    return {
        "format": "SHIFT.SGBRuntime/1",
        "ready": True,
        "chunks": chunks,
    }


def test_flat_summ_runtime_index_joins_wrapper_order():
    result = build_sgb_placement_join(_report())

    assert result["format"] == FORMAT
    assert result["ready"] is True
    assert result["modes_present"] == ["flat-summ"]
    join = result["flat_summ"]
    assert join["flat_leaf_count"] == 2
    assert join["summ_wrapper_count"] == 2
    assert join["runtime_index_contiguous"] is True
    assert [row["runtime_index"] for row in join["links"]] == [0, 1]
    assert [row["summ"]["name"] for row in join["links"]] == [
        "SUMM_A",
        "SUMM_B",
    ]
    assert join["links"][0]["flat"]["leaf_offset"] == 0x60
    assert join["links"][1]["flat"]["leaf_offset"] == 0x20
    assert join["links"][0]["flat"]["node_aabbox"]["min_xyz"] == [
        -10.0, -20.0, -30.0
    ]
    assert join["links"][0]["flat"]["bounding_sphere"]["radius"] == 4.0
    assert join["links"][0]["flat"]["spatial_bounds"]["source_consumer_proven"] is True


def test_flat_summ_duplicate_runtime_index_blocks():
    report = _report()
    flat = next(row for row in report["chunks"] if row["tag"] == "FLAT")
    flat["flat_runtime"]["root"]["records"][1]["runtime_index"] = 1

    result = build_sgb_placement_join(report)

    assert result["ready"] is False
    assert any(
        reason.startswith("flat-summ:duplicate-runtime-indices:")
        for reason in result["blocking_reasons"]
    )
    assert any(
        reason.startswith("flat-summ:missing-runtime-indices:")
        for reason in result["blocking_reasons"]
    )


def test_flat_summ_count_mismatch_blocks():
    report = _report()
    summ = next(row for row in report["chunks"] if row["tag"] == "SUMM")
    summ["records"].append(_wrapper(2, "SUMM_C", "OBJECT"))

    result = build_sgb_placement_join(report)

    assert result["ready"] is False
    assert "flat-summ:count-mismatch:flat=2:summ=3" in result["blocking_reasons"]


def test_part_child_ids_join_one_based_node_registry():
    result = build_sgb_placement_join(
        _report(with_flat=False, with_summ=False, with_part=True)
    )

    assert result["ready"] is True
    assert result["modes_present"] == ["part-node"]
    join = result["part_node"]
    assert join["node_registry_count"] == 2
    assert join["linked_child_object_count"] == 2
    assert [row["node_registry_index"] for row in join["links"]] == [1, 0]
    assert [row["node"]["name"] for row in join["links"]] == [
        "NODE_B",
        "NODE_A",
    ]
    assert join["links"][0]["partition_aabbox"] == {
        "min_xyz": [-10.0, -20.0, -30.0],
        "max_xyz": [40.0, 50.0, 60.0],
        "source": "PART record +0x04..+0x18",
    }


def test_part_child_id_zero_is_not_silently_wrapped_to_uint32():
    report = _report(with_flat=False, with_summ=False, with_part=True)
    part = next(row for row in report["chunks"] if row["tag"] == "PART")
    part["records"][0]["child_object_indices"] = [0]

    result = build_sgb_placement_join(report)

    assert result["ready"] is False
    assert (
        "part-node:part-0:child-0:id-not-one-based"
        in result["blocking_reasons"]
    )


def test_both_placement_modes_must_validate_when_both_are_present():
    result = build_sgb_placement_join(_report(with_part=True))
    assert result["ready"] is True
    assert result["modes_present"] == ["flat-summ", "part-node"]
    assert result["modes_ready"] == ["flat-summ", "part-node"]


def test_part_runtime_flat_materialization_keeps_serialized_boundary_explicit():
    result = build_sgb_placement_join(
        _report(with_flat=False, with_summ=False, with_part=True)
    )
    bridge = result["part_runtime_flat_materialization"]

    assert bridge["source"] == "FUN_0068a810 -> FUN_006afd50 -> FUN_00689db0"
    assert bridge["serialized_claim"] is False
    assert bridge["generated_leaf_bytes"] == 0x40
    assert bridge["generated_leaf_direct_object_pointer_offset"] == 0x38
    assert bridge["generated_leaf_runtime_index_offset"] == 0x3C
    assert bridge["runtime_index_source"] == "sequential traversal ordinal"


def test_no_spatial_mode_blocks():
    report = {
        "format": "SHIFT.SGBRuntime/1",
        "ready": True,
        "chunks": [{"tag": "NODE", "records": [_wrapper(0, "A", "OBJECT")]}],
    }
    result = build_sgb_placement_join(report)

    assert result["ready"] is False
    assert result["blocking_reasons"] == ["placement:no-supported-spatial-mode"]


def test_wrong_input_format_is_rejected():
    try:
        build_sgb_placement_join({"format": "wrong"})
    except ValueError as error:
        assert "SGBRuntime" in str(error)
    else:
        raise AssertionError("wrong input format must be rejected")
