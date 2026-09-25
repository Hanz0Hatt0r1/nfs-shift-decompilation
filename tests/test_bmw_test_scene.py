import json
from pathlib import Path


SCENE = Path(__file__).parents[1] / "tests" / "scenes" / "bmw_m3_e36_kit00_test_scene.json"


def test_bmw_m3_test_scene_is_pinned_to_retail_asset_identity():
    scene = json.loads(SCENE.read_text(encoding="utf-8"))
    assert scene["format"] == "SHIFT.BMWM3TestScene/1"
    assert scene["ready"] is True
    assert scene["source"]["archive_sha256"] == "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70"
    assert scene["source"]["vhf_resource"] == "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
    assert scene["source"]["kit"] == "00"
    assert scene["source"]["lod"] == "A"
    assert scene["vehicle"]["part_count"] == 27
    assert scene["vehicle"]["golden_body_meb"]["sha256"] == "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"


def test_bmw_m3_test_scene_has_stable_turntable_cameras():
    scene = json.loads(SCENE.read_text(encoding="utf-8"))
    cameras = scene["cameras"]
    assert [row["name"] for row in cameras] == [
        "front_left",
        "rear_right",
        "side",
        "front",
    ]
    assert [(row["yaw_deg"], row["pitch_deg"]) for row in cameras] == [
        (-28.0, -15.0),
        (152.0, -12.0),
        (-90.0, -10.0),
        (0.0, -8.0),
    ]


def test_bmw_m3_test_scene_explicitly_separates_geometry_preview_from_runtime_proof():
    scene = json.loads(SCENE.read_text(encoding="utf-8"))
    assert scene["renderer"]["mode"] == "geometry-preview"
    assert scene["renderer"]["material_execution"] is False
    assert scene["renderer"]["runtime_capture_required"] is False
    assert scene["screenshot_policy"]["artifacts_external"] is True


def test_bmw_m3_test_scene_pins_external_screenshot_hashes():
    scene = json.loads(SCENE.read_text(encoding="utf-8"))
    assert [(row["name"], row["sha256"]) for row in scene["screenshots"]] == [
        ("01_front_left", "43a8cbc47315a4236f6eb1a87b89569d2760ce183475131021228701e787886a"),
        ("02_rear_right", "1db293487454261752c8ee3be3aa7112883ddf487a1aa21add6d52faa917fc96"),
        ("03_side", "0e80ab9ec108e35d3ff0833de9da5bc6a7887f1d8990dda390a5da2edc1befcd"),
        ("04_front", "a1f086f5001c0a009b645457b92497b2166b6f5ba0db3f085cd5788204bc73fa"),
    ]
    assert all(row["width"] == 1600 and row["height"] == 900 for row in scene["screenshots"])
    assert all(row["geometry_unchanged"] is True for row in [scene["screenshot_policy"]])
    assert scene["screenshot_policy"]["material_execution"] is False
