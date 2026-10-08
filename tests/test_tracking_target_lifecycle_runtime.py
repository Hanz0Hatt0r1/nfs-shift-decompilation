from tracking_target_lifecycle_runtime import (
    FORMAT,
    describe_tracking_camera_lifecycle_reset,
    describe_tracking_override_resolution,
    describe_tracking_target_acquisition,
)


def test_override_resolution_stops_at_first_tracking_camera_name_match():
    result = describe_tracking_override_resolution(
        override_name_present=True,
        override_name_count_nonzero=True,
        service_available=True,
        candidates=[
            {"contains_rtti_0xc25fb8": False, "name_0x60_matches_override_0xd4": True},
            {"contains_rtti_0xc25fb8": True, "name_0x60_matches_override_0xd4": False},
            {"contains_rtti_0xc25fb8": True, "name_0x60_matches_override_0xd4": True},
        ],
    )
    assert result["format"] == FORMAT
    assert result["status"] == "attached"
    assert result["selected_candidate"] == 2
    assert result["semantic_classification"] == "camera-to-camera override linkage"
    assert result["not_vehicle_target_proof"] is True
    compare = result["candidate_trace"]["actions"][1]
    assert compare["arguments"]["candidate_name"] == "candidate byte +0x60"
    assert "+0xd4" in compare["arguments"]["override_name"]
    assert any(a["action"] == "FUN_00812970" for a in result["actions"][-1]["actions"])


def test_override_resolution_returns_not_found_when_all_candidates_fail():
    result = describe_tracking_override_resolution(
        override_name_present=True,
        override_name_count_nonzero=True,
        service_available=True,
        candidates=[
            {"contains_rtti_0xc25fb8": True, "name_0x60_matches_override_0xd4": False},
        ],
    )
    assert result["status"] == "not-found"
    assert result["not_vehicle_target_proof"] is True


def test_override_resolution_skips_service_scan_without_override_name():
    result = describe_tracking_override_resolution(
        override_name_present=False,
        override_name_count_nonzero=False,
        service_available=True,
        candidates=[],
    )
    assert result["status"] == "no-override-name"


def test_legacy_target_acquisition_name_is_compatibility_only():
    result = describe_tracking_target_acquisition(
        target_handle_present=True,
        target_handle_count_nonzero=True,
        service_available=True,
        candidates=[
            {"contains_rtti_0xc25fb8": True, "field_0x18_matches_target": True},
        ],
    )
    assert result["status"] == "attached"
    assert result["compatibility_wrapper"] == "describe_tracking_target_acquisition"
    assert result["not_vehicle_target_proof"] is True
    assert result["evidence"]["reflection_target_field"] == "CTrackingCamData byte +0x78"
    assert "+0xd4" in result["evidence"]["reflection_override_field"]


def test_tracking_lifecycle_reset_clears_tracking_frame_stack_and_calls_13f70():
    result = describe_tracking_camera_lifecycle_reset()
    assert [a["action"] for a in result["actions"]] == [
        "write vtable",
        "FUN_0081ea80",
        "FUN_00675d70",
        "FUN_00813f70",
    ]
