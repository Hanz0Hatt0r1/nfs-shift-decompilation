import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "camera_follow_p14_update_order.json"


def test_update_order_is_physics_before_mode2_camera_on_admitted_path():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.CameraFollowP14UpdateOrder/1"
    assert payload["ready"] is True

    callback = payload["callback_registration"]
    assert callback["owner"] == "FUN_0070fe90() cPhysicsManager"
    assert callback["field"] == "+0x298"
    assert callback["target"] == "FUN_00489f70"

    order = payload["scheduler_order"]
    assert order["physics_scheduler_callsite"] == "0x0071196b -> FUN_0070f940"
    assert order["default_scheduler_call"] == "0x0070f9af -> FUN_007155e0"
    assert order["callback_dispatch_callsite"] == "0x007119a7 -> FUN_0070f890"
    assert order["ordering"] == "physics scheduler completes before callback dispatcher"

    camera = payload["camera_update_chain"]
    assert "FUN_0080b820" in camera["camera_manager_update"]
    assert camera["active_source_field"] == "CameraManager+0x2568"
    assert camera["mode2_target"] == "FUN_008216a0"

    adjudication = payload["adjudication"]
    assert adjudication["cphysics_callback_owner_proven"] is True
    assert adjudication["physics_before_camera_callback_proven"] is True
    assert adjudication["mode2_per_frame_update_after_physics_proven"] is True
    assert adjudication["phase651_request_4_complete"] is True
    assert adjudication["applies_to_admitted_default_steady_path"] is True
    assert adjudication["phase651_request_3_complete"] is False
    assert adjudication["native_camera_follow_ready"] is False
    assert adjudication["external_provider_count"] == 7
