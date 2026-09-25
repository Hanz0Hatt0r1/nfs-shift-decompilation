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
    assert scene["screenshots"]["artifacts_are_external"] is True
