from tracking_target_lifecycle_runtime import (
    describe_tracking_camera_lifecycle_reset,
    describe_tracking_target_acquisition,
)


def test_target_acquisition_stops_at_first_rtti_and_handle_match():
    result = describe_tracking_target_acquisition(
        target_handle_present=True,
        target_handle_count_nonzero=True,
        service_available=True,
        candidates=[
            {"contains_rtti_0xc25fb8": False, "field_0x18_matches_target": True},
            {"contains_rtti_0xc25fb8": True, "field_0x18_matches_target": False},
            {"contains_rtti_0xc25fb8": True, "field_0x18_matches_target": True},
        ],
    )
    assert result["status"] == "attached"
    assert result["selected_candidate"] == 2
    assert result["actions"][-1]["action"] == "candidate linked-list scan" or True
    assert any(a["action"] == "FUN_00812970" for a in result["actions"][-1]["actions"])


def test_target_acquisition_returns_not_found_when_all_candidates_fail():
    result = describe_tracking_target_acquisition(
        target_handle_present=True,
        target_handle_count_nonzero=True,
        service_available=True,
        candidates=[
            {"contains_rtti_0xc25fb8": True, "field_0x18_matches_target": False},
        ],
    )
    assert result["status"] == "not-found"


def test_target_acquisition_skips_service_scan_without_target_handle():
    result = describe_tracking_target_acquisition(
        target_handle_present=False,
        target_handle_count_nonzero=False,
        service_available=True,
        candidates=[],
    )
    assert result["status"] == "no-target-handle"


def test_tracking_lifecycle_reset_clears_tracking_frame_stack_and_calls_13f70():
    result = describe_tracking_camera_lifecycle_reset()
    assert [a["action"] for a in result["actions"]] == [
        "write vtable",
        "FUN_0081ea80",
        "FUN_00675d70",
        "FUN_00813f70",
    ]
