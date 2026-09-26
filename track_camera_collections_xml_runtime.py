"""Evidence-backed Splines/Areas XML serializers from TrackCameraMan.

Recovered from FUN_00812450 and FUN_00812550.

12450 serializes only entries in TrackCameraMan +0x48 whose object +0x24 equals
DAT_00c259f0. 12550 serializes every entry from +0x7c. Both use the same
0x50-byte funcpropdata helper object and each object's vtable +0x04 serializer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

FORMAT = "SHIFT.TrackCameraCollectionsXmlRuntime/1"


@dataclass(frozen=True)
class TrackCameraCollectionEntry:
    object_value: Any
    filter_value_24: int = 0
    name: str | None = None


def describe_collection_xml_setup(
    *,
    xml_collection: str,
    funcpropdata_bytes: int = 0x50,
) -> dict[str, Any]:
    """Reproduce the common XML setup used by 12450/12550."""
    if int(funcpropdata_bytes) != 0x50:
        raise ValueError("TrackCameraMan XML serializer allocates exactly 0x50 bytes")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "collection-xml-setup",
        "collection": xml_collection,
        "actions": [
            {
                "action": "FUN_0063e9b0",
                "path": "param_2 +0x84.elements",
            },
            {
                "action": "FUN_008868c0",
                "bytes": 0x50,
            },
            {
                "action": "FUN_0063e650",
                "condition": "allocation succeeded",
            },
            {
                "action": "FUN_0063c0d0",
                "purpose": "attach funcpropdata",
            },
        ],
        "evidence": {
            "serializer_12450": "FUN_00812450",
            "serializer_12550": "FUN_00812550",
        },
    }


def serialize_spline_collection(
    *,
    entries: Sequence[TrackCameraCollectionEntry],
    global_type: int,
    funcpropdata: Any = None,
) -> dict[str, Any]:
    """Reproduce FUN_00812450."""
    selected = [
        (index, entry)
        for index, entry in enumerate(entries)
        if int(entry.filter_value_24) == int(global_type)
    ]
    rows = [
        {
            "index": index,
            "filter_value_24": int(entry.filter_value_24),
            "object": entry.object_value,
            "actions": [
                {
                    "action": "entry.vtable +0x04",
                    "result": entry.object_value,
                },
                {
                    "action": "FUN_00640dd0",
                    "arguments": {
                        "entry": index,
                        "funcpropdata": funcpropdata,
                    },
                },
            ],
        }
        for index, entry in selected
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "splines-xml-save",
        "status": "ok",
        "source_list": "+0x48",
        "filter_offset": "+0x24",
        "global_type": int(global_type),
        "selected_count": len(rows),
        "serialized": rows,
        "evidence": {
            "function": "FUN_00812450",
            "xml_elements": "param_2 +0x84.elements",
            "serializer": "entry.vtable +0x04",
        },
    }


def serialize_area_collection(
    *,
    entries: Sequence[TrackCameraCollectionEntry],
    funcpropdata: Any = None,
) -> dict[str, Any]:
    """Reproduce FUN_00812550."""
    rows = [
        {
            "index": index,
            "object": entry.object_value,
            "actions": [
                {
                    "action": "entry.vtable +0x04",
                    "result": entry.object_value,
                },
                {
                    "action": "FUN_00640dd0",
                    "arguments": {
                        "entry": index,
                        "funcpropdata": funcpropdata,
                    },
                },
            ],
        }
        for index, entry in enumerate(entries)
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "areas-xml-save",
        "status": "ok",
        "source_list": "+0x7c",
        "filter": None,
        "serialized": rows,
        "serialized_count": len(rows),
        "evidence": {
            "function": "FUN_00812550",
            "xml_elements": "param_2 +0x84.elements",
            "serializer": "entry.vtable +0x04",
        },
    }


def describe_track_camera_man_xml_registrations() -> dict[str, Any]:
    """Reproduce FUN_00812650's TrackCameraMan child registration map."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "track-camera-man-xml-registration",
        "children": [
            {
                "name": "Trackside Cams",
                "storage_offset": 0x48,
                "load_callback": "FUN_00816d30",
                "save_callback": "FUN_00812260",
            },
            {
                "name": "Splines",
                "storage_offset": 0x48,
                "load_callback": "FUN_008117c0",
                "save_callback": "FUN_00812450",
            },
            {
                "name": "Areas",
                "storage_offset": 0x7C,
                "load_callback": "FUN_00811d40",
                "save_callback": "FUN_00812550",
            },
        ],
        "container_factory": "FUN_00408320(type=0xbfa72c)",
        "property_registration": "FUN_006420b0",
        "evidence": {"function": "FUN_00812650"},
    }
