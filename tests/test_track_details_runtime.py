import math

from track_details_runtime import (
    ALLOCATION_CONTINUATION,
    ALLOCATION_SIZE_STUB,
    CLASS_NAME,
    CONSTRUCTOR,
    DESTRUCTOR,
    DESTRUCTOR_BODY,
    DIRECT_DWORD_WRITES,
    HELPER_INITIALIZED_OFFSETS,
    LOADER,
    OBJECT_SIZE,
    PARENT_CLASS,
    REFLECTED_FIELDS,
    RTTI_DESCRIPTOR,
    RTTI_GETTER,
    VTABLE,
    describe_track_details_runtime,
    direct_constructor_writes,
    reflected_constructor_defaults,
    reflected_field_index,
)


def test_track_details_identity_and_exact_allocation_are_frozen():
    report = describe_track_details_runtime()

    assert CLASS_NAME == "TrackDetails"
    assert RTTI_DESCRIPTOR == 0x00BCCE48
    assert PARENT_CLASS == "BPersistent"
    assert VTABLE == 0x00ABB208
    assert RTTI_GETTER == 0x0049BCE0
    assert CONSTRUCTOR == "FUN_0049b9c0"
    assert DESTRUCTOR == "FUN_0049bf00"
    assert DESTRUCTOR_BODY == "FUN_0049bd10"
    assert LOADER == "FUN_0049c050"

    assert OBJECT_SIZE == 0x1D4
    assert ALLOCATION_SIZE_STUB == 0x00432446
    assert ALLOCATION_CONTINUATION == 0x0049EF4D
    assert report["allocation"]["object_size"] == 0x1D4


def test_all_44_direct_reflection_fields_are_preserved_once():
    assert len(REFLECTED_FIELDS) == 44
    fields = reflected_field_index()
    assert len(fields) == 44

    assert fields["ScenegraphFile"]["offset"] == 0x20
    assert fields["LeaderboardID"]["offset"] == 0x34
    assert fields["TrackName"]["offset"] == 0x40
    assert fields["Allowed Weather"]["offset"] == 0x110
    assert fields["Year"]["offset"] == 0x124
    assert fields["AI Grip"]["offset"] == 0x190
    assert fields["Post race position"]["offset"] == 0x1AC
    assert fields["Time Attack duration long"]["offset"] == 0x1D0

    assert max(int(row["offset"]) for row in REFLECTED_FIELDS) == OBJECT_SIZE - 4


def test_constructor_defaults_match_direct_fun_0049b9c0_writes():
    defaults = reflected_constructor_defaults()

    assert defaults["LeaderboardID"] == 0xFFFFFFFF
    assert defaults["Length"] == 0xFFFFFFFF
    assert defaults["Year"] == 0
    assert defaults["Sun Angle(DEG)"] == 0
    assert defaults["PreRace Allowed (true/false)"] == 0
    assert defaults["Max AI participants"] == 15

    assert math.isclose(defaults["AI Grip"], 1.0)
    assert defaults["AI drift score min"] == 400
    assert defaults["AI drift score max"] == 4000
    assert defaults["Rolling Start"] == 0

    assert defaults["Post race position"] == (0.0, 0.0, 0.0)
    assert defaults["Post race orientation"] == (0.0, 0.0, 0.0)
    assert math.isclose(defaults["Post race steering"], 0.0)

    assert defaults["Time Attack duration short"] == 5
    assert defaults["Time Attack duration medium"] == 10
    assert defaults["Time Attack duration long"] == 20


def test_constructor_contract_preserves_raw_internal_writes():
    writes = {row["offset"]: row for row in direct_constructor_writes()}

    assert len(DIRECT_DWORD_WRITES) == len(writes)
    assert writes[0x004] == {"offset": 0x004, "width": 4, "raw_value": 0}
    assert writes[0x008] == {"offset": 0x008, "width": 4, "raw_value": 1}
    assert writes[0x034]["raw_value"] == 0xFFFFFFFF
    assert writes[0x190]["raw_value"] == 0x3F800000
    assert writes[0x190]["float_value"] == 1.0
    assert writes[0x198]["raw_value"] == 400
    assert writes[0x19C]["raw_value"] == 4000
    assert writes[0x1D0]["raw_value"] == 20


def test_helper_initialized_offsets_remain_raw_evidence():
    generic = HELPER_INITIALIZED_OFFSETS["FUN_00533e70"]
    secondary = HELPER_INITIALIZED_OFFSETS["AptCharacterInst::GetAnimationInst"]

    assert 0x20 in generic
    assert 0x40 in generic
    assert 0x110 in generic
    assert 0x184 in generic
    assert 0x1A8 in generic

    assert secondary == (0x058, 0x07C, 0x0A4, 0x0C8, 0x0EC, 0x140)


def test_runtime_report_keeps_unproven_semantics_outside_contract():
    report = describe_track_details_runtime()

    assert report["direct_reflected_field_count"] == 44
    assert "not inferred" in report["evidence_boundary"]
    assert report["identity"]["loader"] == "FUN_0049c050"
    assert report["identity"]["destructor_body"] == "FUN_0049bd10"
