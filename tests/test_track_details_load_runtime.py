from track_details_load_runtime import (
    ALLOCATION_LOAD_WRAPPER,
    DATA_READY_VTABLE_OFFSET,
    DIRECTORY_SCAN,
    OWNER_COLLECTION_OFFSET,
    PROPERTY_LOAD_VTABLE_OFFSET,
    SOURCE_PATH_HASH_OFFSET,
    TOKEN_COLLECTIONS,
    TRACK_EXTENSION,
    YEAR_BUCKET_COLLECTION_OFFSET,
    classify_track_year,
    derive_post_load_values,
    describe_track_details_load_runtime,
    is_track_details_filename,
    normalize_track_source_path,
    split_track_tokens,
)


def test_comma_tokenization_matches_loader_edge_cases():
    assert split_track_tokens("A,B,C") == ["A", "B", "C"]
    assert split_track_tokens("A,,B") == ["A", "B"]
    assert split_track_tokens(",B") == ["B"]
    assert split_track_tokens("A,") == ["A", ""]
    assert split_track_tokens("A") == ["A"]
    assert split_track_tokens("") == [""]


def test_year_buckets_match_exact_source_boundaries():
    assert classify_track_year(0) == "UNSET"
    assert classify_track_year(1) == "50BC"
    assert classify_track_year(1900) == "50BC"
    assert classify_track_year(1901) == "1930-1969"
    assert classify_track_year(1969) == "1930-1969"
    assert classify_track_year(1970) == "1970-1999"
    assert classify_track_year(1999) == "1970-1999"
    assert classify_track_year(2000) == "2000-2019"
    assert classify_track_year(2019) == "2000-2019"
    assert classify_track_year(2020) == "2020-2100"
    assert classify_track_year(2100) == "2020-2100"
    assert classify_track_year(2101) == "ERROR"


def test_source_path_normalization_and_trd_filter_are_source_equivalent():
    assert normalize_track_source_path("Tracks/Silverstone/ERA3.TRD") == (
        "tracks\\silverstone\\era3.trd"
    )
    assert is_track_details_filename("silverstone.trd")
    assert is_track_details_filename("SILVERSTONE.TRD")
    assert not is_track_details_filename("silverstone.trd.bak")
    assert not is_track_details_filename("trd")


def test_post_load_derivatives_keep_hash_as_explicit_source_call():
    report = derive_post_load_values(
        {
            "Track Type": "Circuit,Race",
            "Allowed TimeOfDay": "Day,Night",
            "Event Types": "Race,,TimeAttack",
            "Class": "A,",
            "Allowed Weather": "Dry",
            "Year": 2020,
        },
        "Tracks/Silverstone/ERA3.TRD",
    )

    assert report["token_collections"]["Track Type"] == ["Circuit", "Race"]
    assert report["token_collections"]["Allowed TimeOfDay"] == ["Day", "Night"]
    assert report["token_collections"]["Event Types"] == ["Race", "TimeAttack"]
    assert report["token_collections"]["Class"] == ["A", ""]
    assert report["token_collections"]["Allowed Weather"] == ["Dry"]
    assert report["year_bucket"] == "2020-2100"
    assert report["normalized_source_path"] == "tracks\\silverstone\\era3.trd"

    hash_contract = report["source_path_hash"]
    assert hash_contract["function"] == "FUN_0063ad50"
    assert hash_contract["destination_offset"] == 0x120
    assert hash_contract["seed"] == 0
    assert hash_contract["case_sensitive_flag"] == 1
    assert hash_contract["numeric_hash"] == 0x0A1A5C1E


def test_loader_contract_freezes_reflected_to_internal_token_joins():
    report = describe_track_details_load_runtime()
    post = report["post_load"]

    assert PROPERTY_LOAD_VTABLE_OFFSET == 0x20
    assert DATA_READY_VTABLE_OFFSET == 0x24
    assert SOURCE_PATH_HASH_OFFSET == 0x120
    assert YEAR_BUCKET_COLLECTION_OFFSET == 0x58

    rows = {
        row["field_name"]: row
        for row in post["token_collections"]
    }
    assert rows["Track Type"]["source_offset"] == 0xA0
    assert rows["Track Type"]["destination_offset"] == 0x7C
    assert rows["Allowed Weather"]["source_offset"] == 0x110
    assert rows["Allowed Weather"]["destination_offset"] == 0xA4
    assert rows["Allowed TimeOfDay"]["source_offset"] == 0x114
    assert rows["Allowed TimeOfDay"]["destination_offset"] == 0xC8
    assert rows["Event Types"]["source_offset"] == 0x118
    assert rows["Event Types"]["destination_offset"] == 0xEC
    assert rows["Class"]["source_offset"] == 0x13C
    assert rows["Class"]["destination_offset"] == 0x140
    assert len(rows) == len(TOKEN_COLLECTIONS) == 5


def test_allocation_handoff_and_recursive_discovery_are_preserved():
    report = describe_track_details_load_runtime()
    handoff = report["allocation_and_ownership"]
    discovery = report["directory_discovery"]

    assert ALLOCATION_LOAD_WRAPPER == "FUN_0049ef4d"
    assert OWNER_COLLECTION_OFFSET == 0x10
    assert handoff["success_insert_function"] == "FUN_004f5e60"
    assert handoff["failure_action"] == "invoke object virtual destructor"
    assert "Tracklist:" in handoff["failure_log_prefix"]

    assert DIRECTORY_SCAN == "FUN_0049f010"
    assert discovery["recursive"] is True
    assert discovery["skip_names"] == [".", ".."]
    assert discovery["extension"] == TRACK_EXTENSION == ".trd"
    assert discovery["extension_case_sensitive"] is False
    assert discovery["load_function"] == ALLOCATION_LOAD_WRAPPER


def test_loader_boundary_keeps_unproven_types_and_policy_out():
    report = describe_track_details_load_runtime()
    boundary = report["evidence_boundary"]

    assert "not inferred" in boundary
    assert report["tracklist_text_load_function"] == "FUN_0049f2c0"
