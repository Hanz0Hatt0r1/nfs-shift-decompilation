from derived_camera_view_runtime import (
    describe_derived_camera_view_constructor,
    describe_derived_camera_view_delete,
    describe_derived_camera_view_reset,
)


def test_derived_constructor_preserves_exact_projection_overrides():
    result = describe_derived_camera_view_constructor()
    assert result["writes"]["+0x34"] == 0x3F860A92
    assert result["writes"]["+0x48"] == 0x3F000000
    assert result["writes"]["+0x4c"] == 0
    assert result["writes"]["+0x50"] == 0
    assert result["writes"]["+0x5c"] == 0


def test_derived_constructor_sets_final_vtable():
    result = describe_derived_camera_view_constructor()
    assert result["actions"][5]["value"] == "PTR_FUN_00b162e8"


def test_derived_reset_delegates_to_base_reset():
    result = describe_derived_camera_view_reset()
    assert result["actions"][1]["action"] == "FUN_0081ac60"


def test_derived_delete_calls_cleanup_only_when_flag_is_set():
    result = describe_derived_camera_view_delete()
    assert result["actions"][1]["condition"] == "param_1 & 1"
