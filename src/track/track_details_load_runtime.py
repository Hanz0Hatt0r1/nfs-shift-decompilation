"""Source-backed TrackDetails load/tokenization contract.

This module captures only the post-property-load behavior explicit in
FUN_0049c050 plus the allocation/ownership wrapper and recursive .trd discovery.
It deliberately keeps internal collection container types opaque.
"""
from __future__ import annotations

from typing import Any, Mapping

from shift_hash_runtime import shift_hash32
from track_details_runtime import LOADER, reflected_field_index

FORMAT = "SHIFT.TrackDetailsLoadRuntime/1"

ALLOCATION_LOAD_WRAPPER = "FUN_0049ef4d"
DIRECTORY_SCAN = "FUN_0049f010"
TRACKLIST_TEXT_LOAD = "FUN_0049f2c0"
TOKEN_APPEND = "FUN_0049bf70"
OWNER_INSERT = "FUN_004f5e60"
SOURCE_HASH = "FUN_0063ad50"
LOWERCASE = "FUN_00631a10"
CHAR_REPLACE = "FUN_00631410"
PATH_DIRECTORY_EXTRACTOR = "FUN_00636090"
PATH_SET_DIRECTORY = "FUN_006361f0"
PATH_SET_FILENAME = "FUN_006362e0"
PATH_STEM_EXTRACTOR = "FUN_006360f0"
PATH_NORMALIZER = "FUN_00635f20"

PROPERTY_LOAD_VTABLE_OFFSET = 0x20
DATA_READY_VTABLE_OFFSET = 0x24
OWNER_COLLECTION_OFFSET = 0x10
SOURCE_PATH_HASH_OFFSET = 0x120
YEAR_BUCKET_COLLECTION_OFFSET = 0x58
SCENEGRAPH_STEM_OFFSET = 0x10
SCENEGRAPH_FILE_OFFSET = 0x20
SCENEGRAPH_PATH_OFFSET = 0x24
TRACK_EXTENSION = ".trd"

TOKEN_COLLECTIONS = {
    "Track Type": {
        "source_offset": 0x0A0,
        "destination_offset": 0x07C,
    },
    "Allowed TimeOfDay": {
        "source_offset": 0x114,
        "destination_offset": 0x0C8,
    },
    "Event Types": {
        "source_offset": 0x118,
        "destination_offset": 0x0EC,
    },
    "Class": {
        "source_offset": 0x13C,
        "destination_offset": 0x140,
    },
    "Allowed Weather": {
        "source_offset": 0x110,
        "destination_offset": 0x0A4,
    },
}

YEAR_FIELD = "Year"
YEAR_OFFSET = 0x124


def split_track_tokens(value: str) -> list[str]:
    """Mirror FUN_0049c050's comma splitting.

    Empty prefixes around commas are discarded, while the final remainder is
    always appended. This preserves the source distinction for a trailing comma,
    which produces an empty final entry.
    """
    remaining = value
    out: list[str] = []
    while len(remaining) >= 2:
        comma = remaining.find(",")
        if comma < 0:
            break
        prefix = remaining[:comma]
        if prefix:
            out.append(prefix)
        remaining = remaining[comma + 1 :]
    out.append(remaining)
    return out


def classify_track_year(year: int) -> str:
    """Return the exact year bucket selected by FUN_0049c050."""
    if year == 0:
        return "UNSET"
    if year < 0x76D:
        return "50BC"
    if year < 0x7B2:
        return "1930-1969"
    if year < 2000:
        return "1970-1999"
    if year < 0x7E4:
        return "2000-2019"
    if year < 0x835:
        return "2020-2100"
    return "ERROR"


def normalize_track_source_path(path: str) -> str:
    """Mirror the explicit lower-case and slash replacement before hashing."""
    return path.lower().replace("/", "\\")


def _normalize_ascii_runtime_path(path: str) -> str:
    """Normalize only the ASCII path domain established by retail evidence."""
    value = str(path)
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("retail path normalization is only proven for ASCII") from exc
    return value.lower().replace("/", "\\")


def derive_scenegraph_path(source_path: str, scenegraph_file: str) -> str:
    """Reproduce FUN_0049c050's path-object construction at TrackDetails +0x24.

    The loader extracts the directory of the source .trd path, assigns that
    directory to the internal path object, replaces its filename with the
    reflected ScenegraphFile value, and normalizes the resulting path.
    """
    source = _normalize_ascii_runtime_path(source_path)
    scenegraph = _normalize_ascii_runtime_path(scenegraph_file)
    slash = source.rfind("\\")
    directory = source[: slash + 1] if slash >= 0 else ""
    return directory + scenegraph


def derive_scenegraph_stem(source_path: str, scenegraph_file: str) -> str:
    """Return the lower-case basename-without-extension stored at +0x10."""
    path = derive_scenegraph_path(source_path, scenegraph_file)
    slash = path.rfind("\\")
    basename = path[slash + 1 :] if slash >= 0 else path
    if not basename or basename.startswith("."):
        return ""
    dot = basename.rfind(".")
    return basename[:dot] if dot > 0 else basename


def is_track_details_filename(name: str) -> bool:
    """Mirror FUN_0049f010's case-insensitive final-four-byte .trd test."""
    return len(name) > 3 and name[-4:].lower() == TRACK_EXTENSION


def derive_post_load_values(
    properties: Mapping[str, Any],
    source_path: str,
) -> dict[str, Any]:
    """Produce only the source-backed post-load derived values.

    Missing properties are represented by an empty source string for token
    parsing; this helper is not a replacement for the retail property loader.
    Numeric source-path hash parity is available for ASCII source paths, which
    matches the recovered retail TrackDetails corpus path convention.
    """
    token_collections = {
        name: split_track_tokens(str(properties.get(name, "")))
        for name in TOKEN_COLLECTIONS
    }
    year = int(properties.get(YEAR_FIELD, 0))
    normalized_path = normalize_track_source_path(source_path)
    path_bytes = normalized_path.encode("ascii")
    scenegraph_file = str(properties.get("ScenegraphFile", ""))
    scenegraph_path = derive_scenegraph_path(source_path, scenegraph_file)
    scenegraph_stem = derive_scenegraph_stem(source_path, scenegraph_file)
    return {
        "token_collections": token_collections,
        "year_bucket": classify_track_year(year),
        "scenegraph_path": scenegraph_path,
        "scenegraph_stem": scenegraph_stem,
        "normalized_source_path": normalized_path,
        "source_path_hash": {
            "function": SOURCE_HASH,
            "destination_offset": SOURCE_PATH_HASH_OFFSET,
            "byte_length": len(path_bytes),
            "seed": 0,
            "case_sensitive_flag": 1,
            "numeric_hash": shift_hash32(path_bytes, 0),
        },
    }


def describe_track_details_load_runtime() -> dict[str, Any]:
    fields = reflected_field_index()
    assert int(fields["ScenegraphFile"]["offset"]) == SCENEGRAPH_FILE_OFFSET
    token_rows = []
    for field_name, contract in TOKEN_COLLECTIONS.items():
        source_offset = int(contract["source_offset"])
        assert int(fields[field_name]["offset"]) == source_offset
        token_rows.append({
            "field_name": field_name,
            "source_offset": source_offset,
            "destination_offset": int(contract["destination_offset"]),
            "separator": ",",
            "append_function": TOKEN_APPEND,
        })

    return {
        "format": FORMAT,
        "version": 1,
        "loader": {
            "function": LOADER,
            "property_load_vtable_offset": PROPERTY_LOAD_VTABLE_OFFSET,
            "data_ready_vtable_offset": DATA_READY_VTABLE_OFFSET,
            "property_failure_text": "Failed to load the properties for: ",
            "data_failure_text": "Failed to load the data for: ",
        },
        "post_load": {
            "token_collections": token_rows,
            "year": {
                "source_field": YEAR_FIELD,
                "source_offset": YEAR_OFFSET,
                "destination_offset": YEAR_BUCKET_COLLECTION_OFFSET,
                "append_function": TOKEN_APPEND,
                "buckets": [
                    {"condition": "year == 0", "value": "UNSET"},
                    {"condition": "year < 1901", "value": "50BC"},
                    {"condition": "year < 1970", "value": "1930-1969"},
                    {"condition": "year < 2000", "value": "1970-1999"},
                    {"condition": "year < 2020", "value": "2000-2019"},
                    {"condition": "year < 2101", "value": "2020-2100"},
                    {"condition": "otherwise", "value": "ERROR"},
                ],
            },
            "source_path": {
                "lowercase_function": LOWERCASE,
                "replace_function": CHAR_REPLACE,
                "replace_from": "/",
                "replace_to": "\\",
                "hash_function": SOURCE_HASH,
                "hash_destination_offset": SOURCE_PATH_HASH_OFFSET,
                "hash_seed": 0,
                "hash_case_sensitive_flag": 1,
            },
            "scenegraph_identity": {
                "scenegraph_file_field": "ScenegraphFile",
                "scenegraph_file_offset": SCENEGRAPH_FILE_OFFSET,
                "path_object_offset": SCENEGRAPH_PATH_OFFSET,
                "stem_offset": SCENEGRAPH_STEM_OFFSET,
                "directory_extractor": PATH_DIRECTORY_EXTRACTOR,
                "set_directory_function": PATH_SET_DIRECTORY,
                "set_filename_function": PATH_SET_FILENAME,
                "path_normalizer": PATH_NORMALIZER,
                "stem_extractor": PATH_STEM_EXTRACTOR,
                "normalization": "ASCII lower-case, slash to backslash",
                "value": "basename(ScenegraphFile) without final extension",
            },
        },
        "allocation_and_ownership": {
            "function": ALLOCATION_LOAD_WRAPPER,
            "success_insert_function": OWNER_INSERT,
            "owner_collection_offset": OWNER_COLLECTION_OFFSET,
            "failure_action": "invoke object virtual destructor",
            "failure_log_prefix": "Tracklist: Failed to load: ",
        },
        "directory_discovery": {
            "function": DIRECTORY_SCAN,
            "api": ["FindFirstFileA", "FindNextFileA"],
            "recursive": True,
            "skip_names": [".", ".."],
            "extension": TRACK_EXTENSION,
            "extension_case_sensitive": False,
            "load_function": ALLOCATION_LOAD_WRAPPER,
        },
        "tracklist_text_load_function": TRACKLIST_TEXT_LOAD,
        "evidence_boundary": (
            "Comma tokenization, year bucketing, ASCII source-path normalization "
            "and numeric hash parity, ScenegraphFile-derived path/stem identity, "
            "recursive .trd discovery, and success/failure ownership handoff are "
            "recovered. Internal collection types, non-ASCII CRT path behavior, "
            "property-parser internals and higher-level event-selection policy "
            "are not inferred."
        ),
    }
