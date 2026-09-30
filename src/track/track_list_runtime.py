"""Source-backed TrackList singleton, loader, filter and lookup contract."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from track_details_load_runtime import (
    TOKEN_COLLECTIONS,
    YEAR_BUCKET_COLLECTION_OFFSET,
    classify_track_year,
    is_track_details_filename as _is_track_details_filename,
    split_track_tokens,
)
from track_details_runtime import (
    OBJECT_SIZE as TRACK_DETAILS_SIZE,
    reflected_field_index as _track_details_fields,
)

FORMAT = "SHIFT.TrackListRuntime/1"

CLASS_NAME = "TrackList"
PARENT_CLASS = "BPersistent"
PARENT_DESCRIPTOR = 0x00BFA608
RTTI_DESCRIPTOR = 0x00BCD48C
RTTI_GETTER = 0x0049EEA0
VTABLE = 0x00ABB4D0
REGISTRATION_FUNCTION = "FUN_00a78200"
REFLECTION_METADATA = "DAT_00b81ee4"
REFLECTION_BUILDER = "FUN_00d6a940"
REFLECTION_BUILDER_ALIASES = ("FUN_00d6a940", "thunk_FUN_00d6a940")
CONSTRUCTOR = "FUN_00d6aee0"
CONSTRUCTOR_ALIASES = ("FUN_00d6aee0", "thunk_FUN_00d6aee0")
DESTRUCTOR = "FUN_0049ef10"
DESTRUCTOR_BODY = "FUN_0049edb0"

SIZE = 0xE4
SINGLETON_POINTER_GLOBAL = 0x00BCD484
SINGLETON_INITIALIZER = "FUN_0049f940"
ALLOCATOR = "FUN_008868c0"

PRIMARY_TRACK_CONTAINER_OFFSET = 0x10
LOADER_CONTEXT_OFFSET = 0x30

REFLECTED_FIELDS = (
    {"name": "Era Names", "offset": 0xD4, "type_code": 0x0, "flags": 3},
    {"name": "Track Types", "offset": 0xD8, "type_code": 0x0, "flags": 3},
    {"name": "Track Locations", "offset": 0xDC, "type_code": 0x0, "flags": 3},
    {"name": "Track Groups", "offset": 0xE0, "type_code": 0x0, "flags": 3},
)

FILTER_CONTAINER_OFFSETS = {
    "Track Types": 0x40,
    "Track Locations": 0x64,
    "Era Names": 0x88,
    "Track Groups": 0xB0,
}
FILTER_DEFAULT = "All"
FILTER_SPLITTER = "thunk_FUN_00d6ad30"
FILTER_INSERT = "FUN_0049bf70"

TRACKLIST_PATH = "tracks/_Data/tracklist.lst"
TRACKLIST_LOADER = "FUN_0049f2c0"
DIRECTORY_FALLBACK = "FUN_0049f010"
DIRECTORY_FALLBACK_ROOT = "Tracks"
TRACK_DETAILS_EXTENSION = ".trd"
TRACK_DETAILS_OBJECT_LOADER = "FUN_0049ef40"
TRACK_DETAILS_PROPERTY_LOADER = "FUN_0049c050"
TRACK_DETAILS_INSERT = "FUN_004f5e60"
LOOKUP_BY_KEY = "FUN_0049ed00"
LOOKUP_FIRST = "thunk_FUN_00480cb0"
LOOKUP_BY_CLASS_FILTER = "thunk_FUN_00d6abc0"

TRACK_DETAILS_DERIVED_TOKEN_CONTAINERS = {
    "era": YEAR_BUCKET_COLLECTION_OFFSET,
    "track_type": int(TOKEN_COLLECTIONS["Track Type"]["destination_offset"]),
    "weather": int(TOKEN_COLLECTIONS["Allowed Weather"]["destination_offset"]),
    "time_of_day": int(TOKEN_COLLECTIONS["Allowed TimeOfDay"]["destination_offset"]),
    "event_type": int(TOKEN_COLLECTIONS["Event Types"]["destination_offset"]),
    "class": int(TOKEN_COLLECTIONS["Class"]["destination_offset"]),
}
TRACK_DETAILS_LOOKUP_KEY_OFFSET = 0x10
TRACK_DETAILS_CLASS_FIELD_OFFSET = int(_track_details_fields()["Class"]["offset"])


def reflected_field_index() -> dict[str, dict[str, Any]]:
    """Return a detached name-indexed copy of the four direct reflected fields."""
    return {str(row["name"]): dict(row) for row in REFLECTED_FIELDS}


def split_source_csv(value: str) -> list[str]:
    """Reuse the source-backed TrackDetails comma splitter."""
    return split_track_tokens(str(value))


def build_filter_indices(values: Mapping[str, str | None]) -> dict[str, list[str]]:
    """Apply constructor fallback-to-All and build the four filter token lists."""
    out: dict[str, list[str]] = {}
    for field in ("Era Names", "Track Types", "Track Locations", "Track Groups"):
        value = values.get(field)
        normalized = value if value else FILTER_DEFAULT
        out[field] = split_source_csv(normalized)
    return out


def year_era_bucket(year: int) -> str:
    """Reuse FUN_0049c050's already-recovered year bucket."""
    return classify_track_year(int(year))


def track_details_class_matches(
    declared_class: str | None,
    class_tokens: Iterable[str],
    query: str,
) -> bool:
    """Reproduce thunk_FUN_00d696c0 All/include/!exclude class filtering."""
    needle = str(query)
    if (declared_class or "").casefold() == "all" or needle.casefold() == "all":
        return True
    tokens = {str(token).casefold() for token in class_tokens}
    if needle.startswith("!"):
        return needle[1:].casefold() not in tokens
    return needle.casefold() in tokens


def lookup_key_matches(stored_key: str | None, query: str | None) -> bool:
    """Case-insensitive key comparison used by FUN_0049ed00."""
    if not query:
        return False
    return (stored_key or "").casefold() == str(query).casefold()


def parse_tracklist_requests(text: str) -> list[str]:
    """Recover load requests from the retail CRLF tracklist.lst grammar.

    FUN_0049f2c0 consumes newline-terminated records and removes the byte
    immediately before LF. On the retail list contract that byte is CR. An
    optional @ splits a record into two pieces that are concatenated before
    FUN_0049ef40 is called. LF-only records are rejected rather than silently
    dropping their final filename character.
    """
    if not isinstance(text, str):
        raise TypeError("tracklist text must be str")
    if text and not text.endswith("\n"):
        raise ValueError("retail tracklist records must be newline terminated")

    out: list[str] = []
    for raw in text.splitlines(keepends=True):
        if not raw.endswith("\n"):
            raise ValueError("retail tracklist records must be newline terminated")
        before_lf = raw[:-1]
        if len(before_lf) < 2:
            continue
        if not before_lf.endswith("\r"):
            raise ValueError("retail tracklist parser expects CRLF records")
        line = before_lf[:-1]
        at = line.find("@")
        out.append(line if at < 0 else line[:at] + line[at + 1 :])
    return out


def is_track_details_filename(name: str) -> bool:
    """Reuse the recovered recursive .trd admission predicate."""
    return _is_track_details_filename(str(name))


def describe_track_list_runtime() -> dict[str, Any]:
    """Return the source/PE-backed TrackList structural/load contract."""
    return {
        "format": FORMAT,
        "version": 1,
        "class_name": CLASS_NAME,
        "parent": {"class_name": PARENT_CLASS, "descriptor": PARENT_DESCRIPTOR},
        "identity": {
            "rtti_descriptor": RTTI_DESCRIPTOR,
            "rtti_getter": RTTI_GETTER,
            "vtable": VTABLE,
            "registration_function": REGISTRATION_FUNCTION,
            "reflection_metadata": REFLECTION_METADATA,
            "reflection_builder": REFLECTION_BUILDER,
            "reflection_builder_aliases": list(REFLECTION_BUILDER_ALIASES),
            "constructor": CONSTRUCTOR,
            "constructor_aliases": list(CONSTRUCTOR_ALIASES),
            "destructor": DESTRUCTOR,
            "destructor_body": DESTRUCTOR_BODY,
        },
        "singleton": {
            "pointer_global": SINGLETON_POINTER_GLOBAL,
            "initializer": SINGLETON_INITIALIZER,
            "allocator": ALLOCATOR,
            "exact_size": SIZE,
        },
        "size": SIZE,
        "layout": {
            "primary_track_container_offset": PRIMARY_TRACK_CONTAINER_OFFSET,
            "loader_context_offset": LOADER_CONTEXT_OFFSET,
            "filter_container_offsets": dict(FILTER_CONTAINER_OFFSETS),
        },
        "direct_reflected_field_count": len(REFLECTED_FIELDS),
        "direct_reflected_fields": [dict(row) for row in REFLECTED_FIELDS],
        "load": {
            "tracklist_path": TRACKLIST_PATH,
            "list_loader": TRACKLIST_LOADER,
            "directory_fallback": DIRECTORY_FALLBACK,
            "directory_fallback_root": DIRECTORY_FALLBACK_ROOT,
            "track_details_extension": TRACK_DETAILS_EXTENSION,
            "track_details_object_loader": TRACK_DETAILS_OBJECT_LOADER,
            "track_details_property_loader": TRACK_DETAILS_PROPERTY_LOADER,
            "track_details_insert": TRACK_DETAILS_INSERT,
            "track_details_size": TRACK_DETAILS_SIZE,
        },
        "filters": {
            "default": FILTER_DEFAULT,
            "splitter": FILTER_SPLITTER,
            "insert": FILTER_INSERT,
            "track_details_derived_token_containers": dict(
                TRACK_DETAILS_DERIVED_TOKEN_CONTAINERS
            ),
            "track_details_class_field_offset": TRACK_DETAILS_CLASS_FIELD_OFFSET,
        },
        "lookups": {
            "by_key": LOOKUP_BY_KEY,
            "first": LOOKUP_FIRST,
            "by_class_filter": LOOKUP_BY_CLASS_FILTER,
            "track_details_lookup_key_offset": TRACK_DETAILS_LOOKUP_KEY_OFFSET,
        },
        "ownership": (
            "The +0x10 container owns loaded TrackDetails pointers: successful "
            "FUN_0049c050 loads are inserted there, failed loads destroy the "
            "new object, and FUN_0049edb0 destroys every surviving element."
        ),
        "evidence_boundary": (
            "Exact TrackList identity/size, reflected taxonomy strings, "
            "TrackDetails ownership, list/directory load control flow and "
            "case-insensitive/class-filter lookups are recovered. The internal "
            "tree/container node ABI and the higher-level meaning of the "
            "TrackDetails +0x10 lookup key remain structural."
        ),
    }
