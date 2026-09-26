from static_camera_runtime import (
    copy_config_record,
    copy_static_camera_state,
    interpolate_static_camera_records,
    reset_static_camera_state,
    static_camera_defaults,
    static_camera_property_registration,
    describe_static_camera_constructor,
    describe_static_camera_reset,
    set_static_camera_runtime_pair,
    set_static_camera_function_bindings,
    copy_static_camera_runtime_payload,
)


def test_static_defaults_match_projection_and_target_sentinels():
    result = static_camera_defaults()
    assert result["raw"]["+0x64"] == 0x3F490FDB
    assert result["raw"]["+0x68"] == 1
    assert result["raw"]["+0x6c"] == 0x3F800000
    assert result["raw"]["+0x70"] == 0x443B8000
    assert result["integer_defaults"]["+0x1d"] == 0xFFFFFFFF
    assert result["integer_defaults"]["+0x1f"] == 0xFFFFFFFF


def test_config_record_copy_has_exact_25_dwords():
    source = {i * 4: i for i in range(25)}
    result = copy_config_record(source)
    assert result["count"] == 25
    assert result["range"] == ["+0x00", "+0x60"]


def test_static_camera_copy_preserves_special_d8_reset():
    source = {offset: offset for offset in (
        list(range(0x10, 0x30, 4))
        + [0x60]
        + list(range(0x64, 0xC9, 4))
        + [0xCC, 0xD0, 0xDC]
        + list(range(0xE0, 0xF0, 4))
    )}
    result = copy_static_camera_state(source)
    assert result["special_writes"]["+0xd8"] == 0xFFFFFFFF
    assert "+0xc8" in result["copied_offsets"]
    assert "+0xcc" in result["copied_offsets"]
    assert "+0xdc" in result["copied_offsets"]


def test_static_reset_releases_string_fields_and_base_state():
    result = reset_static_camera_state()
    assert [a["target"] for a in result["actions"] if a["action"] == "FUN_006310c0"] == [
        "+0xdc", "+0xd4", "+0xcc", "+0x60"
    ]


def test_property_registration_preserves_overlapping_shake_offsets():
    result = static_camera_property_registration()
    props = [(p["name"], p["offset"]) for p in result["properties"]]
    assert ("ShakeFrequency", 0xB8) in props
    assert ("ShakeScreenVelocity", 0xB8) in props
    assert ("ShakeFrequencyMin", 0xB4) in props
    assert ("ShakeScreenVelocityMin", 0xB4) in props
    assert ("ActiveAreas", 0x2C) in props


def test_static_interpolation_reproduces_component_blend():
    result = interpolate_static_camera_records(
        first=[1, 10, 3],
        second=[3, 20, 5],
        alpha=0.25,
    )
    assert result["value"] == [1.5, 12.5, 3.5]


def test_static_camera_record_lookup_copies_snapshot_and_zeroes_aux():
    result = resolve_static_camera_record(
        source_pointer="record0",
        record_helper_success=True,
        record_snapshot={0x10: 1, 0x64: 7},
    )
    assert result["status"] == "resolved"
    assert result["actions"][1]["action"] == "FUN_00812a00"
    assert result["actions"][2] == {"action": "write +0x64", "value": 0}


def test_static_camera_blend_uses_absolute_wrap_counts_times_eight():
    result = blend_static_camera_records(
        first_value=[1, 10, 3],
        second_value=[3, 20, 5],
        alpha=0.25,
        first_wrap_count=-1,
        second_wrap_count=2,
    )
    assert result["value"] == [1.5, 2.5, 3.5]


def test_static_camera_constructor_sets_exact_shake_rates_and_targets():
    result = describe_static_camera_constructor()
    assert result["writes"]["+0x3c"] == 0x3F000000
    assert result["shake"]["+0x84"]["rate"] == 0x40C00000
    assert result["shake"]["+0xD8"]["rate"] == 0x41800000
    assert result["shake"]["+0x84"]["target"] == [0x3C23D70A, 0x3C23D70A, 0x3BA3D70A]


def test_static_camera_reset_delegates_to_13f70():
    result = describe_static_camera_reset()
    assert result["actions"][0]["action"] == "FUN_00813f70"


def test_static_camera_runtime_setters_preserve_exact_offsets():
    result = set_static_camera_runtime_pair(
        pair_a=["a", "b"],
        pair_b=["c", "d"],
    )
    assert result["writes"]["+0x324/+0x328"] == ["a", "b"]
    assert result["writes"]["+0x32c/+0x330"] == ["c", "d"]


def test_static_camera_function_bindings_preserve_all_four_offsets():
    result = set_static_camera_function_bindings(
        slot_380=1, slot_384=2, slot_388=3, slot_34c=4
    )
    assert result["writes"] == {"+0x380":1, "+0x384":2, "+0x388":3, "+0x34c":4}


def test_static_camera_runtime_copy_uses_base_then_plus_48_payload():
    result = copy_static_camera_runtime_payload(
        destination="dst",
        source="src",
    )
    assert [a["action"] for a in result["actions"]] == [
        "FUN_0081af70",
        "FUN_00815620",
    ]
    assert result["actions"][1]["destination"] == "dst+0x48"
