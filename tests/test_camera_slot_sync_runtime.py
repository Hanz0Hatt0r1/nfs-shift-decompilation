from camera_slot_sync_runtime import (
    CameraServiceSyncState,
    CameraViewSyncRecord,
    describe_camera_slot_sync,
)


def _records():
    return [
        CameraViewSyncRecord(source=f"view-{i}", field_0x90=i, field_0x98=i + 10, field_0xa0=i + 20, field_0xa8=i + 30)
        for i in range(3)
    ]


def test_requires_exactly_three_view_records():
    try:
        describe_camera_slot_sync(
            slot_root_present=True,
            trigger_value=1,
            view_records=_records()[:2],
            service=CameraServiceSyncState(service_present=False),
        )
    except ValueError:
        return
    raise AssertionError("expected exact three-record requirement")


def test_slot_sync_has_nested_sync_then_fixed_vtable_order_for_each_record():
    result = describe_camera_slot_sync(
        slot_root_present=True,
        trigger_value=42,
        view_records=_records(),
        service=CameraServiceSyncState(service_present=False),
    )
    actions = result["slot_actions"]
    assert actions[0]["action"] == "FUN_0080db30"
    assert actions[1]["action"].endswith("+0x24()")
    assert actions[2]["action"].endswith("+0x6c()")
    assert actions[3]["argument"] == 0
    assert actions[4]["argument"] == 10
    assert actions[5]["argument"] == 20
    assert actions[6]["argument"] == 30
    assert len(actions) == 1 + 3 * 7


def test_null_slot_root_skips_view_record_block_but_keeps_service_sync():
    result = describe_camera_slot_sync(
        slot_root_present=False,
        trigger_value=0,
        view_records=_records(),
        service=CameraServiceSyncState(
            service_present=True,
            value_0xe0=1,
            shadow_0xf4=0,
        ),
    )
    assert result["slot_actions"] == []
    assert result["service_actions"][0]["action_if_mismatch"].startswith("service vtable +0x48") is False


def test_equal_triple_uses_vtable_plus_48_without_shadow_writes():
    result = describe_camera_slot_sync(
        slot_root_present=True,
        trigger_value=0,
        view_records=_records(),
        service=CameraServiceSyncState(
            value_0xe0=1, value_0xe4=2, value_0xe8=3,
            shadow_0xf4=1, shadow_0xf8=2, shadow_0xfc=3,
            value_0xec=4, value_0xf0=5, shadow_0x100=4, shadow_0x104=5,
        ),
    )
    triple_actions = [x for x in result["service_actions"] if "+0xe0/+0xe4/+0xe8" in x.get("condition", "")]
    assert triple_actions[0]["action"] == "service vtable +0x48()"


def test_different_pair_calls_service_plus_4c_then_mirrors_pair():
    result = describe_camera_slot_sync(
        slot_root_present=False,
        trigger_value=0,
        view_records=_records(),
        service=CameraServiceSyncState(
            value_0xec=11, value_0xf0=12, shadow_0x100=0, shadow_0x104=0,
        ),
    )
    assert result["service_actions"][-2]["action"].startswith("service vtable +0x4c")
    assert result["service_actions"][-1]["action"] == "+0x100/+0x104 = +0xec/+0xf0"
