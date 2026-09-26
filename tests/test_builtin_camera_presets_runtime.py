from builtin_camera_presets_runtime import (
    builtin_camera_preset_table,
    f32_from_bits,
    free_look_and_pitch_limits,
    u32,
)


def test_builtin_preset_order_matches_constructor():
    result = builtin_camera_preset_table()
    assert result["selection_order"] == [
        "BumperCam",
        "BonnetCam",
        "CockpitCam",
        "ChaseCam",
        "ShotgunCam",
        "Local_Bow",
        "Local_Starboard",
        "Local_Port",
        "Local_Aft",
    ]


def test_bumper_and_bonnet_raw_overrides_match_source():
    result = builtin_camera_preset_table()
    presets = {p["name"]: p for p in result["presets"]}
    assert presets["BumperCam"]["overrides"]["+0x34"] == 0xBFE66666
    assert presets["BonnetCam"]["overrides"]["+0x38"] == 0xBDBEDFA4
    assert presets["BonnetCam"]["byte_overrides"]["+0xae"] == 1


def test_cockpit_and_shotgun_preserve_distinct_orientation_bits():
    result = builtin_camera_preset_table()
    presets = {p["name"]: p for p in result["presets"]}
    assert presets["CockpitCam"]["overrides"]["+0x38"] == 0xBD8F5C29
    assert presets["ShotgunCam"]["overrides"]["+0x38"] == 0xBC23D70A
    assert presets["ShotgunCam"]["byte_overrides"]["+0xaf"] == 0


def test_chase_preset_keeps_non_default_b4_and_camera_axes():
    result = builtin_camera_preset_table()
    chase = next(p for p in result["presets"] if p["name"] == "ChaseCam")
    assert chase["overrides"]["+0xb4"] == 2
    assert chase["overrides"]["+0x48"] == 0x40000000
    assert chase["byte_overrides"]["+0xb0"] == 1


def test_local_camera_dynamic_orientation_expressions_are_preserved():
    result = builtin_camera_preset_table()
    presets = {p["name"]: p for p in result["presets"]}
    assert presets["Local_Bow"]["overrides"]["+0x3c"] == 0x40490FDB
    assert presets["Local_Starboard"]["symbolic_overrides"]["+0x3c"].startswith("_DAT_00b8de1c")
    assert presets["Local_Port"]["symbolic_overrides"]["+0x3c"] == "_DAT_00b8de1c"
    assert "+0xaf" not in presets["Local_Aft"]["byte_overrides"]


def test_global_limits_match_exact_raw_bits_and_offsets():
    result = free_look_and_pitch_limits()
    yaw = result["limits"]["FreeLookYawLimits"]
    assert yaw["raw_bits"] == [0xC2700000, 0x42700000]
    assert yaw["float_values"] == [-60.0, 60.0]
    assert result["property_offsets"]["FreeLookPitchLimits"] == 0x2C0
    assert result["limits"]["RotateChaseCamPitchLimits"]["float_values"] == [-70.0, 0.0]


def test_u32_normalizes_decompiler_signed_literals():
    assert u32(-0x4019999A) == 0xBFE66666
    assert f32_from_bits(0x3F8C0831) > 1.0
