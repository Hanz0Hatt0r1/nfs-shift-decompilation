from camera_area_xml_runtime import (
    deserialize_camera_areas,
    instantiate_camera_area_from_class,
    release_camera_area_lists,
    reset_camera_area_mode,
)


def test_reset_camera_area_mode_sets_inactive_mode_and_output_invalid():
    result = reset_camera_area_mode(collection_present=True)
    assert any(a.get("value") == 0x7FFFFFFF for a in result["actions"])
    assert any(
        a["action"] == "write output-valid" and a["value"] == 0
        for a in result["actions"]
    )


def test_sphere_and_box_area_factories_keep_exact_sizes():
    sphere = instantiate_camera_area_from_class(
        class_symbol="DAT_00c25f88",
        allocation_succeeded=True,
        constructor_succeeded=True,
    )
    box = instantiate_camera_area_from_class(
        class_symbol="DAT_00c25f98",
        allocation_succeeded=True,
        constructor_succeeded=True,
    )
    assert sphere["allocation_bytes"] == 0x20
    assert sphere["constructor"] == "FUN_0081e750"
    assert box["allocation_bytes"] == 0x60
    assert box["constructor"] == "FUN_0081ea20"


def test_unknown_camera_area_class_is_unsupported():
    result = instantiate_camera_area_from_class(
        class_symbol="unknown",
        allocation_succeeded=True,
        constructor_succeeded=True,
    )
    assert result["status"] == "unsupported-class"


def test_area_xml_load_marks_inherited_area_objects():
    result = deserialize_camera_areas(
        elements=[{"class": "Sphere", "secondary": "A"}],
        factory_success=[True],
        property_application_success=[True],
        resolved_classes=["DAT_00c25f88"],
        inheritance_lists=[["DAT_00c25f78"]],
    )
    assert result["status"] == "loaded"
    assert result["entries"][0]["is_area_derived"] is True


def test_area_xml_load_stops_at_property_application_failure():
    result = deserialize_camera_areas(
        elements=[{"class": "Sphere", "secondary": "A"}],
        factory_success=[True],
        property_application_success=[False],
        resolved_classes=["DAT_00c25f88"],
        inheritance_lists=[[]],
    )
    assert result["status"] == "property-application-failed"


def test_release_camera_area_lists_has_three_independent_walks():
    result = release_camera_area_lists(
        list_counts={"+0x14": 1, "+0x48": 2, "+0x7c": 3}
    )
    assert [a["count"] for a in result["actions"]] == [1, 2, 3]
