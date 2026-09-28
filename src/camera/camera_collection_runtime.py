"""Camera collection/index and XML dispatch runtime around FUN_00816ba0..00816d30."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.CameraCollectionRuntime/1"
STATIC_CAMERA_TYPE = "DAT_00c25e70"


def previous_camera_index(*, value: int, current_slot_count: int) -> dict[str, Any]:
    """Reproduce FUN_00816ba0."""
    count = int(current_slot_count)
    v = int(value)
    if v == 0:
        result = count - 1
        source = "+0x244-derived count"
    else:
        result = v - 1
        source = "input - 1"
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "previous-index",
        "result": result,
        "source": source,
        "evidence": {"function": "FUN_00816ba0"},
    }


def next_camera_index(*, value: int, current_slot_count: int) -> dict[str, Any]:
    """Reproduce FUN_00816bd0."""
    count = int(current_slot_count)
    last = count - 1
    v = int(value)
    result = 0 if v == last else v + 1
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "next-index",
        "result": result,
        "wrapped": v == last,
        "evidence": {"function": "FUN_00816bd0"},
    }


def next_index_for_slot(
    *,
    value: int,
    slot_selector: int,
    slot_counts: Mapping[int, int],
) -> dict[str, Any]:
    """Reproduce FUN_00816c00's selector-specific wrap."""
    if int(slot_selector) not in slot_counts:
        raise KeyError(slot_selector)
    last = int(slot_counts[int(slot_selector)]) - 1
    v = int(value)
    result = 0 if v == last else v + 1
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "selector-next-index",
        "result": result,
        "wrapped": v == last,
        "slot_selector": int(slot_selector),
        "evidence": {"function": "FUN_00816c00"},
    }


def update_collection_marker(
    *,
    collection_present: bool,
    index: int,
    marker_flag: int,
    local_lookup_succeeded: bool,
) -> dict[str, Any]:
    """Reproduce FUN_00816c30."""
    if not collection_present:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "collection-marker",
            "status": "ignored",
        }
    if int(marker_flag) == 0:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "collection-marker",
            "status": "marked",
            "writes": {
                "entry.byte_0d": 1,
                "entry.byte_0e": 1,
            },
            "lookup": local_lookup_succeeded,
            "evidence": {"function": "FUN_00816c30"},
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "collection-marker",
        "status": "counter-increment",
        "writes": {"+0x36c": "old + 1"},
        "evidence": {"function": "FUN_00816c30"},
    }


def update_secondary_collection_marker(
    *,
    collection_present: bool,
    index: int,
    marker_flag: int,
) -> dict[str, Any]:
    """Reproduce FUN_00816c70."""
    if not collection_present:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "secondary-marker",
            "status": "ignored",
        }
    if int(marker_flag) == 0:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "secondary-marker",
            "status": "marked",
            "writes": {
                "entry.byte_0d": 1,
                "entry.byte_0e": 1,
            },
            "evidence": {"function": "FUN_00816c70"},
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "secondary-marker",
        "status": "counter-increment",
        "writes": {"+0x374": "old + 1"},
        "evidence": {"function": "FUN_00816c70"},
    }


def reset_collection_condition(
    *,
    mode: int,
    collection_present: bool,
) -> dict[str, Any]:
    """Reproduce FUN_00816cb0."""
    should_reset = int(mode) in (0, 0x7FFFFFFF) and bool(collection_present)
    if not should_reset:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "collection-reset",
            "status": "not-triggered",
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "collection-reset",
        "status": "reset",
        "writes": {
            "+0x240": 0,
            "+0x244": 0x7FFFFFFF,
            "+0x328.deref": 0,
            "+0x265": 1,
        },
        "action": "FUN_00816570",
        "evidence": {"function": "FUN_00816cb0"},
    }


def force_collection_reset() -> dict[str, Any]:
    """Reproduce FUN_00816d00."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "collection-force-reset",
        "writes": {
            "+0x244": 4,
            "+0x328.deref": 0,
            "+0x266": 1,
            "+0x265": 1,
        },
        "actions": [
            {"action": "FUN_00816570"},
        ],
        "evidence": {"function": "FUN_00816d00"},
    }


def deserialize_camera_collection(
    *,
    elements: Sequence[Mapping[str, Any]],
    factory_results: Sequence[Any],
    application_results: Sequence[bool],
    inheritance_results: Sequence[Sequence[Any]],
) -> dict[str, Any]:
    """Trace FUN_00816d30's per-element XML/factory/application loop."""
    if not (
        len(elements)
        == len(factory_results)
        == len(application_results)
        == len(inheritance_results)
    ):
        raise ValueError("all collection result arrays must have equal length")
    actions: list[dict[str, Any]] = []
    outputs = []
    for index, element in enumerate(elements):
        class_name = str(element.get("class", ""))
        secondary_name = str(element.get("secondary", ""))
        actions.extend([
            {
                "action": "read XML attributes",
                "index": index,
                "class": class_name,
                "secondary": secondary_name,
            },
            {
                "action": "FUN_00823a60",
                "result": factory_results[index],
            },
        ])
        factory = factory_results[index]
        if factory is None or factory is False:
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "deserialize-camera-collection",
                "status": "factory-failed",
                "actions": actions,
            }
        if not application_results[index]:
            actions.append({
                "action": "FUN_006408f0",
                "result": False,
                "index": index,
            })
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "deserialize-camera-collection",
                "status": "application-failed",
                "actions": actions,
            }
        static_match = STATIC_CAMERA_TYPE in inheritance_results[index]
        actions.append({
            "action": "FUN_004cb900",
            "index": index,
            "static_camera_inheritance": static_match,
        })
        outputs.append({
            "class": class_name,
            "secondary": secondary_name,
            "factory": factory,
            "is_static_camera_derived": static_match,
        })
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "deserialize-camera-collection",
        "status": "loaded",
        "entries": outputs,
        "actions": actions,
        "evidence": {
            "function": "FUN_00816d30",
            "xml_root": "param_4 + 0x8c.elements",
            "secondary_attribute": "DAT_00aaadb0",
            "static_camera_type": STATIC_CAMERA_TYPE,
        },
    }
