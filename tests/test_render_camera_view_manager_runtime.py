from render_camera_view_manager_runtime import (
    describe_camera_manager_refresh_bridge,
    describe_render_camera_view_manager_constructor,
    describe_render_camera_view_manager_delete,
    describe_render_camera_view_manager_reset,
    get_render_camera_view_manager_singleton,
)


def test_constructor_sets_exact_vtable_and_runtime_label():
    result = describe_render_camera_view_manager_constructor()
    assert result["actions"][1]["value"] == "PTR_FUN_00b15aa8"
    assert result["actions"][2]["argument"] == "RenderCameraViewManager"


def test_reset_delegates_to_00647b20():
    result = describe_render_camera_view_manager_reset()
    assert result["actions"][1]["action"] == "FUN_00647b20"


def test_delete_only_frees_when_low_bit_is_set():
    result = describe_render_camera_view_manager_delete(delete_flag=0)
    assert result["actions"][1]["condition"] == "(delete_flag & 1) != 0"
    result = describe_render_camera_view_manager_delete(delete_flag=1)
    assert result["delete_flag"] == 1


def test_singleton_initializes_once_and_registers_atexit():
    result = get_render_camera_view_manager_singleton(guard_before=0)
    assert result["status"] == "initialized"
    assert result["guard_after"] == 1
    assert result["actions"][2]["action"] == "_atexit"


def test_singleton_returns_existing_without_reconstruction():
    result = get_render_camera_view_manager_singleton(guard_before=1)
    assert result["status"] == "existing"
    assert result["actions"] == []


def test_refresh_bridge_calls_camera_manager_refresh_and_returns_zero():
    result = describe_camera_manager_refresh_bridge()
    assert [a["action"] for a in result["actions"]] == [
        "FUN_0080bfb0",
        "FUN_0080c180",
    ]
    assert result["return_value"] == 0
