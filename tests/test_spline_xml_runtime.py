from spline_xml_runtime import (
    describe_spline_runtime_size,
    describe_spline_xml_load,
    describe_spline_xml_property_registration,
    describe_spline_xml_save,
)


def test_spline_property_registration_matches_exact_fields():
    result = describe_spline_xml_property_registration()
    props = {p.get("name", p.get("name_symbol")): p for p in result["properties"]}
    assert props["NumNodes"]["offset"] == 0x10
    assert props["Length"]["offset"] == 0x18
    assert props["nodes"]["offset"] == 0x14
    assert result["callbacks"]["load"] == "FUN_00821e80"
    assert result["callbacks"]["save"] == "FUN_00822770"


def test_spline_xml_load_allocates_exact_funcpropdata_size():
    result = describe_spline_xml_load(
        node_count=4,
        existing_record_count=2,
        root_present=True,
    )
    assert result["actions"][1]["bytes"] == 0x50
    assert result["actions"][2]["action"] == "FUN_0063c0d0"
    assert result["evidence"]["record_stride"] == 0x24


def test_spline_xml_load_handles_missing_root_without_record_walk():
    result = describe_spline_xml_load(
        node_count=4,
        existing_record_count=2,
        root_present=False,
    )
    assert result["status"] == "root-unavailable"
    assert not any(a["action"] == "iterate existing records" for a in result["actions"])


def test_spline_xml_save_tracks_class_and_secondary_attributes():
    result = describe_spline_xml_save(
        node_count=2,
        records=[{}, {}],
        class_names=["A", "B"],
        secondary_attributes=["id0", "id1"],
    )
    reads = [a for a in result["actions"] if a["action"] == "read record attributes"]
    assert reads[0]["class"] == "A"
    assert reads[0]["secondary"] == "id0"
    assert reads[1]["record_offset"] == 0x24


def test_spline_xml_save_aborts_on_failed_record_application():
    result = describe_spline_xml_save(
        node_count=1,
        records=[{}],
        class_names=["A"],
        secondary_attributes=["id"],
        all_record_application_succeeds=False,
    )
    assert result["status"] == "failed"
    assert result["actions"][-1]["action"] == "abort"


def test_spline_runtime_size_is_four_bytes_plus_record_array():
    result = describe_spline_runtime_size(node_count=5)
    assert result["bytes"] == 4 + 5 * 0x24
