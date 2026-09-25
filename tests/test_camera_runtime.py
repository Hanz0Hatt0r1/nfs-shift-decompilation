import pytest

from camera_runtime import (
    CAMERA_CONFIG_PATH,
    LOCAL_CAMERAS_PATH,
    TRACKS_CAMERA_CONFIG_PATH,
    TRACK_CAMERA_CONFIG_TEMPLATE,
    TRACK_CAMERA_TEMPLATE,
    build_camera_load_plan,
    parse_camera_xml,
    property_catalog,
)


def test_global_camera_load_plan_uses_global_track_config_without_track_name():
    plan = build_camera_load_plan()
    assert plan.global_paths == (CAMERA_CONFIG_PATH, TRACKS_CAMERA_CONFIG_PATH)
    assert plan.local_paths == (LOCAL_CAMERAS_PATH,)
    assert plan.track_camera_paths == (TRACK_CAMERA_TEMPLATE % "",)


def test_global_camera_load_plan_uses_track_specific_camera_config():
    plan = build_camera_load_plan(track_name="Donington")
    assert plan.global_paths == (
        CAMERA_CONFIG_PATH,
        TRACK_CAMERA_CONFIG_TEMPLATE % "Donington",
    )


def test_named_camera_file_keeps_direct_path_then_runtime_fallback():
    plan = build_camera_load_plan(camera_name="TrackCam01")
    assert plan.track_camera_paths == (
        "TrackCam01",
        TRACK_CAMERA_TEMPLATE % "TrackCam01",
    )


def test_camera_xml_preserves_class_id_and_data_boundary():
    xml = b"""
    <root>
      <elements>
        <camera class="CStaticCamera" id="Main">
          <data FOV="60" FarZ="5000">
            <Pos>1;2;3</Pos>
            <QuatOri>0;0;0;1</QuatOri>
            <Unknown value="kept" />
          </data>
        </camera>
      </elements>
    </root>
    """
    report = parse_camera_xml(xml, source_name="sample.xml")
    assert report["object_count"] == 1
    row = report["objects"][0]
    assert row["class"] == "CStaticCamera"
    assert row["id"] == "Main"
    assert row["data_attributes"] == {"FOV": "60", "FarZ": "5000"}
    assert row["data_children"]["Pos"] == "1;2;3"
    assert row["data_children"]["Unknown"]["attributes"] == {"value": "kept"}


def test_namespace_qualified_elements_are_supported():
    xml = """
    <ns:root xmlns:ns="urn:test">
      <ns:elements>
        <ns:camera class="CTrackingCamera" id="SplineA">
          <ns:data><ns:SplineID>42</ns:SplineID></ns:data>
        </ns:camera>
      </ns:elements>
    </ns:root>
    """
    report = parse_camera_xml(xml)
    assert report["objects"][0]["class"] == "CTrackingCamera"
    assert report["objects"][0]["data_children"]["SplineID"] == "42"


def test_property_catalog_preserves_overlapping_runtime_offsets():
    catalog = property_catalog()
    rows = {row["name"]: row for row in catalog["static_camera"]}
    assert rows["ShakeScreenVelocityMin"]["offset"] == rows["ShakeFrequencyMin"]["offset"]
    assert rows["ShakeScreenVelocity"]["offset"] == rows["ShakeFrequency"]["offset"]


def test_invalid_camera_xml_is_rejected():
    with pytest.raises(ValueError):
        parse_camera_xml("<root>")


def test_proven_tracking_camera_inheritance_chain_is_exposed():
    from camera_runtime import resolve_camera_class_chain

    report = resolve_camera_class_chain("CTrackingCamera")
    assert report["chain"] == ["CTrackingCamera", "CStaticCamera", "CBaseCamera", "CCameraObj"]
    assert report["resolved_links"] == 3
    assert report["fully_resolved"] is True


def test_area_subclasses_keep_their_known_base_prefix():
    from camera_runtime import resolve_camera_class_chain

    assert resolve_camera_class_chain("CSphereArea")["chain"] == ["CSphereArea", "CCamArea"]
    assert resolve_camera_class_chain("COBBArea")["chain"] == ["COBBArea", "CCamArea"]


def test_unknown_camera_base_is_not_guessed():
    from camera_runtime import resolve_camera_class_chain

    report = resolve_camera_class_chain("CCamSpline")
    assert report["chain"] == ["CCamSpline"]
    assert report["fully_resolved"] is True
    assert "CCamSpline" not in report["camera_class_bases"] if "camera_class_bases" in report else True