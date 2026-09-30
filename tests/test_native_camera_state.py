import json

import pytest

from camera_state_snapshot_runtime import CameraManagerState, snapshot_camera_state
from native_camera_state import (
    FORMAT,
    PROJECTION_DEFAULT_BITS,
    build_native_camera_state,
    build_native_camera_state_file,
)


def _snapshot(**overrides):
    values = {
        "active_buffer_index": 1,
        "camera_source": "opaque-retail-pointer",
        "mode": 3,
        "sub_index": 12,
        "camera_id": 8,
        "active_group": 4,
        "group_restore_value": 6,
        "sub_flag": 1,
    }
    values.update(overrides)
    return snapshot_camera_state(CameraManagerState(**values))


def test_native_camera_state_admits_exact_snapshot_manager_fields():
    report = build_native_camera_state(_snapshot())

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["active_buffer_index"] == 1
    assert report["update_in_progress"] is False
    assert report["manager_mode"] == 3
    assert report["buffer_sub_index"] == 12
    assert report["camera_id"] == 8
    assert report["active_group"] == 4
    assert report["group_restore_value"] == 6
    assert report["active_buffer_sub_flag"] == 1
    assert report["projection_default_bits"] == PROJECTION_DEFAULT_BITS

    assert report["source"]["opaque_camera_source_present"] is True
    assert report["boundary"]["opaque_camera_source_admitted"] is False
    assert report["boundary"]["seeds_active_buffer_only"] is True
    assert report["boundary"]["inactive_buffer_state_inferred"] is False
    assert report["boundary"]["camera_behavior_inferred"] is False


def test_native_camera_state_rejects_missing_group_restore_value():
    report = build_native_camera_state(
        _snapshot(group_restore_value=None)
    )

    assert report["ready"] is False
    assert any(
        "word5_group_restore_value must be an integer" in reason
        for reason in report["blocking_reasons"]
    )


def test_native_camera_state_rejects_invalid_active_buffer():
    report = _snapshot()
    report["source_context"]["active_buffer_index"] = 2

    native = build_native_camera_state(report)

    assert native["ready"] is False
    assert "native-camera:active-buffer-index-invalid" in (
        native["blocking_reasons"]
    )


def test_native_camera_state_rejects_sub_flag_outside_byte_range():
    report = _snapshot()
    report["source_context"]["active_buffer_sub_flag"] = 256

    native = build_native_camera_state(report)

    assert native["ready"] is False
    assert "native-camera:active-buffer-sub-flag-out-of-range" in (
        native["blocking_reasons"]
    )


def test_native_camera_state_rejects_wrong_source_contract():
    with pytest.raises(
        ValueError,
        match="SHIFT.CameraStateSnapshotRuntime/1",
    ):
        build_native_camera_state({"format": "SHIFT.Other/1"})


def test_native_camera_state_file_roundtrip(tmp_path):
    source = tmp_path / "camera-snapshot.json"
    output = tmp_path / "native-camera.json"
    source.write_text(json.dumps(_snapshot()), encoding="utf-8")

    report = build_native_camera_state_file(source, output)

    assert report["ready"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["format"] == FORMAT
    assert written["camera_id"] == 8
    assert written["active_buffer_index"] == 1
