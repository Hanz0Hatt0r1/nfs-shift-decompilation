from animation_track_runtime import base_transform_defaults
from scene_node_runtime import (
    build_scene_manifest,
    classify_object_type,
    parse_integer_reference_list,
    parse_light,
    parse_node,
    parse_scene_partition,
    parse_transform,
)


def test_scene_object_dispatch_matches_recovered_tags():
    assert classify_object_type("NODE")["kind"] == "node"
    assert classify_object_type("TRANSFORM")["kind"] == "transform"
    assert classify_object_type("LIGHT")["kind"] == "light"
    assert classify_object_type("UNKNOWN")["recognized"] is False


def test_node_preserves_runtime_flags_and_defaults():
    result = parse_node(
        name="body",
        attributes={
            "Merged": "TRUE",
            "Animated": "FALSE",
            "Dynamic": "TRUE",
            "VariationIndex": 4,
            "Instances": 2,
            "Resource": "tracks/body.meb",
            "VariationPaletteFile": "palette.xml",
        },
        transform=parse_transform(),
    )
    assert result["flags"] == {"merged": True, "animated": False, "dynamic": True}
    assert result["instances"] == 2
    assert result["resource"] == "tracks/body.meb"
    assert result["transform"]["position"] == [0.0, 0.0, 0.0]


def test_transform_defaults_are_distinct_from_animation_node_defaults():
    scene_transform = parse_transform()
    anim_transform = base_transform_defaults()
    assert scene_transform["position"] == [0.0, 0.0, 0.0]
    assert anim_transform["translation"] == [0.0, 0.0, 0.0]
    assert scene_transform["orientation"] == [1.0, 0.0, 0.0, 0.0]


def test_integer_reference_list_accepts_hex_and_delimiters():
    values = parse_integer_reference_list("NONE, 0x10; 3 7")
    assert 16 in values
    assert 3 in values
    assert 7 in values


def test_scene_partition_preserves_source_lists():
    result = parse_scene_partition(
        partition_id=7,
        aabbox_min=[-1, -2, -3],
        aabbox_max=[1, 2, 3],
        child_partitions="1, 0x2",
        child_objects="10 11",
    )
    assert result["partition_id"] == 7
    assert result["child_partitions"] == [1, 2]
    assert result["child_objects"] == [10, 11]


def test_light_type_and_angle_conversion():
    result = parse_light(light_type="Spotlight", inner_angle=20, outer_angle=40)
    assert result["type_code"] == 3
    assert abs(result["inner_angle_radians"] - 0.1745329252) < 1e-6
    assert abs(result["outer_angle_radians"] - 0.3490658504) < 1e-6


def test_manifest_keeps_unknown_types_explicit():
    result = build_scene_manifest(
        [{"tag": "NODE", "name": "A"}, {"tag": "FOO", "name": "B"}],
        file_version="3",
        merged=True,
    )
    assert result["object_counts"]["node"] == 1
    assert result["unknown_object_types"] == ["FOO"]
