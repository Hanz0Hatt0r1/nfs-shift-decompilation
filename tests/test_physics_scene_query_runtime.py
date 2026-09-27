import struct
import pytest

from collision_stream_runtime import (
    build_collision_stream_contract,
    parse_collision_record,
)
from physics_scene_query_runtime import (
    FLT_MAX,
    build_scene_query_contract,
    query_mode_contract,
    validate_query_inputs,
)


def test_csm_record_type_lt_two_has_seven_words_and_three_buffers():
    data = struct.pack("<IIIIIII", 0, 11, 22, 33, 44, 55, 66)
    r = parse_collision_record(data)
    assert r["consumed_bytes"] == 28
    assert r["raw_fields_u32"] == [11, 22, 33, 44, 55, 66]
    assert [x["count"] for x in r["allocated_buffers"]] == [44, 55, 66]


def test_csm_discriminator_ge_two_stops_after_one_word():
    r = parse_collision_record(struct.pack("<I", 2))
    assert r["consumed_bytes"] == 4
    assert r["allocated_buffers"] == []


def test_csm_truncation_can_be_blocked_non_strictly():
    r = parse_collision_record(b"\0" * 8, strict=False)
    assert r["status"] == "blocked"
    assert r["blockers"] == ["collision-record:truncated"]


def test_csm_contract_freezes_expected_version_and_modes():
    c = build_collision_stream_contract()
    assert c["version_check"]["expected"] == 0xAFB
    assert c["load_modes"]["required"]["argument"] == 1
    assert c["load_modes"]["optional"]["argument"] == 0


def test_query_modes_match_observed_dispatch():
    assert query_mode_contract(0)["scene_query_type"] == 1
    assert query_mode_contract(1)["scene_query_type"] == 2
    assert query_mode_contract(2)["mask_u32"] == 0x80000000
    assert build_scene_query_contract()["modes"][3]["scene_query_type"] == 3


def test_query_input_validation_is_fail_closed():
    assert validate_query_inputs(True, 0, 30.0)["ready"] is True
    assert validate_query_inputs(False, 0, 30.0)["ready"] is False
    assert validate_query_inputs(True, 99, 30.0)["ready"] is False
    assert validate_query_inputs(True, 0, -1.0)["failure_result"] == FLT_MAX


def test_query_rejects_nan():
    assert validate_query_inputs(True, 0, float("nan"))["ready"] is False


def test_query_mode_unknown_raises():
    with pytest.raises(ValueError):
        query_mode_contract(4)
