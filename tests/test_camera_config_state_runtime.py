from camera_config_state_runtime import (
    describe_camera_config_defaults,
    describe_camera_config_load,
    describe_camera_slot_reset,
    describe_reflected_camera_config,
)


def test_defaults_initialize_exactly_two_interleaved_profiles():
    result = describe_camera_config_defaults()
    assert result["profile_count"] == 2
    assert result["profiles"][0][0x20] == 0x3F800000
    assert result["profiles"][0][0x88] == 0x3F490FF9
    assert result["profiles"][1][0x10] == 0x3F800000
    assert result["profiles"][1][0xA4] == 0x3FAAA993


def test_defaults_preserve_tail_state_values():
    result = describe_camera_config_defaults()
    assert result["tail_writes"]["+0x6c"] == 0x3F800000
    assert result["tail_writes"]["+0xa8"] == 1
    assert result["tail_writes"]["+0xac"] == 1
    assert result["tail_writes"]["+0xbc"] == 1
    assert result["tail_writes"]["+0xc0"] == 0


def test_reflected_config_exposes_exact_destination_helpers():
    result = describe_reflected_camera_config(source_values={0x08: 1, 0x40: 2, 0xA8: 1, 0xAC: 1})
    by_offset = {row["destination"]: row["helper"] for row in result["reads"]}
    assert by_offset["+0x08"] == "FUN_00806e70"
    assert by_offset["+0x40"] == "FUN_00806ea0"
    assert result["flag_reads"][0]["destination"] == "+0xa8"
    assert result["flag_reads"][-1]["destination"] == "+0xbc"


def test_reflected_config_falls_back_when_required_flags_are_zero():
    result = describe_reflected_camera_config(source_values={0xA8: 0, 0xAC: 1})
    assert "FUN_0080d880" in result["fallback_condition"]["fallback"]


def test_config_load_uses_defaults_when_root_or_variation_is_unavailable():
    for available, variation in ((False, 7), (True, 0)):
        result = describe_camera_config_load(
            config_available=available,
            config_handle="cfg",
            variation_id=variation,
        )
        assert result["status"] == "defaults"
        assert result["actions"][0]["action"] == "FUN_0080d880"


def test_config_load_mirrors_nine_pointer_slots_d0_through_f0():
    result = describe_camera_config_load(
        config_available=True,
        config_handle="cfg",
        variation_id=7,
    )
    offsets = [row["destination"] for row in result["actions"][1:]]
    assert offsets == [
        "+0xd0", "+0xd4", "+0xd8", "+0xdc", "+0xe0",
        "+0xe4", "+0xe8", "+0xec", "+0xf0",
    ]


def test_slot_reset_clears_scratch_and_exact_raw_defaults():
    result = describe_camera_slot_reset(
        slot_base="slot0",
        camera_objects_present=True,
    )
    assert result["actions"][0]["size"] == 0x100
    assert result["raw_writes"]["+0x29f0"] == 3
    assert result["raw_writes"]["+0x2a14"] == 3
    assert result["raw_writes"]["+0x2a80"] == 0


def test_slot_reset_resets_both_camera_view_data_blocks():
    result = describe_camera_slot_reset(
        slot_base="slot0",
        camera_objects_present=True,
    )
    targets = [x["target"] for x in result["actions"] if x["action"] == "FUN_0081c8f0"]
    assert targets == ["slot0+0x20", "slot0+0xbe0"]
