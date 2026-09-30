"""Source-backed TrackList singleton/runtime contract."""
from __future__ import annotations

from typing import Any

from track_details_load_runtime import split_track_tokens

FORMAT = "SHIFT.TrackListRuntime/1"

CLASS_NAME = "TrackList"
RTTI_DESCRIPTOR = 0x00BCD48C
PARENT_CLASS = "BPersistent"
PARENT_DESCRIPTOR = 0x00BFA608
REFLECTION_METADATA = "DAT_00b81ee4"
REFLECTION_BUILDER = "FUN_00d6a940"
REFLECTION_BUILDER_THUNK = "thunk_FUN_00d6a940"

VTABLE = 0x00ABB4D0
RTTI_GETTER = 0x0049EEA0
CONSTRUCTOR = "FUN_00d6aee0"
CONSTRUCTOR_THUNK = "thunk_FUN_00d6aee0"
DESTRUCTOR = "FUN_0049ef10"
DESTRUCTOR_BODY = "FUN_0049edb0"

SINGLETON_GLOBAL = "DAT_00bcd484"
SINGLETON_INITIALIZER = "FUN_0049f940"
ALLOCATOR = "FUN_008868c0"
OBJECT_SIZE = 0x0E4

TRACK_DETAILS_COLLECTION_OFFSET = 0x10
AUXILIARY_INDEX_OFFSET = 0x30

DEFAULT_TRACKLIST_PATH = "tracks/_Data/tracklist.lst"
TRACKLIST_TEXT_LOAD = "FUN_0049f2c0"
RECURSIVE_TRACK_SCAN = "FUN_0049f010"
FILTER_SPLIT = "thunk_FUN_00d6ad30"
DEFAULT_FILTER_TEXT = "All"

REFLECTED_FILTERS = (
    {
        "name": "Era Names",
        "source_offset": 0x0D4,
        "destination_offset": 0x088,
        "type_code": 0,
        "flags": 3,
    },
    {
        "name": "Track Types",
        "source_offset": 0x0D8,
        "destination_offset": 0x040,
        "type_code": 0,
        "flags": 3,
    },
    {
        "name": "Track Locations",
        "source_offset": 0x0DC,
        "destination_offset": 0x064,
        "type_code": 0,
        "flags": 3,
    },
    {
        "name": "Track Groups",
        "source_offset": 0x0E0,
        "destination_offset": 0x0B0,
        "type_code": 0,
        "flags": 3,
    },
)


def normalize_filter_text(value: str) -> str:
    """Mirror the constructor's empty-string fallback before token splitting."""
    return value if value else DEFAULT_FILTER_TEXT


def build_filter_tokens(value: str) -> list[str]:
    return split_track_tokens(normalize_filter_text(value))


def reflected_filter_index() -> dict[str, dict[str, Any]]:
    return {str(row["name"]): dict(row) for row in REFLECTED_FILTERS}


def describe_track_list_runtime() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "class_name": CLASS_NAME,
        "identity": {
            "rtti_descriptor": RTTI_DESCRIPTOR,
            "parent_class": PARENT_CLASS,
            "parent_descriptor": PARENT_DESCRIPTOR,
            "reflection_metadata": REFLECTION_METADATA,
            "reflection_builder": REFLECTION_BUILDER,
            "reflection_builder_thunk": REFLECTION_BUILDER_THUNK,
            "vtable": VTABLE,
            "rtti_getter": RTTI_GETTER,
            "constructor": CONSTRUCTOR,
            "constructor_thunk": CONSTRUCTOR_THUNK,
            "destructor": DESTRUCTOR,
            "destructor_body": DESTRUCTOR_BODY,
        },
        "singleton": {
            "global": SINGLETON_GLOBAL,
            "initializer": SINGLETON_INITIALIZER,
            "allocator": ALLOCATOR,
            "object_size": OBJECT_SIZE,
        },
        "owned_track_details": {
            "collection_offset": TRACK_DETAILS_COLLECTION_OFFSET,
            "destructor_behavior": (
                "iterate collection and invoke each non-null object's virtual "
                "destructor before destroying the collection"
            ),
        },
        "auxiliary_index_offset": AUXILIARY_INDEX_OFFSET,
        "direct_reflected_field_count": len(REFLECTED_FILTERS),
        "reflected_filters": [dict(row) for row in REFLECTED_FILTERS],
        "startup_load": {
            "preferred_path": DEFAULT_TRACKLIST_PATH,
            "preferred_loader": TRACKLIST_TEXT_LOAD,
            "fallback_when_loader_returns_zero": {
                "function": RECURSIVE_TRACK_SCAN,
                "root": "Tracks",
                "extension": ".trd",
            },
        },
        "filter_derivation": {
            "empty_source_default": DEFAULT_FILTER_TEXT,
            "delimiter": ",",
            "split_function": FILTER_SPLIT,
            "collections": [
                {
                    "field_name": row["name"],
                    "source_offset": row["source_offset"],
                    "destination_offset": row["destination_offset"],
                }
                for row in REFLECTED_FILTERS
            ],
        },
        "evidence_boundary": (
            "Singleton identity, exact 0xe4 allocation, four reflected filter "
            "strings, filter token destinations, TrackDetails ownership teardown, "
            "tracklist.lst preference and recursive .trd fallback are recovered. "
            "Auxiliary index internals, text track-list line syntax and higher-level "
            "selection/sorting policy are not inferred."
        ),
    }
