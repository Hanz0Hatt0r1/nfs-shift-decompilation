from camera_view_profile_runtime import (
    CameraProfile,
    CameraViewState,
    camera_profile_catalog,
    normalized_profile_time,
    resolve_camera_data_object,
    select_camera_profile,
    service_profile_differs,
    service_profile_matches,
    load_camera_profile,
    update_cockpit_flag,
)


PROFILE = CameraProfile(
    profile_id=7,
    fov_bits_or_value=1.25,
    aspect_ratio_bits_or_value=1.777,
    near_z_bits_or_value=0.1,
    far_z_bits_or_value=750.0,
    service_value=2.0,
    hide_car=True,
    hide_car_rear_look=True,
    render_cockpit=True,
    allow_cycle=False,
)


def test_resolve_camera_data_object_forwards_non_null_e8():
    result = resolve_camera_data_object(
        {"plus_0x64": {"name": "root", "plus_0xe8": {"name": "nested"}}}
    )
    assert result["resolved"]["name"] == "nested"


def test_resolve_camera_data_object_keeps_root_when_e8_is_null():
    result = resolve_camera_data_object({"plus_0x64": {"name": "root", "plus_0xe8": None}})
    assert result["resolved"]["name"] == "root"


def test_service_profile_match_requires_non_negative_service_id():
    assert service_profile_matches(service_current_id=7, selected_profile_id=7)
    assert not service_profile_matches(service_current_id=-1, selected_profile_id=-1)


def test_service_profile_diff_treats_both_minus_one_as_equal():
    assert not service_profile_differs(service_current_id=-1, selected_profile_id=-1)
    assert service_profile_differs(service_current_id=-1, selected_profile_id=7)


def test_profile_time_clamps_to_unit_interval():
    assert normalized_profile_time(sample_time=0, profile_start=0, profile_end=10) == 0
    assert normalized_profile_time(sample_time=5, profile_start=0, profile_end=10) == 0.5
    assert normalized_profile_time(sample_time=20, profile_start=0, profile_end=10) == 1


def test_catalog_contains_exact_projection_and_camera_flag_offsets():
    fields = {row["name"]: row["offset"] for row in camera_profile_catalog()["fields"]}
    assert fields["FOV"] == 0x54
    assert fields["AspectRatio"] == 0x60
    assert fields["NearZ"] == 0x64
    assert fields["FarZ"] == 0x68
    assert fields["HideCar"] == 0xAC
    assert fields["AllowCycle"] == 0xAF


def test_profile_loader_uses_render_cockpit_for_ce10_and_hide_car_for_cdf0():
    _, result = load_camera_profile(
        CameraViewState(),
        requested_profile_id=7,
        resolved_profile=PROFILE,
        group_id=7,
        suppress_history_update=True,
    )
    assert result["actions"][10]["action"] == "FUN_0080ce10"
    assert result["actions"][11]["action"] == "FUN_0080cdf0"


def test_profile_loader_copies_projection_state_and_vectors():
    state, result = load_camera_profile(
        CameraViewState(),
        requested_profile_id=7,
        resolved_profile=PROFILE,
        group_id=7,
    )
    assert state.selected_profile_id == 7
    assert state.selected_profile_object == PROFILE
    assert result["status"] == "loaded"
    assert any(x.get("field") == "FOV" for x in result["actions"])
    assert any("+0x6c" in x.get("action", "") for x in result["actions"])


def test_profile_loader_honors_minus_two_as_reload_current_profile():
    state, _ = load_camera_profile(
        CameraViewState(selected_profile_id=7),
        requested_profile_id=-2,
        resolved_profile=PROFILE,
        suppress_history_update=True,
        group_id=7,
    )
    assert state.selected_profile_id == 7


def test_profile_selection_records_selector_and_history_path():
    state, result = select_camera_profile(
        CameraViewState(
            selected_profile_id=1,
            last_service_profile_id=7,
            last_fallback_profile_id=4,
        ),
        profile_id=9,
        service_current_id=9,
    )
    assert state.selector_profile_id == 9
    assert state.selected_profile_id == 1
    assert result["selector_profile_id"] == 9
    assert result["history_value_used"] == 4
    assert result["status"] == "service-profile-diff"


def test_cockpit_flag_unchanged_is_no_op():
    result = update_cockpit_flag(
        current_flag=1,
        new_flag=1,
        manager_swap_in_progress=False,
    )
    assert result["status"] == "unchanged"


def test_cockpit_flag_is_blocked_by_manager_swap_guard():
    result = update_cockpit_flag(
        current_flag=0,
        new_flag=1,
        manager_swap_in_progress=True,
    )
    assert result["status"] == "blocked-by-swap"


def test_cockpit_flag_reload_marks_camera_data_dirty():
    result = update_cockpit_flag(
        current_flag=0,
        new_flag=1,
        manager_swap_in_progress=False,
    )
    assert result["actions"][1]["action"] == "FUN_0081c920(-2,0)"
    assert result["actions"][3]["action"] == "FUN_0080cd40(manager)"


def test_profile_selection_uses_service_history_when_selector_matches_service_id():
    _, result = select_camera_profile(
        CameraViewState(last_service_profile_id=7, last_fallback_profile_id=4),
        profile_id=9,
        service_current_id=9,
    )
    assert result["history_value_used"] == 7
    assert result["status"] == "service-current-profile"


def test_profile_selection_does_not_reload_when_both_service_and_selector_are_minus_one():
    _, result = select_camera_profile(
        CameraViewState(last_service_profile_id=7, last_fallback_profile_id=4),
        profile_id=-1,
        service_current_id=-1,
    )
    assert result["status"] == "no-profile-reload"
    assert result["history_value_used"] is None
