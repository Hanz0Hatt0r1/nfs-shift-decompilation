from track_camera_collections_xml_runtime import (
    TrackCameraCollectionEntry,
    describe_collection_xml_setup,
    describe_track_camera_man_xml_registrations,
    serialize_area_collection,
    serialize_spline_collection,
)


def test_common_xml_setup_uses_exact_0x50_buffer():
    result = describe_collection_xml_setup(xml_collection="elements")
    assert result["actions"][1]["bytes"] == 0x50


def test_spline_collection_filters_by_plus_24_against_global_type():
    result = serialize_spline_collection(
        entries=[
            TrackCameraCollectionEntry("a", filter_value_24=1),
            TrackCameraCollectionEntry("b", filter_value_24=2),
            TrackCameraCollectionEntry("c", filter_value_24=1),
        ],
        global_type=1,
    )
    assert [x["index"] for x in result["serialized"]] == [0, 2]
    assert result["filter_offset"] == "+0x24"


def test_spline_collection_uses_vtable_plus_four_serializer():
    result = serialize_spline_collection(
        entries=[TrackCameraCollectionEntry("a", filter_value_24=1)],
        global_type=1,
    )
    assert result["serialized"][0]["actions"][0]["action"] == "entry.vtable +0x04"


def test_area_collection_serializes_every_entry_without_filter():
    result = serialize_area_collection(
        entries=[
            TrackCameraCollectionEntry("a", filter_value_24=1),
            TrackCameraCollectionEntry("b", filter_value_24=2),
        ]
    )
    assert result["serialized_count"] == 2
    assert len(result["serialized"]) == 2


def test_area_collection_comes_from_plus_7c():
    result = serialize_area_collection(
        entries=[TrackCameraCollectionEntry("a")],
    )
    assert result["source_list"] == "+0x7c"
    assert result["filter"] is None


def test_track_camera_man_registration_matches_three_children():
    result = describe_track_camera_man_xml_registrations()
    children = {x["name"]: x for x in result["children"]}
    assert children["Trackside Cams"]["save_callback"] == "FUN_00812260"
    assert children["Splines"]["load_callback"] == "FUN_008117c0"
    assert children["Areas"]["storage_offset"] == 0x7C
