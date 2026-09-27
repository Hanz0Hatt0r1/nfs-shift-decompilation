import pytest

from vehicle_cdf_runtime import parse_cdf, section_entries, source_schema, SECTION_HANDLERS


def test_cdf_parser_preserves_sections_and_raw_values():
    report = parse_cdf("""
        ; comment
        [GENERAL]
        Mass = 1397.25
        Inertia = (1.0, 2.0, 3.0)
        DamageFile = physics/damage.cdp
        [FRONTLEFT]
        SpringRange = (100.0, 20.0, 5)
        BumpTravel = 0.08
    """)
    assert report["ready"] is True
    assert report["section_count"] == 2
    assert report["entry_count"] == 5
    assert report["recognized_entry_count"] == 5
    general = section_entries(report, "general")
    assert general[0]["value"] == 1397.25
    assert general[1]["value"] == [1.0, 2.0, 3.0]
    assert general[2]["value"] == "physics/damage.cdp"
    wheel = section_entries(report, "FRONTLEFT")
    assert wheel[0]["schema"]["offset_hex"] == ["0x1c8", "0x1d0", "0x1d8"]
    assert wheel[0]["schema"]["helper"] == "FUN_007a75a0"


def test_source_schema_freezes_dispatch_and_offsets():
    assert SECTION_HANDLERS["GENERAL"] == "FUN_007be420"
    assert SECTION_HANDLERS["FRONTLEFT"] == "FUN_007bc770(index=0)"
    assert SECTION_HANDLERS["REARRIGHT"] == "FUN_007bc770(index=3)"
    general = source_schema("GENERAL")
    assert general["properties"]["Mass"]["offsets"] == [0x1C]
    assert general["properties"]["Inertia"]["offsets"] == [0x30, 0x44, 0x58]
    controls = source_schema("CONTROLS")
    assert controls["properties"]["ThrottleControl"]["offsets"] == [0x188, 0x18C, 0x190, 0x194]
    driveline = source_schema("DRIVELINE")
    assert driveline["properties"]["Gear8Setting"]["offsets"] == [0x244]


def test_unknown_and_malformed_lines_are_retained_not_dropped():
    report = parse_cdf("""
        [UNKNOWN_SECTION]
        Foo = 1,2,3
        malformed line
        [GENERAL]
        UnknownProperty = keep me
    """)
    assert report["section_count"] == 2
    assert report["unknown_entry_count"] == 2
    assert any(item.startswith("line:") for item in report["warnings"])
    unknown = section_entries(report, "UNKNOWN_SECTION")[0]
    assert unknown["value"] == [1, 2, 3]
    assert unknown["schema"] is None
    assert section_entries(report, "GENERAL")[0]["recognized"] is False


def test_strict_mode_rejects_non_assignment_lines():
    with pytest.raises(ValueError, match="unparsed"):
        parse_cdf("[GENERAL]\nnot-an-assignment\n", strict=True)


def test_engine_speed_limiter_is_a_source_backed_bool_field():
    row = section_entries(parse_cdf("[ENGINE]\nSpeedLimiter = true\n"), "ENGINE")[0]
    assert row["value"] is True
    assert row["schema"]["helper"] == "FUN_007a6470"
    assert row["schema"]["offsets"] == [0x28F0]
