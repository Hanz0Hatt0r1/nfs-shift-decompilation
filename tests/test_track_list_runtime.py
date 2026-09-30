from track_list_runtime import (
    ALLOCATOR,
    CLASS_NAME,
    CONSTRUCTOR,
    DEFAULT_FILTER_TEXT,
    DEFAULT_TRACKLIST_PATH,
    DESTRUCTOR,
    DESTRUCTOR_BODY,
    FILTER_SPLIT,
    OBJECT_SIZE,
    PARENT_CLASS,
    RECURSIVE_TRACK_SCAN,
    REFLECTED_FILTERS,
    RTTI_DESCRIPTOR,
    RTTI_GETTER,
    SINGLETON_GLOBAL,
    SINGLETON_INITIALIZER,
    TRACKLIST_TEXT_LOAD,
    TRACK_DETAILS_COLLECTION_OFFSET,
    VTABLE,
    build_filter_tokens,
    describe_track_list_runtime,
    normalize_filter_text,
    reflected_filter_index,
)


def test_track_list_identity_singleton_and_exact_size_are_frozen():
    report = describe_track_list_runtime()

    assert CLASS_NAME == "TrackList"
    assert RTTI_DESCRIPTOR == 0x00BCD48C
    assert PARENT_CLASS == "BPersistent"
    assert VTABLE == 0x00ABB4D0
    assert RTTI_GETTER == 0x0049EEA0
    assert CONSTRUCTOR == "FUN_00d6aee0"
    assert DESTRUCTOR == "FUN_0049ef10"
    assert DESTRUCTOR_BODY == "FUN_0049edb0"

    assert SINGLETON_GLOBAL == "DAT_00bcd484"
    assert SINGLETON_INITIALIZER == "FUN_0049f940"
    assert ALLOCATOR == "FUN_008868c0"
    assert OBJECT_SIZE == 0xE4
    assert report["singleton"]["object_size"] == 0xE4


def test_four_reflected_filter_strings_reach_end_of_allocation():
    assert len(REFLECTED_FILTERS) == 4
    fields = reflected_filter_index()

    assert fields["Era Names"]["source_offset"] == 0xD4
    assert fields["Track Types"]["source_offset"] == 0xD8
    assert fields["Track Locations"]["source_offset"] == 0xDC
    assert fields["Track Groups"]["source_offset"] == 0xE0
    assert max(row["source_offset"] for row in REFLECTED_FILTERS) == OBJECT_SIZE - 4

    assert all(row["type_code"] == 0 for row in REFLECTED_FILTERS)
    assert all(row["flags"] == 3 for row in REFLECTED_FILTERS)


def test_filter_strings_map_to_exact_internal_token_destinations():
    fields = reflected_filter_index()

    assert fields["Era Names"]["destination_offset"] == 0x88
    assert fields["Track Types"]["destination_offset"] == 0x40
    assert fields["Track Locations"]["destination_offset"] == 0x64
    assert fields["Track Groups"]["destination_offset"] == 0xB0


def test_empty_filters_default_to_all_then_use_recovered_comma_split():
    assert DEFAULT_FILTER_TEXT == "All"
    assert normalize_filter_text("") == "All"
    assert normalize_filter_text("Road") == "Road"

    assert build_filter_tokens("") == ["All"]
    assert build_filter_tokens("Road,Circuit") == ["Road", "Circuit"]
    assert build_filter_tokens("Road,,Circuit") == ["Road", "Circuit"]
    assert build_filter_tokens("Road,") == ["Road", ""]


def test_constructor_prefers_tracklist_file_then_falls_back_to_recursive_scan():
    report = describe_track_list_runtime()
    startup = report["startup_load"]

    assert DEFAULT_TRACKLIST_PATH == "tracks/_Data/tracklist.lst"
    assert TRACKLIST_TEXT_LOAD == "FUN_0049f2c0"
    assert RECURSIVE_TRACK_SCAN == "FUN_0049f010"

    assert startup["preferred_path"] == DEFAULT_TRACKLIST_PATH
    assert startup["preferred_loader"] == TRACKLIST_TEXT_LOAD
    assert startup["fallback_when_loader_returns_zero"] == {
        "function": RECURSIVE_TRACK_SCAN,
        "root": "Tracks",
        "extension": ".trd",
    }


def test_track_details_collection_is_owned_and_destroyed_by_track_list():
    report = describe_track_list_runtime()
    owned = report["owned_track_details"]

    assert TRACK_DETAILS_COLLECTION_OFFSET == 0x10
    assert owned["collection_offset"] == 0x10
    assert "virtual destructor" in owned["destructor_behavior"]


def test_runtime_boundary_keeps_unresolved_tracklist_policy_out():
    report = describe_track_list_runtime()

    assert report["filter_derivation"]["split_function"] == FILTER_SPLIT
    assert "not inferred" in report["evidence_boundary"]
    assert "text track-list line syntax" in report["evidence_boundary"]
