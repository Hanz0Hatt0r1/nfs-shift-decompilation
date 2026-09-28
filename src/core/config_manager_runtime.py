"""Evidence-backed ConfigManager camera configuration runtime.

Recovered from FUN_00810040, FUN_00810180, FUN_00810410, FUN_00810430,
FUN_00810490, FUN_00810530, FUN_008105f0 and FUN_008106d0/FUN_00810710.

This module models container-level behavior only. Generic MWL/XML/property
helpers remain opaque, while object ownership, lookup, callback ordering and
the two camera-data collections are represented explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

FORMAT = "SHIFT.ConfigManagerRuntime/1"


@dataclass(frozen=True)
class ConfigEntry:
    class_name: str
    secondary_name: str
    object_value: Any = None
    factory_id: Any = None


@dataclass
class ConfigManagerState:
    configs: list[ConfigEntry] = field(default_factory=list)      # +0x10
    defaults: list[Any] = field(default_factory=list)            # +0x44
    selected_default: Any = None                                 # +0x78-backed object
    selected_tracking_default: Any = None                        # +0x168-backed object


def indexed_config(
    entries: Sequence[Any],
    index: int,
) -> dict[str, Any]:
    """Reproduce FUN_00810410."""
    i = int(index)
    if i < 0 or i >= len(entries):
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "indexed-config",
            "status": "out-of-range",
            "value": 0,
            "index": i,
            "evidence": {"function": "FUN_00810410"},
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "indexed-config",
        "status": "found",
        "value": entries[i],
        "index": i,
        "evidence": {
            "function": "FUN_00810410",
            "count_source": "+0x34",
            "array_source": "+0x10",
        },
    }


def find_config_index(
    entries: Sequence[ConfigEntry],
    *,
    query: Any,
    object_property_values: Sequence[Any],
) -> dict[str, Any]:
    """Reproduce FUN_00810430's vtable-property comparison loop."""
    if len(entries) != len(object_property_values):
        raise ValueError("entry/property arrays must have equal length")
    for index, property_value in enumerate(object_property_values):
        if property_value == query:
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "find-config-index",
                "status": "found",
                "index": index,
                "value": entries[index],
                "evidence": {
                    "function": "FUN_00810430",
                    "property_getter": "entry.vtable +0x10",
                    "compare": "FUN_00408210",
                },
            }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "find-config-index",
        "status": "not-found",
        "index": -1,
        "evidence": {"function": "FUN_00810430"},
    }


def release_config_arrays(
    configs: Sequence[Any],
    defaults: Sequence[Any],
) -> dict[str, Any]:
    """Reproduce FUN_00810490's two independent release walks."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "release-arrays",
        "actions": [
            {
                "action": "release each config object",
                "count": len(configs),
                "array": "+0x10",
                "helper": "object vtable destructor/ref-release",
            },
            {
                "action": "FUN_00688010",
                "array": "+0x10",
            },
            {
                "action": "release each default object",
                "count": len(defaults),
                "array": "+0x44",
                "helper": "object vtable destructor/ref-release",
            },
            {
                "action": "FUN_00688010",
                "array": "+0x44",
            },
        ],
        "evidence": {
            "function": "FUN_00810490",
            "config_array": "+0x10",
            "default_array": "+0x44",
        },
    }


def load_config_manager(
    *,
    xml_object: Any,
    manager_registration_succeeded: bool,
    config_entries_result: Sequence[ConfigEntry],
    default_static_object: Any,
    default_tracking_object: Any,
) -> dict[str, Any]:
    """Trace FUN_00810040's top-level ConfigManager load pipeline."""
    actions = [
        {"action": "FUN_0080cc60"},
        {
            "action": "register manager",
            "name": "ConfigManager",
            "helper": "FUN_00631740 + manager vtable +0x14",
        },
        {
            "action": "read manager properties",
            "helper": "manager vtable +0x38",
        },
        {
            "action": "construct ConfigManager config snapshot",
            "helper": "FUN_00823760",
        },
        {
            "action": "copy ConfigManager source state",
            "helper": "FUN_00638360",
        },
        {
            "action": "construct default static camera data",
            "helper": "FUN_00813180",
        },
        {
            "action": "copy static default",
            "helper": "FUN_00638360",
        },
        {
            "action": "construct default tracking camera data",
            "helper": "FUN_0081f8c0",
        },
        {
            "action": "copy tracking default",
            "helper": "FUN_00638360",
        },
        {
            "action": "finalize manager properties",
            "helper": "manager vtable +0x40",
        },
    ]
    if not manager_registration_succeeded:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "load-config-manager",
            "status": "registration-failed",
            "actions": actions,
            "evidence": {"function": "FUN_00810040"},
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "load-config-manager",
        "status": "loaded",
        "xml_object": xml_object,
        "config_entries": list(config_entries_result),
        "default_static": default_static_object,
        "default_tracking": default_tracking_object,
        "actions": actions,
        "evidence": {
            "function": "FUN_00810040",
            "config_snapshot": "FUN_00823760",
            "static_default": "FUN_00813180",
            "tracking_default": "FUN_0081f8c0",
        },
    }


def deserialize_config_entries(
    *,
    xml_entries: Sequence[Mapping[str, Any]],
    existing_entries: Sequence[ConfigEntry],
    existing_properties: Sequence[str],
    factory_succeeded: bool = True,
    property_apply_succeeded: bool = True,
    object_factory: str = "FUN_00823760",
) -> dict[str, Any]:
    """Trace FUN_00810180's XML entry creation and replacement checks."""
    if len(existing_entries) != len(existing_properties):
        raise ValueError("existing entry/property arrays must have equal length")

    parsed: list[ConfigEntry] = list(existing_entries)
    actions: list[dict[str, Any]] = []
    for ordinal, element in enumerate(xml_entries):
        class_name = str(element.get("class", ""))
        secondary_name = str(element.get("secondary", ""))
        actions.append({
            "action": "read XML attributes",
            "ordinal": ordinal,
            "class": class_name,
            "secondary": secondary_name,
        })

        if not factory_succeeded:
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "deserialize-config-entries",
                "status": "factory-failed",
                "parsed": parsed,
                "actions": actions,
                "evidence": {"function": "FUN_00810180"},
            }

        entry = ConfigEntry(
            class_name=class_name,
            secondary_name=secondary_name,
            object_value=object_factory,
        )
        matched = False
        for index, existing_property in enumerate(existing_properties):
            if existing_property == secondary_name:
                matched = True
                actions.extend([
                    {
                        "action": "FUN_0080fd60",
                        "target": f"existing[{index}]",
                        "source": f"new[{ordinal}]",
                    },
                    {
                        "action": "existing vtable +0x28",
                        "index": index,
                    },
                    {
                        "action": "FUN_0080fd60",
                        "target": f"new[{ordinal}]",
                        "source": f"existing[{index}]",
                    },
                ])
                break
        if matched:
            parsed.append(entry)
        else:
            actions.append({
                "action": "append new config",
                "array": "+0x44",
                "ordinal": ordinal,
            })
            parsed.append(entry)

        if not property_apply_succeeded:
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "deserialize-config-entries",
                "status": "property-application-failed",
                "parsed": parsed,
                "actions": actions,
                "evidence": {"function": "FUN_00810180"},
            }

        actions.append({
            "action": "FUN_006408f0",
            "ordinal": ordinal,
            "result": True,
        })

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "deserialize-config-entries",
        "status": "loaded",
        "parsed": parsed,
        "actions": actions,
        "evidence": {
            "function": "FUN_00810180",
            "xml_root": "param_4 + 0x8c.elements",
            "entry_size": 0x11c,
            "secondary_attribute": "DAT_00aaadb0",
        },
        "limitations": [
            "class conversion and exact duplicate-entry policy are exposed as container-level boundaries",
        ],
    }


def serialize_config_entries(
    entries: Sequence[ConfigEntry],
    *,
    class_conversion_succeeded: bool = True,
    record_application_succeeded: bool = True,
) -> dict[str, Any]:
    """Trace FUN_00810530's reverse XML callback."""
    actions: list[dict[str, Any]] = [
        {
            "action": "FUN_0063e9b0",
            "target": "elements",
        },
        {
            "action": "allocate funcpropdata",
            "bytes": 0x50,
        },
    ]
    for index, entry in enumerate(entries):
        actions.append({
            "action": "iterate default/config object",
            "index": index,
            "class_name": entry.class_name,
            "secondary_name": entry.secondary_name,
        })
        if not class_conversion_succeeded:
            actions.append({
                "action": "abort",
                "index": index,
                "reason": "record class/property conversion failed",
            })
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "serialize-config-entries",
                "status": "failed",
                "actions": actions,
            }
        actions.append({
            "action": "FUN_00640dd0",
            "index": index,
            "class": entry.class_name,
            "secondary": entry.secondary_name,
        })
        if not record_application_succeeded:
            actions.append({
                "action": "abort",
                "index": index,
                "reason": "FUN_00640dd0 rejected record",
            })
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "serialize-config-entries",
                "status": "failed",
                "actions": actions,
            }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "serialize-config-entries",
        "status": "saved",
        "actions": actions,
        "evidence": {
            "function": "FUN_00810530",
            "root": "param_2 + 0x84.elements",
            "funcpropdata_size": 0x50,
        },
    }


def clone_default_objects(
    defaults: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Trace FUN_008105f0 cloning from the manager-owned defaults array."""
    clones = []
    actions = []
    for index, source in enumerate(defaults):
        clone = dict(source)
        clones.append(clone)
        actions.extend([
            {
                "action": "FUN_00823760",
                "allocation_bytes": 0x11C,
                "index": index,
            },
            {
                "action": "FUN_0080fd60",
                "index": index,
            },
            {
                "action": "source vtable +0x10",
                "index": index,
            },
            {
                "action": "clone vtable +0x14",
                "index": index,
            },
        ])
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "clone-default-objects",
        "status": "cloned",
        "clones": clones,
        "actions": actions,
        "evidence": {
            "function": "FUN_008105f0",
            "source_array": "+0x44",
            "destination_array": "+0x10",
            "element_size": 0x11C,
        },
    }


def describe_config_manager_reset() -> dict[str, Any]:
    """Reproduce FUN_008106d0."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "reset",
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


def describe_config_manager_registration() -> dict[str, Any]:
    """Reproduce FUN_00810710's property/container registrations."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "registration",
        "properties": [
            {"name": "FreeLookYawLimits", "type_id": 0x0F, "offset": 0x2B8, "flags": 2},
            {"name": "FreeLookPitchLimits", "type_id": 0x0F, "offset": 0x2C0, "flags": 2},
            {"name": "RotateChaseCamPitchLimits", "type_id": 0x0F, "offset": 0x2C8, "flags": 2},
            {"name": "Camera configs", "type_id": 6, "offset": 0x10, "flags": 2},
            {"name": "DefaultStaticCamData", "type_id": 6, "offset": 0x78, "flags": 2},
            {"name": "DefaultTrackingCamData", "type_id": 6, "offset": 0x168, "flags": 2},
        ],
        "container_callbacks": {
            "Camera configs": {
                "save": "FUN_00810530",
                "load": "FUN_00810180",
            },
            "DefaultStaticCamData": {
                "save": "FUN_0080f9d0",
                "load": "FUN_0080fa40",
            },
            "DefaultTrackingCamData": {
                "save": "FUN_0080fb40",
                "load": "FUN_0080fbb0",
            },
        },
        "evidence": {
            "function": "FUN_00810710",
            "registration_helper": "FUN_0063a280",
            "container_helper": "FUN_006420b0",
            "type_factory_id": "0xbfa72c",
        },
    }
