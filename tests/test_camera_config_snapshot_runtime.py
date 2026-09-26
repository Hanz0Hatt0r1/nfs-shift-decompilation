from camera_config_snapshot_runtime import (
    ConfigSnapshot,
    camera_config_snapshot_defaults,
    describe_string_property_parse,
    parse_semicolon_vec3,
    refresh_cached_config,
    update_config_snapshot,
)


def test_semicolon_parser_reads_up_to_three_values():
    assert parse_semicolon_vec3("1;2;3") == (1.0, 2.0, 3.0)
    assert parse_semicolon_vec3("4;5") == (4.0, 5.0, 0.0)


def test_string_parser_uses_length_15_gate_and_vec_callback():
    result = describe_string_property_parse(
        target="vec_a",
        text_value="0;0;0;123456",
        helper_811390_result=12,
    )
    assert result["helper_811390_result"] == 12
    assert result["callback"] == "FUN_00823560"
    result = describe_string_property_parse(
        target="vec_a",
        text_value="anything",
        helper_811390_result=15,
    )
    assert result["helper_811390_result"] == 15
    assert result["callback"] == "FUN_00823590"


def test_snapshot_update_sets_second_vector_only_for_nonempty_second_string():
    snapshot = update_config_snapshot(
        ConfigSnapshot(),
        first_text="1;2;3",
        second_text="4;5;6",
        parameter=7,
    )
    assert snapshot.vec_a == (1.0, 2.0, 3.0)
    assert snapshot.vec_b == (4.0, 5.0, 6.0)
    assert snapshot.has_vec_b is True


def test_snapshot_update_clears_second_vector_flag_for_empty_second_string():
    snapshot = update_config_snapshot(
        ConfigSnapshot(vec_b=(9, 9, 9), has_vec_b=True),
        first_text="1;2;3",
        second_text="",
        parameter=8,
    )
    assert snapshot.vec_a == (1.0, 2.0, 3.0)
    assert snapshot.has_vec_b is False
    assert snapshot.parameter == 8


def test_config_defaults_preserve_projection_and_misc_raw_bits():
    result = camera_config_snapshot_defaults()
    assert result["writes"]["+0x10"] == 0x43B40000
    assert result["writes"]["+0x54"] == 0x3F99999A
    assert result["writes"]["+0x5c"] == 0x42B40000
    assert result["writes"]["+0x60"] == 0x3FAAAAAB
    assert result["writes"]["+0x68"] == 0x43FA0000
    assert result["writes"]["+0xfc"] == 0xFFFFFFFF


def test_cached_config_only_refreshes_when_selector_changes():
    snapshot = ConfigSnapshot()
    hit = refresh_cached_config(
        current_selector=4,
        requested_selector=4,
        snapshot=snapshot,
        first_text="0;0;0",
        second_text=None,
        parameter=4,
    )
    assert hit["status"] == "cache-hit"
    miss = refresh_cached_config(
        current_selector=4,
        requested_selector=5,
        snapshot=snapshot,
        first_text="1;2;3",
        second_text=None,
        parameter=5,
    )
    assert miss["status"] == "refreshed"
    assert miss["snapshot"].parameter == 5
    assert miss["snapshot"].source_selector == 5
