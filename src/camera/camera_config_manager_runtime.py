"""Evidence-backed CameraConfigManager XML/load/reset runtime.

Recovered from FUN_00810040, FUN_00810180, FUN_00810410, FUN_00810430,
FUN_00810490, FUN_00810530, FUN_008105f0 and FUN_008106d0.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.CameraConfigManagerRuntime/1"


def get_camera_config_entry(
    *,
    entries: Sequence[Any],
    index: int,
) -> dict[str, Any]:
    """Reproduce FUN_00810410 bounds check and indexed lookup."""
    i = int(index)
    if i < 0 or i >= len(entries):
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "camera-config-get",
            "status": "out-of-range",
            "index": i,
            "value": None,
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-config-get",
        "status": "found",
        "index": i,
        "value": entries[i],
        "evidence": {"function": "FUN_00810410", "count_field": "+0x34"},
    }


def find_camera_config_index(
    *,
    entries: Sequence[Mapping[str, Any]],
    query: Any,
    helper_matches: Mapping[int, bool] | None = None,
) -> dict[str, Any]:
    """Reproduce FUN_00810430's first-match scan."""
    matches = helper_matches or {}
    for index, entry in enumerate(entries):
        matched = bool(matches.get(index, entry.get("matches_query", False)))
        if matched:
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "camera-config-find-index",
                "status": "found",
                "index": index,
                "query": query,
                "actions": [
                    {
                        "action": "entry.vtable +0x10",
                        "result": entry.get("property_value"),
                    },
                    {
                        "action": "FUN_00408210",
                        "result": True,
                    },
                ],
                "evidence": {"function": "FUN_00810430", "first_match": True},
            }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-config-find-index",
        "status": "not-found",
        "index": -1,
        "query": query,
    }


def release_camera_config_list(
    entries: Sequence[Any],
) -> dict[str, Any]:
    """Reproduce FUN_00810490 list-release behavior for non-null entries."""
    non_null = [entry for entry in entries if entry not in (None, 0)]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-config-list-release",
        "released_count": len(non_null),
        "release_callback": "entry.vtable[0](1)",
        "actions": [
            {
                "action": "FUN_00688010",
                "target": "list",
                "after_releasing": len(non_null),
            }
        ],
        "evidence": {
            "function": "FUN_00810490",
            "lists": ["+0x10", "+0x44"],
        },
    }


def serialize_camera_config_list(
    *,
    entries: Sequence[Any],
    funcpropdata: Any = None,
) -> dict[str, Any]:
    """Reproduce FUN_00810530's per-entry serializer order."""
    actions: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        actions.extend([
            {
                "action": "entry.vtable +0x04",
                "index": index,
                "result": entry,
            },
            {
                "action": "FUN_00640dd0",
                "index": index,
                "funcpropdata": funcpropdata,
            },
        ])
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-config-list-save",
        "source_list": "+0x44",
        "count": len(entries),
        "actions": actions,
        "evidence": {
            "function": "FUN_00810530",
            "xml_elements": "param_2+0x84.elements",
            "funcpropdata_bytes": 0x50,
            "per_entry_order": "vtable +0x04 -> FUN_00640dd0",
        },
    }


def load_camera_config_elements(
    *,
    class_entries: Sequence[Mapping[str, Any]],
    existing_configs: Sequence[Mapping[str, Any]],
    apply_success: Mapping[int, bool] | None = None,
    class_conversion_success: Mapping[int, bool] | None = None,
    property_matches: Mapping[tuple[int, int], bool] | None = None,
) -> dict[str, Any]:
    """Reproduce FUN_00810180's XML element loop and merge strategy."""
    apply_ok = apply_success or {}
    conversion_ok = class_conversion_success or {}
    matches = property_matches or {}
    actions: list[dict[str, Any]] = []
    working = list(existing_configs)

    for element_index, element in enumerate(class_entries):
        class_name = element.get("class")
        secondary = element.get("secondary")
        actions.append({
            "action": "read element class",
            "index": element_index,
            "class": class_name,
            "secondary": secondary,
        })
        if not conversion_ok.get(element_index, True):
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "camera-config-load",
                "status": "failed-class-conversion",
                "failed_index": element_index,
                "actions": actions,
            }

        actions.append({
            "action": "allocate",
            "bytes": 0x11C,
            "constructor": "FUN_00823760",
        })
        actions.append({
            "action": "FUN_006408f0",
            "index": element_index,
            "class": class_name,
            "secondary": secondary,
            "success": apply_ok.get(element_index, True),
        })
        if not apply_ok.get(element_index, True):
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "camera-config-load",
                "status": "failed-apply",
                "failed_index": element_index,
                "actions": actions,
            }

        matching_index = None
        for existing_index, existing in enumerate(working):
            matched = bool(
                matches.get(
                    (element_index, existing_index),
                    existing.get("name") == class_name,
                    )
            )
            if matched:
                matching_index = existing_index
                break

        if matching_index is None:
            working.append({
                "name": class_name,
                "secondary": secondary,
                "source": "FUN_00810180",
            })
            actions.append({
                "action": "FUN_004cb900",
                "target": "+0x44",
                "reason": "no existing name match",
                "index": len(working) - 1,
            })
        else:
            working[matching_index] = {
                **dict(working[matching_index]),
                "name": class_name,
                "secondary": secondary,
                "source": "FUN_00810180",
            }
            actions.append({
                "action": "refresh existing config",
                "index": matching_index,
                "reason": "name match",
                "helpers": [
                    "FUN_0080fd60",
                    "FUN_006408f0",
                    "entry.vtable +0x28",
                    "FUN_0080fd60(existing)",
                ],
            })

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-config-load",
        "status": "ok",
        "loaded_count": len(class_entries),
        "result_configs": working,
        "actions": actions,
        "evidence": {
            "function": "FUN_00810180",
            "xml_elements": "param_4+0x8c.elements",
            "property_container": "param_4+0x8c",
            "record_allocation": 0x11C,
        },
    }


def rebuild_camera_config_list(
    *,
    source_entries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Reproduce FUN_008105f0's conversion from +0x44 to +0x10."""
    rebuilt = [
        {
            "name": entry.get("name"),
            "source": entry,
            "constructor": "FUN_00823760",
        }
        for entry in source_entries
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-config-rebuild",
        "status": "rebuilt",
        "source_list": "+0x44",
        "destination_list": "+0x10",
        "count": len(rebuilt),
        "actions": [
            {"action": "allocate", "bytes": 0x11C, "constructor": "FUN_00823760"},
            {
                "action": "FUN_0080fd60",
                "source": "+0x44 entry",
            },
            {
                "action": "source.vtable +0x10",
                "purpose": "obtain configuration name/object",
            },
            {
                "action": "camera-config.vtable +0x14",
                "purpose": "apply source object",
            },
            {
                "action": "FUN_004cb900",
                "target": "+0x10",
            },
        ],
        "rebuilt": rebuilt,
        "evidence": {
            "function": "FUN_008105f0",
            "record_constructor": "FUN_00823760",
        },
    }


def describe_config_manager_refresh(
    *,
    config_source_available: bool,
    base_config_object: Any,
) -> dict[str, Any]:
    """Reproduce FUN_00810040's three temporary-object refreshes."""
    if not config_source_available:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "config-manager-refresh",
            "status": "source-unavailable",
            "actions": [],
        }

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "config-manager-refresh",
        "status": "refreshed",
        "actions": [
            {"action": "request ConfigManager", "name": "ConfigManager"},
            {
                "action": "copy config into temporary snapshot",
                "constructor": "FUN_00823760",
                "source": base_config_object,
            },
            {
                "action": "copy config into static camera",
                "constructor": "FUN_00813180",
                "post_copy": "FUN_00813500",
            },
            {
                "action": "copy config into tracking camera",
                "constructor": "FUN_0081f8c0",
                "post_copy": "FUN_0081ea60",
            },
            {"action": "finalize config manager", "vtable": "+0x40"},
        ],
        "evidence": {
            "function": "FUN_00810040",
            "config_manager_name": "ConfigManager",
            "snapshot_constructor": "FUN_00823760",
            "static_constructor": "FUN_00813180",
            "tracking_constructor": "FUN_0081f8c0",
        },
    }


def describe_config_manager_reset() -> dict[str, Any]:
    """Reproduce FUN_008106d0 exact reset order."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "config-manager-reset",
        "actions": [
            {"action": "write vtable", "value": "PTR_FUN_00b15908"},
            {"action": "FUN_00810490"},
            {"action": "FUN_0081ea60", "target": "+0x168"},
            {"action": "FUN_00813500", "target": "+0x78"},
            {"action": "FUN_004f0050", "target": "+0x44"},
            {"action": "FUN_004f0050", "target": "+0x10"},
            {"action": "FUN_006383f0"},
        ],
        "evidence": {"function": "FUN_008106d0"},
    }
