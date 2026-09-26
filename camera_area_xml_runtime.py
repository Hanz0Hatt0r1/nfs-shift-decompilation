"""Camera area XML factory/reset/release runtime from FUN_00818710/18760/18940."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.CameraAreaXmlRuntime/1"

AREA_FACTORIES = {
    "DAT_00c25f88": {
        "bytes": 0x20,
        "constructor": "FUN_0081e750",
        "role": "sphere-area",
    },
    "DAT_00c25f98": {
        "bytes": 0x60,
        "constructor": "FUN_0081ea20",
        "role": "box-area",
    },
}
AREA_INHERITANCE_MARKER = "DAT_00c25f78"


def reset_camera_area_mode(*, collection_present: bool) -> dict[str, Any]:
    """Reproduce FUN_00818710."""
    actions: list[dict[str, Any]] = []
    if collection_present:
        actions.extend([
            {"action": "write +0x240", "value": 0},
            {"action": "write +0x244", "value": 0x7FFFFFFF},
            {"action": "FUN_00816570"},
            {"action": "write output-valid", "target": "+0x328", "value": 0},
            {"action": "write +0x265", "value": 1},
            {"action": "write +0x266", "value": 1},
        ])
    actions.append({
        "action": "FUN_00818250",
        "argument": 0,
    })
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "reset-camera-area-mode",
        "status": "processed",
        "actions": actions,
        "evidence": {
            "function": "FUN_00818710",
            "inactive_mode": 0x7FFFFFFF,
        },
    }


def instantiate_camera_area_from_class(
    *,
    class_symbol: str,
    allocation_succeeded: bool,
    constructor_succeeded: bool,
) -> dict[str, Any]:
    """Reproduce FUN_00818760's exact two-class factory dispatch."""
    entry = AREA_FACTORIES.get(str(class_symbol))
    if entry is None:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "instantiate-camera-area",
            "status": "unsupported-class",
            "class_symbol": str(class_symbol),
            "object": None,
            "evidence": {"function": "FUN_00818760"},
        }
    if not allocation_succeeded:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "instantiate-camera-area",
            "status": "allocation-failed",
            "class_symbol": str(class_symbol),
            "allocation_bytes": entry["bytes"],
        }
    if not constructor_succeeded:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "constructor-failed",
            "class_symbol": str(class_symbol),
            "constructor": entry["constructor"],
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "instantiate-camera-area",
        "status": "constructed",
        "class_symbol": str(class_symbol),
        "allocation_bytes": entry["bytes"],
        "constructor": entry["constructor"],
        "role": entry["role"],
        "object": {"class_symbol": str(class_symbol)},
    }


def deserialize_camera_areas(
    *,
    elements: Sequence[Mapping[str, Any]],
    factory_success: Sequence[bool],
    property_application_success: Sequence[bool],
    resolved_classes: Sequence[str],
    inheritance_lists: Sequence[Sequence[str]],
) -> dict[str, Any]:
    """Trace FUN_00818760's per-element XML path and area-list registration."""
    n = len(elements)
    if not (len(factory_success) == len(property_application_success) == len(resolved_classes) == len(inheritance_lists) == n):
        raise ValueError("camera-area result arrays must have equal length")

    entries: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []

    for index, element in enumerate(elements):
        class_name = str(element.get("class", ""))
        secondary_name = str(element.get("secondary", ""))
        actions.append({
            "action": "read XML attributes",
            "index": index,
            "class": class_name,
            "secondary": secondary_name,
        })

        factory = instantiate_camera_area_from_class(
            class_symbol=resolved_classes[index],
            allocation_succeeded=factory_success[index],
            constructor_succeeded=factory_success[index],
        )
        actions.append({
            "action": "factory",
            "index": index,
            "result": factory,
        })
        if factory["status"] != "constructed":
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "deserialize-camera-areas",
                "status": "factory-failed",
                "entries": entries,
                "actions": actions,
            }

        if not property_application_success[index]:
            actions.append({
                "action": "FUN_006408f0",
                "index": index,
                "result": False,
            })
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "deserialize-camera-areas",
                "status": "property-application-failed",
                "entries": entries,
                "actions": actions,
            }

        inherited_area = AREA_INHERITANCE_MARKER in set(inheritance_lists[index])
        actions.append({
            "action": "FUN_004cb900",
            "destination": "+0x7c",
            "index": index,
            "value": 1 if inherited_area else 0,
            "inheritance_marker": AREA_INHERITANCE_MARKER,
        })
        entries.append({
            "class": class_name,
            "secondary": secondary_name,
            "resolved_class": resolved_classes[index],
            "is_area_derived": inherited_area,
        })

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "deserialize-camera-areas",
        "status": "loaded",
        "entries": entries,
        "actions": actions,
        "evidence": {
            "function": "FUN_00818760",
            "area_sphere_class": "DAT_00c25f88",
            "area_box_class": "DAT_00c25f98",
            "area_base_marker": AREA_INHERITANCE_MARKER,
        },
    }


def release_camera_area_lists(*, list_counts: Mapping[str, int]) -> dict[str, Any]:
    """Reproduce FUN_00818940's three independent release walks."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "release-camera-area-lists",
        "actions": [
            {
                "action": "release list",
                "offset": "+0x14",
                "count": int(list_counts.get("+0x14", 0)),
            },
            {
                "action": "release list",
                "offset": "+0x48",
                "count": int(list_counts.get("+0x48", 0)),
            },
            {
                "action": "release list",
                "offset": "+0x7c",
                "count": int(list_counts.get("+0x7c", 0)),
            },
        ],
        "evidence": {
            "function": "FUN_00818940",
            "release_helper": "FUN_00688010",
        },
    }
