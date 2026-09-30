from sgb_scene_placement import (
    FORMAT,
    build_sgb_scene_placement,
)


def _object(index=0, name="SUMM_A", kind="LOD"):
    return {
        "index": index,
        "offset": 0x100 + index * 0x40,
        "name": name,
        "resource": f"tracks/test/{name.lower()}.meb",
        "object_kind": kind,
        "object_decoded": True,
    }


def _flat_mode():
    return {
        "present": True,
        "ready": True,
        "status": "ready",
        "blocking_reasons": [],
        "links": [{
            "runtime_index": 0,
            "flat": {
                "tree_path": [0],
                "node_aabbox": {
                    "min_xyz": [-10.0, -20.0, -30.0],
                    "max_xyz": [40.0, 50.0, 60.0],
                },
                "filter_masks": {
                    "include_words": [1, 2],
                    "exclude_words": [4, 8],
                },
                "bounding_sphere": {
                    "center_xyz": [1.0, 2.0, 3.0],
                    "radius": 25.0,
                },
                "spatial_bounds_candidate": {
                    "min_xyz": [-1.0, -2.0, -3.0],
                    "max_xyz": [3.0, 6.0, 9.0],
                    "source_consumer_proven": False,
                },
            },
            "summ": _object(),
        }],
    }


def _part_mode():
    return {
        "present": True,
        "ready": True,
        "status": "ready",
        "blocking_reasons": [],
        "links": [{
            "part_record_index": 0,
            "partition_id": 7,
            "child_slot": 0,
            "source_child_object_id": 2,
            "node_registry_index": 1,
            "node": _object(1, "NODE_B", "OBJECT"),
            "spatial": {
                "partition_aabbox": {
                    "min_xyz": [-100.0, -50.0, -25.0],
                    "max_xyz": [100.0, 50.0, 25.0],
                },
            },
        }],
    }


def _join(*, flat=True, part=False, ready=True):
    return {
        "format": "SHIFT.SGBPlacementJoin/1",
        "ready": ready,
        "blocking_reasons": [] if ready else ["upstream:blocker"],
        "flat_summ": _flat_mode() if flat else {
            "present": False,
            "ready": False,
            "links": [],
        },
        "part_node": _part_mode() if part else {
            "present": False,
            "ready": False,
            "links": [],
        },
    }


def test_flat_summ_scene_placement_preserves_only_proven_geometry():
    report = build_sgb_scene_placement(_join())

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["placement_count"] == 1
    assert report["mode_counts"] == {"flat-summ": 1}

    row = report["placements"][0]
    assert row["identity"]["runtime_index"] == 0
    assert row["object"]["name"] == "SUMM_A"
    assert row["spatial"]["node_aabbox"]["ordered_axes"] is True
    assert row["spatial"]["filter_masks"]["include_words"] == [1, 2]
    assert row["spatial"]["bounding_sphere"]["radius"] == 25.0
    assert row["spatial"]["proven_geometry"] == [
        "node_aabbox",
        "filter_masks",
        "bounding_sphere",
    ]

    candidate = row["spatial"]["bounds_candidate"]
    assert candidate["source_consumer_proven"] is False
    assert candidate["admission"] == "advisory-only"
    assert candidate["used_as_proven_aabb"] is False

    handoff = row["render_binding_handoff"]
    assert handoff["world_transform_status"] == "not-emitted"
    assert handoff["spatial_culling_ready"] is True
    assert handoff["draw_admission"] is False


def test_part_node_scene_placement_uses_partition_aabb_only():
    report = build_sgb_scene_placement(
        _join(flat=False, part=True)
    )

    assert report["ready"] is True
    row = report["placements"][0]
    assert row["mode"] == "part-node"
    assert row["identity"]["source_child_object_id"] == 2
    assert row["identity"]["node_registry_index"] == 1
    assert row["spatial"]["scope"] == "partition"
    assert row["spatial"]["partition_aabbox"]["ordered_axes"] is True
    assert row["spatial"]["filter_masks"] is None
    assert row["spatial"]["bounding_sphere"] is None
    assert row["spatial"]["proven_geometry"] == ["partition_aabbox"]


def test_both_spatial_modes_are_normalized_without_merging_identities():
    report = build_sgb_scene_placement(_join(flat=True, part=True))

    assert report["ready"] is True
    assert report["placement_count"] == 2
    assert report["mode_counts"] == {
        "flat-summ": 1,
        "part-node": 1,
    }
    assert [row["placement_index"] for row in report["placements"]] == [0, 1]


def test_missing_flat_query_geometry_blocks_neutral_placement():
    value = _join()
    del value["flat_summ"]["links"][0]["flat"]["filter_masks"]

    report = build_sgb_scene_placement(value)

    assert report["ready"] is False
    assert (
        "scene-placement:flat-summ:0:filter-masks-missing"
        in report["blocking_reasons"]
    )
    assert report["placements"][0]["ready"] is False


def test_upstream_placement_join_blocker_is_preserved():
    report = build_sgb_scene_placement(_join(ready=False))

    assert report["ready"] is False
    assert "upstream:blocker" in report["blocking_reasons"]
    assert (
        "scene-placement:placement-join-not-ready"
        in report["blocking_reasons"]
    )


def test_render_binding_boundary_remains_fail_closed_on_world_transform():
    report = build_sgb_scene_placement(_join())
    boundary = report["render_binding_boundary"]

    assert boundary["object_identity_ready"] is True
    assert boundary["spatial_query_geometry_ready"] is True
    assert boundary["world_transform_emitted"] is False
    assert boundary["draw_admission"] is False
    assert boundary["corpus_bounds_candidate_is_advisory"] is True


def test_wrong_input_format_is_rejected():
    try:
        build_sgb_scene_placement({"format": "wrong"})
    except ValueError as error:
        assert "SGBPlacementJoin" in str(error)
    else:
        raise AssertionError("wrong input format must be rejected")
