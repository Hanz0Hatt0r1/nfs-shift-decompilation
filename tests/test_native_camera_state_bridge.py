from camera_state_snapshot_runtime import (
    CameraBufferState,
    CameraManagerState,
    begin_camera_buffer_swap,
    complete_camera_buffer_update,
    snapshot_camera_state,
)
from native_camera_state_bridge import (
    FORMAT,
    build_native_camera_state_bridge,
)


def _snapshot(*, source="opaque-camera"):
    return snapshot_camera_state(
        CameraManagerState(
            active_buffer_index=0,
            camera_source=source,
            mode=1,
            sub_index=7,
            camera_id=42,
            active_group=3,
            group_restore_value=2,
            sub_flag=1,
        )
    )


def test_snapshot_maps_only_proven_numeric_camera_state():
    report = build_native_camera_state_bridge(_snapshot())

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["active_index"] == 0
    assert report["update_in_progress"] is False
    assert report["manager_mode"] == 1
    assert report["buffer_sub_index"] == 7
    assert report["camera_id"] == 42
    assert report["active_group"] == 3
    assert report["group_restore_value"] == 2
    assert report["active_buffer_sub_flag"] == 1
    assert report["opaque_camera_source_present"] is True
    assert "opaque-camera" not in str(report)
    assert report["boundary"]["camera_source_transport"] == (
        "not-performed"
    )
    assert report["boundary"]["camera_math_inferred"] is False
    assert (
        report["boundary"]["inactive_buffer_state_inferred"]
        is False
    )


def test_swap_then_complete_updates_native_double_buffer_state():
    swap = begin_camera_buffer_swap(
        CameraBufferState(index=0)
    )
    complete = complete_camera_buffer_update(
        CameraBufferState(index=1)
    )

    report = build_native_camera_state_bridge(
        _snapshot(),
        [swap, complete],
    )

    assert report["ready"] is True
    assert report["active_index"] == 1
    assert report["update_in_progress"] is False
    assert report["transition_count"] == 2
    assert [row["status"] for row in report["transitions"]] == [
        "swapped",
        "ready",
    ]


def test_swapped_state_can_remain_update_in_progress():
    swap = begin_camera_buffer_swap(
        CameraBufferState(index=0)
    )
    report = build_native_camera_state_bridge(
        _snapshot(),
        [swap],
    )

    assert report["ready"] is True
    assert report["active_index"] == 1
    assert report["update_in_progress"] is True


def test_busy_transition_does_not_change_active_index():
    busy = begin_camera_buffer_swap(
        CameraBufferState(index=0),
        update_in_progress=True,
    )
    report = build_native_camera_state_bridge(
        _snapshot(),
        [busy],
    )

    assert report["ready"] is True
    assert report["active_index"] == 0
    assert report["update_in_progress"] is True


def test_unknown_group_restore_value_blocks_bridge():
    snapshot = snapshot_camera_state(
        CameraManagerState(
            active_buffer_index=0,
            camera_source=None,
            mode=0,
            sub_index=-1,
            camera_id=-1,
            active_group=-1,
            group_restore_value=None,
            sub_flag=0,
        )
    )

    report = build_native_camera_state_bridge(snapshot)

    assert report["ready"] is False
    assert any(
        "word5_group_restore_value is unresolved" in reason
        for reason in report["blocking_reasons"]
    )


def test_transition_sequence_mismatch_is_fail_closed():
    swap = begin_camera_buffer_swap(
        CameraBufferState(index=1)
    )
    report = build_native_camera_state_bridge(
        _snapshot(),
        [swap],
    )

    assert report["ready"] is False
    assert any(
        "swap-sequence-mismatch" in reason
        for reason in report["blocking_reasons"]
    )


def test_wrong_snapshot_contract_is_rejected():
    try:
        build_native_camera_state_bridge(
            {"format": "SHIFT.Other/1"}
        )
    except ValueError as error:
        assert "CameraStateSnapshotRuntime" in str(error)
    else:
        raise AssertionError("wrong snapshot contract was accepted")
