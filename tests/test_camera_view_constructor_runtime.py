from camera_view_constructor_runtime import (
    choose_initial_camera_profile,
    describe_view_constructor,
    normalize_initial_profile_id,
)


def test_initial_camera_priority_starts_with_bumper():
    result = choose_initial_camera_profile(
        {"Cam_Bumper": True, "Cam_Bonnet": True, "Cam_Cockpit": True, "Cam_Chase": True}
    )
    assert result["profile_name"] == "BumperCam"


def test_bonnet_is_used_when_bumper_is_unavailable():
    result = choose_initial_camera_profile(
        {"Cam_Bumper": False, "Cam_Bonnet": True, "Cam_Cockpit": True}
    )
    assert result["profile_name"] == "BonnetCam"


def test_cockpit_is_used_before_chase_when_cockpit_is_available():
    result = choose_initial_camera_profile(
        {"Cam_Bumper": False, "Cam_Bonnet": False, "Cam_Cockpit": True, "Cam_Chase": True}
    )
    assert result["profile_name"] == "CockpitCam"


def test_chase_precedes_shotgun_when_cockpit_is_unavailable():
    result = choose_initial_camera_profile(
        {"Cam_Cockpit": False, "Cam_Chase": True, "Cam_Shotgun": True}
    )
    assert result["profile_name"] == "ChaseCam"


def test_shotgun_is_used_when_chase_is_unavailable():
    result = choose_initial_camera_profile(
        {"Cam_Cockpit": False, "Cam_Chase": False, "Cam_Shotgun": True}
    )
    assert result["profile_name"] == "ShotgunCam"


def test_missing_capabilities_fall_back_to_chase():
    result = choose_initial_camera_profile({})
    assert result["profile_name"] == "ChaseCam"
    assert result["status"] == "fallback"


def test_constructor_normalizes_only_minus_one_to_zero():
    assert normalize_initial_profile_id(-1) == 0
    assert normalize_initial_profile_id(0) == 0
    assert normalize_initial_profile_id(17) == 17


def test_constructor_copies_selected_profile_id_into_three_history_slots():
    result = describe_view_constructor(selected_profile_id=-1)
    assert result["raw_selected_profile_id"] == -1
    assert result["normalized_profile_id"] == 0
    assert result["writes"]["+0xc4"] == 0
    assert result["writes"]["+0xc8"] == 0
    assert result["writes"]["+0xcc"] == 0


def test_constructor_records_projection_and_nested_state_delegates():
    result = describe_view_constructor(selected_profile_id=3)
    assert result["delegates"][0]["action"] == "FUN_0081aeb0"
    assert result["delegates"][1]["action"] == "FUN_0081c3b0"
