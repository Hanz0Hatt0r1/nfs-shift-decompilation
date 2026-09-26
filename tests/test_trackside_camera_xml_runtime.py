from trackside_camera_xml_runtime import (
    TracksideEntry,
    count_non_type1,
    describe_trackside_xml_setup,
    serialize_trackside_entries,
)


def test_count_non_type1_matches_source_scan():
    entries = [
        TracksideEntry(type_discriminator=0, is_tracking_camera=False),
        TracksideEntry(type_discriminator=1, is_tracking_camera=False),
        TracksideEntry(type_discriminator=2, is_tracking_camera=False),
    ]
    assert count_non_type1(entries) == 2


def test_type1_tracking_camera_temporarily_rebases_spline_id_by_count():
    entries = [
        TracksideEntry(type_discriminator=0, is_tracking_camera=False),
        TracksideEntry(type_discriminator=1, is_tracking_camera=True, spline_id=7),
        TracksideEntry(type_discriminator=1, is_tracking_camera=True, spline_id=-1),
    ]
    result = serialize_trackside_entries(
        entries=entries,
        global_type=1,
        shared_type_object="funcpropdata",
    )
    row = result["serialized"][0]
    assert row["temporary_subtraction"] == 5
    assert row["serialized_spline_id"] == 2
    assert row["restored_spline_id"] == 7


def test_type_non1_tracking_camera_invalidates_spline_when_cutoff_reached():
    entries = [
        TracksideEntry(type_discriminator=0, is_tracking_camera=True, spline_id=4),
        TracksideEntry(type_discriminator=0, is_tracking_camera=False),
        TracksideEntry(type_discriminator=1, is_tracking_camera=False),
    ]
    result = serialize_trackside_entries(
        entries=entries,
        global_type=0,
    )
    row = result["serialized"][0]
    assert row["invalidated"] is True
    assert row["serialized_spline_id"] == -1


def test_non_tracking_entries_are_serialized_without_spline_mutation():
    entries = [
        TracksideEntry(type_discriminator=1, is_tracking_camera=False, spline_id=4),
    ]
    result = serialize_trackside_entries(entries=entries, global_type=1)
    row = result["serialized"][0]
    assert row["serialized_spline_id"] == 4
    assert row["temporary_subtraction"] is None


def test_unmatched_type_is_skipped():
    entries = [
        TracksideEntry(type_discriminator=2, is_tracking_camera=False),
    ]
    result = serialize_trackside_entries(entries=entries, global_type=1)
    assert result["serialized"] == []


def test_setup_exposes_exact_funcpropdata_allocation():
    result = describe_trackside_xml_setup(
        existing_entries=[],
        root_available=True,
    )
    assert result["actions"][3]["bytes"] == 0x50
    assert result["actions"][5]["purpose"] == "attach funcpropdata"
