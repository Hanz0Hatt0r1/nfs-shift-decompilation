from static_camera_runtime import (
    copy_config_record,
    copy_static_camera_state,
    interpolate_static_camera_records,
    reset_static_camera_state,
    static_camera_defaults,
    static_camera_property_registration,
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
