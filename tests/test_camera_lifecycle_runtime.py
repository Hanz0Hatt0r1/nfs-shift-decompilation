from camera_lifecycle_runtime import (
    describe_manager_initialize,
    describe_manager_reset,
    describe_post_load_lifecycle,
    describe_post_load_sync,
    describe_slot_initializer,
    describe_time_origin_refresh,
    resolve_lifecycle_timestamp,
)


def test_lifecycle_timestamp_uses_base_only_without_high_resolution_flag():
    result = resolve_lifecycle_timestamp(100)
    assert result["timestamp"] == 100
    assert result["expression"] == "+0x44"


def test_lifecycle_timestamp_adds_opaque_high_resolution_delta():
    result = resolve_lifecycle_timestamp(
        100, high_resolution_enabled=True, high_resolution_delta=7
    )
    assert result["timestamp"] == 107
    assert "FUN_0040f0d0" in result["source"]


def test_initialize_resets_all_three_slots_then_writes_time_cursor():
    result = describe_manager_initialize(
        base_timestamp=100,
        high_resolution_enabled=False,
    )
    assert [x["slot_index"] for x in result["actions"][:3]] == [0, 1, 2]
    assert result["actions"][-1]["action"] == "write +0x828"
    assert result["time_cursor_after"] == 100


def test_reset_has_three_slot_resets_global_reset_and_time_cursor():
    result = describe_manager_reset(
        base_timestamp=100,
        high_resolution_enabled=True,
        high_resolution_delta=9,
    )
    assert len(result["slot_reset"]) == 3 if isinstance(result["slot_reset"], list) else result["slot_reset"]["count"] == 3
    assert result["actions"][3]["action"] == "FUN_00818940"
    assert result["time_cursor_after"] == 109


def test_time_origin_refresh_only_writes_cursor():
    result = describe_time_origin_refresh(
        base_timestamp=50, high_resolution_enabled=False
    )
    assert result["actions"] == [{"action": "write +0x828", "value": 50}]


def test_post_load_sync_only_syncs_enabled_slots_and_marks_complete():
    result = describe_post_load_sync(
        slot_container_present=True,
        slot_enabled=[True, False, True],
    )
    assert [x["slot_index"] for x in result["actions"][:-1]] == [0, 2]
    assert result["actions"][-1] == {"action": "write +0x82c", "value": 1}


def test_post_load_sync_skips_everything_without_slot_container():
    result = describe_post_load_sync(
        slot_container_present=False,
        slot_enabled=[True, True, True],
    )
    assert result["actions"] == []


def test_post_load_lifecycle_calls_sync_only_when_marker_is_clear_then_clears_marker():
    result = describe_post_load_lifecycle(
        feature_enabled=True,
        sync_marker=False,
        slot_container_present=True,
        slot_enabled=[True, True, False],
    )
    assert result["actions"][0]["operation"] == "post-load-sync"
    assert result["actions"][-1] == {"action": "write +0x82c", "value": 0}
    assert result["sync_marker_after"] is False


def test_post_load_lifecycle_does_not_resync_when_marker_is_set():
    result = describe_post_load_lifecycle(
        feature_enabled=True,
        sync_marker=True,
        slot_container_present=True,
        slot_enabled=[True, True, True],
    )
    assert len(result["actions"]) == 1
    assert result["actions"][0] == {"action": "write +0x82c", "value": 0}


def test_slot_initializer_exposes_exact_core_state_defaults():
    result = describe_slot_initializer(slot_base="slot0")
    writes = result["writes"]
    assert writes["+0x2560"] == 0
    assert writes["+0x2574"] == -1
    assert writes["+0x2578"] == -1
    assert writes["+0x26a0"] == -1
    assert writes["+0x26a4"] == -1
    assert writes["+0x26a8"] == 0
