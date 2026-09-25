from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / "tests/scenes/bmw_m3_e36_render_demo_scene.json"
SCREENSHOT = ROOT / "docs/artifacts/render/bmw_m3_e36_render_demo.png"


def test_bmw_m3_e36_render_demo_scene_checkpoint():
    scene = json.loads(SCENE.read_text(encoding="utf-8"))
    assert scene["format"] == "SHIFT.BMWM3RenderDemoScene/1"
    assert scene["ready"] is True
    assert scene["source"]["resource"] == "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
    assert scene["source"]["resource_sha256"] == "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"
    assert scene["geometry"]["vertex_count"] == 3550
    assert scene["geometry"]["triangle_count"] == 5034
    assert scene["geometry"]["primitive_count"] == 6
    assert SCREENSHOT.exists()
    assert hashlib.sha256(SCREENSHOT.read_bytes()).hexdigest() == scene["screenshot"]["sha256"]
