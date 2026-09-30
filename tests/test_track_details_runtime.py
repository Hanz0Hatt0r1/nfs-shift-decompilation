import struct

import pytest

from track_details_runtime import (
    ALLOCATION_COLD_STUB,
    CLASS_NAME,
    CONSTRUCTOR_STRING_ASSIGNMENTS,
    DESTRUCTOR,
    REFLECTED_CONSTRUCTOR_DEFAULTS,
    REFLECTED_FIELDS,
    RTTI_DESCRIPTOR,
    RTTI_GETTER,
    SIZE,
    STRING_INITIALIZED_FIELDS,
    VTABLE,
    decode_numeric_fields,
    describe_track_details_runtime,
    reflected_field_index,
)


def test_track_details_identity_and_exact_allocation_size():
    report = describe_track_details_runtime()
    assert CLASS_NAME == "TrackDetails"
    assert RTTI_DESCRIPTOR == 0x00BCCE48
    assert RTTI_GETTER == 0x0049BCE0
    assert VTABLE == 0x00ABB208
    assert DESTRUCTOR == "FUN_0049bf00"
    assert ALLOCATION_COLD_STUB == 0x00432446
    assert SIZE == 0x1D4
    assert report["allocation"]["exact_size"] == 0x1D4
    assert "pushes 0x1d4" in report["allocation"]["proof"]


def test_all_forty_four_direct_reflected_fields_are_preserved():
    assert len(REFLECTED_FIELDS) == 44
    fields = reflected_field_index()
    assert len(fields) == 44
    assert fields["ScenegraphFile"]["offset"] == 0x20
    assert fields["LeaderboardID"]["offset"] == 0x34
    assert fields["TrackName"]["offset"] == 0x40
    assert fields["Track Type"]["offset"] == 0xA0
    assert fields["Allowed Weather"]["offset"] == 0x110
    assert fields["Year"]["offset"] == 0x124
    assert fields["Track Surface"]["offset"] == 0x12C
    assert fields["Max AI participants"]["offset"] == 0x138
    assert fields["Class"]["offset"] == 0x13C
    assert fields["AI Grip"]["offset"] == 0x190
    assert fields["Post race position"]["offset"] == 0x1AC
    assert fields["Time Attack duration long"]["offset"] == 0x1D0
    assert all(row["flags"] == 3 for row in REFLECTED_FIELDS)


def test_reflected_offsets_fit_exact_object_size():
    for row in REFLECTED_FIELDS:
        assert 0 <= row["offset"] < SIZE
    assert max(row["offset"] for row in REFLECTED_FIELDS) == 0x1D0


def test_constructor_defaults_only_claim_direct_writes():
    defaults = REFLECTED_CONSTRUCTOR_DEFAULTS
    assert defaults["LeaderboardID"] == -1
    assert defaults["Length"] == -1
    assert defaults["Year"] == 0
    assert defaults["Sun Angle(DEG)"] == 0.0
    assert defaults["PreRace Allowed (true/false)"] == 0
    assert defaults["Max AI participants"] == 15
    assert defaults["AI Grip"] == 1.0
    assert defaults["AI drift score min"] == 400
    assert defaults["AI drift score max"] == 4000
    assert defaults["Rolling Start"] == 0
    assert defaults["Post race position"] == (0.0, 0.0, 0.0)
    assert defaults["Post race orientation"] == (0.0, 0.0, 0.0)
    assert defaults["Post race steering"] == 0.0
    assert defaults["Time Attack duration short"] == 5
    assert defaults["Time Attack duration medium"] == 10
    assert defaults["Time Attack duration long"] == 20
    assert "XLASTID" not in defaults


def test_constructor_string_initialization_is_kept_separate_from_scalar_defaults():
    assert len(STRING_INITIALIZED_FIELDS) == 27
    assert "ScenegraphFile" in STRING_INITIALIZED_FIELDS
    assert "TrackName" in STRING_INITIALIZED_FIELDS
    assert "Class" in STRING_INITIALIZED_FIELDS
    assert "ZoneName" in STRING_INITIALIZED_FIELDS
    assert "AI Grip" not in STRING_INITIALIZED_FIELDS
    assert CONSTRUCTOR_STRING_ASSIGNMENTS == {"Class": "All"}


def test_numeric_decoder_uses_source_backed_offsets():
    blob = bytearray(SIZE)
    struct.pack_into("<i", blob, 0x34, -7)
    struct.pack_into("<i", blob, 0x38, 12345)
    struct.pack_into("<i", blob, 0x3C, 99)
    struct.pack_into("<i", blob, 0x124, 2009)
    struct.pack_into("<f", blob, 0x128, 42.5)
    struct.pack_into("<I", blob, 0x134, 1)
    struct.pack_into("<i", blob, 0x138, 15)
    struct.pack_into("<f", blob, 0x190, 0.875)
    struct.pack_into("<i", blob, 0x198, 400)
    struct.pack_into("<i", blob, 0x19C, 4000)
    struct.pack_into("<I", blob, 0x1A0, 1)
    struct.pack_into("<fff", blob, 0x1AC, 1.0, 2.0, 3.0)
    struct.pack_into("<fff", blob, 0x1B8, 4.0, 5.0, 6.0)
    struct.pack_into("<f", blob, 0x1C4, -0.25)
    struct.pack_into("<iii", blob, 0x1C8, 5, 10, 20)

    row = decode_numeric_fields(blob)
    assert row["leaderboard_id"] == -7
    assert row["length_raw"] == 12345
    assert row["xlastid"] == 99
    assert row["year"] == 2009
    assert row["sun_angle_deg"] == pytest.approx(42.5)
    assert row["pre_race_allowed_raw"] == 1
    assert row["max_ai_participants"] == 15
    assert row["ai_grip"] == pytest.approx(0.875)
    assert row["ai_drift_score_min"] == 400
    assert row["ai_drift_score_max"] == 4000
    assert row["rolling_start_raw"] == 1
    assert row["post_race_position"] == pytest.approx((1.0, 2.0, 3.0))
    assert row["post_race_orientation"] == pytest.approx((4.0, 5.0, 6.0))
    assert row["post_race_steering"] == pytest.approx(-0.25)
    assert row["time_attack_duration_short"] == 5
    assert row["time_attack_duration_medium"] == 10
    assert row["time_attack_duration_long"] == 20


def test_numeric_decoder_rejects_short_record():
    with pytest.raises(ValueError, match="0x1d4"):
        decode_numeric_fields(bytes(SIZE - 1))


def test_evidence_boundary_does_not_claim_dynamic_string_layout_or_gameplay_semantics():
    report = describe_track_details_runtime()
    assert report["direct_reflected_field_count"] == 44
    assert report["identity"]["reflection_builder"] == "FUN_00d67c70"
    assert report["identity"]["reflection_builder_aliases"] == [
        "FUN_00d67c70",
        "thunk_FUN_00d67c70",
    ]
    assert "Dynamic string storage" in report["evidence_boundary"]
    assert "gameplay interpretation" in report["evidence_boundary"]
