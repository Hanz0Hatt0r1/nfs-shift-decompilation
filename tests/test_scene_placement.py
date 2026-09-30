from copy import deepcopy

import pytest

from scene_placement import (
    FORMAT,
    attach_scene_placement,
    build_scene_placement,
)


def _flat_link(index=0):
    return {
        "runtime_index": index,
        "flat": {
            "tree_path": [0],
            "leaf_offset": 0x60,
            "node_aabbox": {
                "min_xyz": [-10.0, -20.0, -30.0],
                "max_xyz": [40.0, 50.0, 60.0],
            },
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
        },
        "summ": {
            "index": index,
            "name": "SUMM_A",
            "resource": "tracks/test/a.meb",
            "object_kind": "OBJECT",
            "object_decoded": True,
        },
    }


def _part_link():
    return {
        "part_record_index": 2,
        "partition_id": 10,
        "child_slot": 1,
        "source_child_object_id": 3,
        "node_registry_index": 2,
        "node": {
            "index": 2,
            "name": "NODE_C",
            "resource": "tracks/test/c.meb",
            "object_kind": "LOD",
            "object_decoded": True,
        },
        "partition_aabbox": {
            "min_xyz": [-100.0, -50.0, -20.0],
            "max_xyz": [100.0, 50.0, 20.0],
            "source": "PART record +0x04..+0x18",
        },
    }


def _join():
    return {
        "format": "SHIFT.SGBPlacementJoin/1",
        "ready": True,
        "blocking_reasons": [],
        "flat_summ": {
            "present": True,
            "ready": True,
            "links": [_flat_link()],
        },
        "part_node": {
            "present": True,
            "ready": True,
            "links": [_part_link()],
        },
    }


def test_scene_placement_emits_leaf_and_partition_precision():
    result = build_scene_placement(_join())

    assert result["format"] == FORMAT
    assert result["ready"] is True
    assert result["placement_count"] == 2
    assert result["modes"] == ["flat-summ", "part-node"]
    assert result["stats"] == {
        "flat_summ": 1,
        "part_node": 1,
        "leaf_precision": 1,
        "partition_precision": 1,
    }

    flat = result["placements"][0]
    assert flat["placement_id"] == "flat-summ:0"
    assert flat["precision"] == "leaf"
    assert flat["resource"] == "tracks/test/a.meb"
    assert flat["spatial"]["bounding_sphere"]["radius"] == 4.0
    assert flat["spatial"]["bounds"]["source_consumer_proven"] is True

    part = result["placements"][1]
    assert part["placement_id"] == "part-node:2:1"
    assert part["precision"] == "partition"
    assert part["resource"] == "tracks/test/c.meb"
    assert part["spatial"]["partition_aabbox"]["min_xyz"] == [
        -100.0, -50.0, -20.0
    ]
    assert part["spatial"]["bounding_sphere"] is None


def test_scene_placement_fails_closed_on_missing_flat_spatial_payload():
    join = _join()
    join["flat_summ"]["links"][0]["flat"]["spatial_bounds"] = None

    result = build_scene_placement(join)

    assert result["ready"] is False
    assert (
        "scene-placement:flat-summ-0:leaf-bounds-invalid"
        in result["blocking_reasons"]
    )


def test_scene_placement_fails_closed_on_invalid_partition_aabb():
    join = _join()
    join["part_node"]["links"][0]["partition_aabbox"]["min_xyz"][0] = 200.0

    result = build_scene_placement(join)

    assert result["ready"] is False
    assert (
        "scene-placement:part-node-2-1:partition-aabb-invalid"
        in result["blocking_reasons"]
    )


def test_attach_scene_placement_preserves_render_commands_verbatim():
    placement = build_scene_placement(_join())
    binding = {
        "format": "SHIFT.RenderBinding/1",
        "packets": [{"name": "P"}],
        "static_draws": [{"format": "SHIFT.StaticDraw/1"}],
        "render_commands": [{
            "format": "SHIFT.RenderCommand/1",
            "ready": True,
            "submeshes": [{"first_index": 0, "index_count": 3}],
        }],
        "stats": {"render_commands": 1},
    }
    original = deepcopy(binding)

    result = attach_scene_placement(binding, placement)

    assert binding == original
    assert result["packets"] == original["packets"]
    assert result["static_draws"] == original["static_draws"]
    assert result["render_commands"] == original["render_commands"]
    assert result["scene_placement"]["format"] == FORMAT
    assert result["stats"]["scene_placements"] == 2
    assert result["stats"]["scene_placement_modes"] == [
        "flat-summ", "part-node"
    ]


def test_attach_scene_placement_rejects_blocked_placement():
    placement = build_scene_placement(_join())
    placement["ready"] = False

    with pytest.raises(ValueError, match="not ready"):
        attach_scene_placement(
            {"format": "SHIFT.RenderBinding/1"},
            placement,
        )


def test_scene_placement_rejects_wrong_input_formats():
    with pytest.raises(ValueError, match="SGBPlacementJoin"):
        build_scene_placement({"format": "wrong"})

    with pytest.raises(ValueError, match="RenderBinding"):
        attach_scene_placement(
            {"format": "wrong"},
            {"format": FORMAT, "ready": True},
        )
