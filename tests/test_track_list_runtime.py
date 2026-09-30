import pytest

from track_list_runtime import (
    DIRECTORY_FALLBACK_ROOT,
    FILTER_CONTAINER_OFFSETS,
    REFLECTED_FIELDS,
    RTTI_DESCRIPTOR,
    RTTI_GETTER,
    SINGLETON_POINTER_GLOBAL,
    SIZE,
    TRACKLIST_PATH,
    TRACK_DETAILS_SIZE,
    VTABLE,
    build_filter_indices,
    describe_track_list_runtime,
    is_track_details_filename,
    lookup_key_matches,
    parse_tracklist_requests,
    reflected_field_index,
    split_source_csv,
    track_details_class_matches,
    year_era_bucket,
)


def test_track_list_identity_singleton_and_exact_size():
    report = describe_track_list_runtime()
    assert RTTI_DESCRIPTOR == 0x00BCD48C
    assert RTTI_GETTER == 0x0049EEA0
    assert VTABLE == 0x00ABB4D0
    assert SIZE == 0xE4
    assert SINGLETON_POINTER_GLOBAL == 0x00BCD484
    assert report["singleton"]["exact_size"] == 0xE4
    assert report["identity"]["destructor"] == "FUN_0049ef10"


def test_four_reflected_taxonomy_strings_and_filter_containers():
    assert len(REFLECTED_FIELDS) == 4
    fields = reflected_field_index()
    assert fields["Era Names"]["offset"] == 0xD4
    assert fields["Track Types"]["offset"] == 0xD8
    assert fields["Track Locations"]["offset"] == 0xDC
    assert fields["Track Groups"]["offset"] == 0xE0
    assert all(row["type_code"] == 0 for row in REFLECTED_FIELDS)
    assert all(row["flags"] == 3 for row in REFLECTED_FIELDS)
    assert FILTER_CONTAINER_OFFSETS == {
        "Track Types": 0x40,
        "Track Locations": 0x64,
        "Era Names": 0x88,
        "Track Groups": 0xB0,
    }


def test_constructor_filter_defaults_and_source_csv_splitter():
    assert split_source_csv("A,B,C") == ["A", "B", "C"]
    assert split_source_csv(",B") == ["B"]
    assert split_source_csv("A,") == ["A", ""]
    assert split_source_csv("") == [""]

    indices = build_filter_indices(
        {
            "Era Names": "",
            "Track Types": "Circuit,Drift",
            "Track Locations": None,
            "Track Groups": "Europe",
        }
    )
    assert indices == {
        "Era Names": ["All"],
        "Track Types": ["Circuit", "Drift"],
        "Track Locations": ["All"],
        "Track Groups": ["Europe"],
    }


@pytest.mark.parametrize(
    ("year", "expected"),
    [
        (0, "UNSET"),
        (-50, "50BC"),
        (1900, "50BC"),
        (1901, "1930-1969"),
        (1969, "1930-1969"),
        (1970, "1970-1999"),
        (1999, "1970-1999"),
        (2000, "2000-2019"),
        (2019, "2000-2019"),
        (2020, "2020-2100"),
        (2100, "2020-2100"),
        (2101, "ERROR"),
    ],
)
def test_track_details_year_era_bucket(year, expected):
    assert year_era_bucket(year) == expected


def test_track_details_class_filter_matches_all_include_and_exclude():
    tokens = ["Road", "Modern", "GT"]
    assert track_details_class_matches("All", tokens, "anything") is True
    assert track_details_class_matches("GT", tokens, "All") is True
    assert track_details_class_matches("GT", tokens, "gt") is True
    assert track_details_class_matches("GT", tokens, "road") is True
    assert track_details_class_matches("GT", tokens, "Oval") is False
    assert track_details_class_matches("GT", tokens, "!Oval") is True
    assert track_details_class_matches("GT", tokens, "!Road") is False


def test_case_insensitive_structural_lookup_key_contract():
    assert lookup_key_matches("Silverstone", "silverSTONE") is True
    assert lookup_key_matches("Silverstone", "Brands Hatch") is False
    assert lookup_key_matches("Silverstone", "") is False
    assert lookup_key_matches(None, "Silverstone") is False


def test_tracklist_lst_crlf_parser_and_at_concatenation():
    text = (
        "Tracks\\Silverstone\\silverstone.trd\r\n"
        "Tracks\\BrandsHatch\\@brands.trd\r\n"
        "\r\n"
        "Tracks\\Spa\\SPA.TRD\r\n"
    )
    assert parse_tracklist_requests(text) == [
        "Tracks\\Silverstone\\silverstone.trd",
        "Tracks\\BrandsHatch\\brands.trd",
        "Tracks\\Spa\\SPA.TRD",
    ]


def test_tracklist_lst_parser_fails_closed_for_non_retail_line_endings():
    with pytest.raises(ValueError, match="CRLF"):
        parse_tracklist_requests("Tracks\\Silverstone\\silverstone.trd\n")
    with pytest.raises(ValueError, match="newline terminated"):
        parse_tracklist_requests("Tracks\\Silverstone\\silverstone.trd\r")


def test_directory_fallback_extension_check_is_case_insensitive():
    assert is_track_details_filename("silverstone.trd") is True
    assert is_track_details_filename("SPA.TRD") is True
    assert is_track_details_filename("foo.trd.bak") is False
    assert is_track_details_filename(".trd") is True
    assert is_track_details_filename("trd") is False


def test_load_and_ownership_contract_links_track_list_to_track_details():
    report = describe_track_list_runtime()
    assert report["load"]["tracklist_path"] == TRACKLIST_PATH
    assert report["load"]["directory_fallback_root"] == DIRECTORY_FALLBACK_ROOT
    assert report["load"]["track_details_size"] == TRACK_DETAILS_SIZE == 0x1D4
    assert report["load"]["track_details_property_loader"] == "FUN_0049c050"
    assert report["load"]["track_details_insert"] == "FUN_004f5e60"
    assert report["layout"]["primary_track_container_offset"] == 0x10
    assert "owns loaded TrackDetails pointers" in report["ownership"]


def test_evidence_boundary_keeps_container_abi_and_lookup_key_semantics_unassigned():
    report = describe_track_list_runtime()
    assert report["direct_reflected_field_count"] == 4
    assert report["lookups"]["track_details_lookup_key_offset"] == 0x10
    assert "internal tree/container node ABI" in report["evidence_boundary"]
    assert "higher-level meaning" in report["evidence_boundary"]
