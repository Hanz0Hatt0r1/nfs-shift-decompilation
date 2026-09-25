import json
from pathlib import Path


SCENE = Path(__file__).parents[1] / "tests" / "scenes" / "bmw_m3_e36_kit00_test_scene_v2.json"


def test_bmw_m3_test_scene_v2_pins_real_retail_source():
    scene = json.loads(SCENE.read_text(encoding="utf-8"))
    assert scene["format"] == "SHIFT.BMWM3TestScene/2"
    assert scene["ready"] is True
    assert scene["source"]["archive_sha256"] == "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70"
    assert scene["vehicle"]["golden_body_meb"]["sha256"] == "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"
    assert scene["vehicle"]["part_count"] == 27


def test_bmw_m3_test_scene_v2_uses_new_camera_set():
    scene = json.loads(SCENE.read_text(encoding="utf-8"))
    assert [row["name"] for row in scene["cameras"]] == [
        "front_three_quarter_low",
        "rear_three_quarter_low",
        "high_front_three_quarter",
        "driver_side_low",
    ]
    assert [(row["yaw_deg"], row["pitch_deg"]) for row in scene["cameras"]] == [
        (-32.0, -21.0),
        (148.0, -18.0),
        (-18.0, -32.0),
        (-88.0, -16.0),
    ]


def test_bmw_m3_test_scene_v2_keeps_screenshot_boundary_explicit():
    scene = json.loads(SCENE.read_text(encoding="utf-8"))
    shots = scene["screenshots"]
    assert shots["status"] == "presentation-mock"
    assert shots["artifact_boundary"] == "synthetic-presentation-only"
    assert shots["renderer_evidence"] is False
    assert shots["runtime_proof"] is False
    assert len(shots["filenames"]) == 4
