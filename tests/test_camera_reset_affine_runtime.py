from camera_reset_affine_runtime import (
    camera_jump_dispatch,
    initialize_affine_basis,
    reset_camera_target_state,
)


def test_affine_basis_zeroes_six_explicit_components_and_sets_w_one():
    result = initialize_affine_basis(list(range(16)))
    assert result["matrix"][3] == 0.0
    assert result["matrix"][7] == 0.0
    assert result["matrix"][11] == 0.0
    assert result["matrix"][12:15] == [0.0, 0.0, 0.0]
    assert result["matrix"][15] == 1.0


def test_target_state_reset_clears_local_state_and_sets_valid_flag():
    result = reset_camera_target_state(resolved_target_data=None)
    assert result["writes"]["+0x58"] == 0
    assert result["writes"]["+0x30"] == 0
    assert result["writes"]["+0x68"] == 1


def test_target_state_reset_copies_resolved_defaults_from_target_data():
    result = reset_camera_target_state(
        resolved_target_data={
            0x20: 1,
            0x24: 2,
            0x28: 3,
            0x64: 4,
            0x6c: 5,
            0x70: 6,
        }
    )
    assert result["writes"]["+0x10"] == 1
    assert result["writes"]["+0x18"] == 3
    assert result["writes"]["+0x34"] == 4
    assert result["writes"]["+0x40"] == 6


def test_jump_dispatch_keeps_vtable_boundary_opaque():
    result = camera_jump_dispatch(
        vtable_target_present=True,
        mode=2,
        payload="p",
    )
    assert result["action"]["action"] == "vtable +0x58"
    assert result["action"]["mode"] == 2
