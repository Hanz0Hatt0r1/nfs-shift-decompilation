from camera_manager_constructor_runtime import (
    camera_manager_constructor_state,
    describe_camera_manager_buffer_copy,
)


def test_constructor_has_exact_camera_double_buffer_layout():
    result = camera_manager_constructor_state()
    groups = {g["name"]: g for g in result["object_groups"]}
    assert groups["CCameraView"]["first_offset"] == 0x20
    assert groups["CCameraView"]["second_offset"] == 0xBE0
    assert groups["StaticCamera"]["first_offset"] == 0x17A0
    assert groups["StaticCamera"]["second_offset"] == 0x1A20
    assert groups["TrackingCamera"]["first_offset"] == 0x1CA0
    assert groups["TrackingCamera"]["second_offset"] == 0x2100


def test_constructor_initial_transition_state_matches_source():
    result = camera_manager_constructor_state()
    writes = result["writes"]
    assert writes["+0x2574"] == 0xFFFFFFFF
    assert writes["+0x2578"] == 0xFFFFFFFF
    assert writes["+0x269c"] == 0
    assert writes["+0x26a0"] == 0xFFFFFFFF
    assert writes["+0x26a4"] == 0xFFFFFFFF
    assert writes["+0x26a8"] == 0
    assert writes["+0x26ac"] == 0


def test_constructor_preserves_raw_camera_selection_state():
    result = camera_manager_constructor_state()
    assert result["writes"]["+0x268c"] == 0x3FAAAAAB
    assert result["writes"]["+0x29f0"] == 3
    assert result["writes"]["+0x2a14"] == 3


def test_buffer_copy_requires_two_distinct_indices():
    result = describe_camera_manager_buffer_copy(old_buffer=0, new_buffer=1)
    copies = {c["name"]: c for c in result["copies"]}
    assert copies["camera-data"]["source"] == 0xBE0
    assert copies["camera-data"]["destination"] == 0x20
    assert copies["static-camera"]["source"] == 0x1A20
    assert copies["static-camera"]["destination"] == 0x17A0
    assert copies["tracking-camera"]["source"] == 0x2100
    assert copies["tracking-camera"]["destination"] == 0x1CA0


def test_buffer_copy_rejects_same_index():
    try:
        describe_camera_manager_buffer_copy(old_buffer=0, new_buffer=0)
    except ValueError:
        return
    raise AssertionError("expected double-buffer index rejection")
