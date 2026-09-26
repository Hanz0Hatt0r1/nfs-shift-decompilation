from tracking_target_state_sync_runtime import synchronize_tracking_target_state


def test_target_metadata_is_written_then_controller_flag_cleared():
    result = synchronize_tracking_target_state(
        target_metadata=[1, 2, 3],
        controller_camera_data={},
        camera_data_fallback={0x10: 4, 0x14: 5, 0x18: 6, 0x34: 7},
        controller_spline_id=-1,
        controller_target_spline_id=-1,
        controller_object_present=False,
    )
    assert result["writes"]["+0x74"] == 1
    assert result["writes"]["+0x7c"] == 3
    assert result["writes"]["+0x80"] == 0


def test_missing_controller_object_uses_camera_data_fallback_fields():
    result = synchronize_tracking_target_state(
        target_metadata=None,
        controller_camera_data={},
        camera_data_fallback={0x10: 4, 0x14: 5, 0x18: 6, 0x34: 7},
        controller_spline_id=-1,
        controller_target_spline_id=-1,
        controller_object_present=False,
    )
    assert result["writes"]["+0x2dc"] == 4
    assert result["writes"]["+0x2e4"] == 6
    assert result["writes"]["+0x2e8"] == 7


def test_controller_camera_data_is_remapped_into_2a0_to_2e8():
    result = synchronize_tracking_target_state(
        target_metadata=[1, 2, 3],
        controller_camera_data={
            0x294: 1, 0x298: 2, 0x29c: 3,
            0x2a0: 4, 0x2a4: 5, 0x2a8: 6, 0x2ac: 7,
            0x2b0: 8, 0x2b4: 9, 0x2b8: 10, 0x2bc: 11,
            0x2c0: 12, 0x2c4: 13, 0x2c8: 14, 0x2cc: 15,
            0x2d0: 16, 0x2d4: 17, 0x2d8: 18, 0x2dc: 19,
            0x2e0: 20, 0x2e4: 21, 0x2e8: 22,
        },
        camera_data_fallback={},
        controller_spline_id=-1,
        controller_target_spline_id=3,
        controller_object_present=True,
    )
    assert result["writes"]["+0x2b0"] == 1
    assert result["writes"]["+0x2bc"] == 4
    assert result["writes"]["+0x2e8"] == 16
    assert result["writes"]["+0x2ec"] == 12
    assert result["writes"]["+0x314"] == 22


def test_target_spline_branch_populates_extended_state():
    result = synchronize_tracking_target_state(
        target_metadata=[1, 2, 3],
        controller_camera_data={offset: offset for offset in range(0x2c0, 0x2ec, 4)},
        camera_data_fallback={},
        controller_spline_id=-1,
        controller_target_spline_id=0,
        controller_object_present=True,
    )
    assert result["writes"]["+0x318"] == 0x2c0
    assert result["writes"]["+0x320"] == 0x2c8
