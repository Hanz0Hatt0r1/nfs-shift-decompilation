import specialized_provider_scalar_selector_provenance_runtime as runtime


def test_selector_groups_match_source_callsites():
    contract = runtime.build_selector_provenance_contract()

    assert [group["group"] for group in contract["groups"]] == [
        "JOINT/HINGE",
        "SECONDARY",
        "BAR",
    ]
    assert [group["width"] for group in contract["groups"]] == [3, 2, 1]
    assert [group["source_line"] for group in contract["groups"]] == [
        814124,
        814138,
        814150,
    ]


def test_selector_source_paths_are_exact():
    groups = {
        item["group"]: item
        for item in runtime.build_selector_provenance_contract()["groups"]
    }

    assert groups["JOINT/HINGE"]["source_field_path"] == ("+0x7c", "+0x30")
    assert groups["SECONDARY"]["source_field_path"] == ("+0x7c", "+0x94")
    assert groups["BAR"]["source_field_path"] == ("+0x7c", "+0x30")


def test_selector_calls_match_declared_width():
    for group in runtime.GROUPS:
        assert len(group["selector_calls"]) == group["width"]


def test_preconditions_keep_bounds_check_boundary_explicit():
    contract = runtime.build_selector_provenance_contract()

    assert "no bounds check" in contract["preconditions"]["selector_domain"]
    assert contract["preconditions"]["enabled_constraint"] == (
        "record+0x70 bit 0 must be set before selector is used"
    )


def test_validate_selector_provenance_contract():
    result = runtime.validate_selector_provenance_contract()

    assert result["ready"] is True
    assert result["errors"] == []
