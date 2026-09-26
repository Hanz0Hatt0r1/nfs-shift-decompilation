from camera_collection_runtime import (
    deserialize_camera_collection,
    force_collection_reset,
    next_camera_index,
    next_index_for_slot,
    previous_camera_index,
    reset_collection_condition,
    update_collection_marker,
    update_secondary_collection_marker,
)


def test_previous_index_wraps_from_zero_to_last_slot():
    assert previous_camera_index(value=0, current_slot_count=5)["result"] == 4
    assert previous_camera_index(value=3, current_slot_count=5)["result"] == 2


def test_next_index_wraps_last_to_zero():
    assert next_camera_index(value=4, current_slot_count=5)["result"] == 0
    assert next_camera_index(value=2, current_slot_count=5)["result"] == 3


def test_selector_next_index_uses_selected_slot_count():
    result = next_index_for_slot(
        value=2,
        slot_selector=1,
        slot_counts={1: 3},
    )
    assert result["result"] == 0


def test_marker_sets_two_entry_bytes_when_flag_zero():
    result = update_collection_marker(
        collection_present=True,
        index=1,
        marker_flag=0,
        local_lookup_succeeded=True,
    )
    assert result["writes"] == {"entry.byte_0d": 1, "entry.byte_0e": 1}


def test_secondary_marker_increments_counter_when_flag_nonzero():
    result = update_secondary_collection_marker(
        collection_present=True,
        index=1,
        marker_flag=1,
    )
    assert result["writes"]["+0x374"] == "old + 1"


def test_reset_condition_accepts_zero_and_maxint_modes_only():
    assert reset_collection_condition(
        mode=0,
        collection_present=True,
    )["status"] == "reset"
    assert reset_collection_condition(
        mode=0x7FFFFFFF,
        collection_present=True,
    )["status"] == "reset"
    assert reset_collection_condition(
        mode=4,
        collection_present=True,
    )["status"] == "not-triggered"


def test_force_reset_sets_mode_four_and_clears_marker():
    result = force_collection_reset()
    assert result["writes"]["+0x244"] == 4
    assert result["writes"]["+0x266"] == 1


def test_collection_xml_deserializer_tracks_static_camera_inheritance():
    result = deserialize_camera_collection(
        elements=[{"class": "StaticCamera", "secondary": "a"}],
        factory_results=["camera"],
        application_results=[True],
        inheritance_results=[[STATIC_CAMERA_TYPE]] if False else [["DAT_00c25e70"]],
    )
    assert result["status"] == "loaded"
    assert result["entries"][0]["is_static_camera_derived"] is True


def test_collection_xml_deserializer_stops_on_factory_failure():
    result = deserialize_camera_collection(
        elements=[{"class": "A", "secondary": "a"}],
        factory_results=[None],
        application_results=[False],
        inheritance_results=[[]],
    )
    assert result["status"] == "factory-failed"
