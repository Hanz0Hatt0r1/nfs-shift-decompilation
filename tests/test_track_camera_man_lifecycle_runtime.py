from track_camera_man_lifecycle_runtime import (
    clear_tracking_input_slots,
    describe_track_camera_load,
    register_tracking_input_slot,
    resolve_target_from_attachment,
    set_tracking_target,
)


def test_load_uses_named_track_loader_then_fallback_path():
    result = describe_track_camera_load(
        param_name_present=True,
        helper_635e40_nonzero=False,
        helper_12180_named_result=False,
        helper_12180_fallback_result=True,
        local_cams_result=False,
    )
    assert result["status"] == 1
    assert any(a.get("path_mode") == "named-path" for a in result["actions"])
    assert any(a.get("path_mode") == "fallback-path" for a in result["actions"])


def test_load_always_or_accumulates_local_cams_status():
    result = describe_track_camera_load(
        param_name_present=False,
        helper_635e40_nonzero=True,
        helper_12180_named_result=False,
        helper_12180_fallback_result=False,
        local_cams_result=True,
    )
    assert result["status"] == 1
    assert any(a["action"] == "OR status into +0xb0" for a in result["actions"])


def test_set_tracking_target_writes_e8():
    result = set_tracking_target(target="object")
    assert result["action"]["value"] == "object"


def test_clear_tracking_input_slots_releases_nonempty_entries_and_zeros_all():
    updated, result = clear_tracking_input_slots(["a", None, "b", None, None, None, None])
    assert updated == [None] * 7
    assert result["released_count"] == 2


def test_register_tracking_input_slot_requires_valid_empty_slot_and_frame_stack():
    slots, result = register_tracking_input_slot(
        [None] * 7,
        action_index=3,
        action_object="a3",
        frame_stack_accepts=True,
    )
    assert slots[3] == "a3"
    assert result["return_low_byte"] == 1

    _, rejected = register_tracking_input_slot(
        slots,
        action_index=3,
        action_object="new",
        frame_stack_accepts=True,
    )
    assert rejected["return_low_byte"] == 0


def test_register_rejects_index_six_plus_one_and_zero():
    slots = [None] * 7
    _, bad7 = register_tracking_input_slot(
        slots,
        action_index=7,
        action_object="x",
        frame_stack_accepts=True,
    )
    _, bad0 = register_tracking_input_slot(
        slots,
        action_index=0,
        action_object="x",
        frame_stack_accepts=True,
    )
    assert bad7["status"] == "rejected"
    assert bad0["status"] == "rejected"


def test_target_resolution_stops_on_first_service_match():
    result = resolve_target_from_attachment(
        target_attachment="handle",
        service_candidates=[
            {"name": "a", "matches_attachment": False},
            {"name": "b", "matches_attachment": True},
            {"name": "c", "matches_attachment": True},
        ],
    )
    assert result["status"] == "service-match"
    assert result["selected"]["name"] == "b"


def test_target_resolution_falls_back_to_selected_camera_index():
    result = resolve_target_from_attachment(
        target_attachment=None,
        service_candidates=[],
    )
    assert result["status"] == "camera-config-fallback"
    assert any(a["action"] == "FUN_00811570" for a in result["actions"])
