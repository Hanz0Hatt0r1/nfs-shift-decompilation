"""D3D9 texture-object lifecycle evidence.

This module links runtime texture pointers seen by SetTexture to successful
CreateTexture/CreateCubeTexture events from the same capture stream. It never
derives a game DDS path from a pointer alone.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

FORMAT = "SHIFT.D3D9TextureLifecycle/1"
CREATE_EVENTS = {"create_texture", "create_cube_texture"}


def _ptr(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, int):
        return f"0x{value:x}"
    value = str(value).strip()
    if not value:
        return None
    try:
        return f"0x{int(value, 0):x}"
    except ValueError:
        return value.lower()


def build_texture_lifecycle(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    resources: dict[str, dict[str, Any]] = {}
    bindings: list[dict[str, Any]] = []
    blockers: list[str] = []

    for event_index, row in enumerate(events):
        event = row.get("event")
        if event in CREATE_EVENTS:
            pointer = _ptr(row.get("texture_ptr"))
            if not pointer:
                blockers.append(f"create:{event_index}:texture-pointer-missing")
                continue
            if pointer in resources:
                blockers.append(f"create:{event_index}:duplicate-texture-pointer:{pointer}")
                continue
            if event == "create_texture":
                resource = {
                    "texture_ptr": pointer,
                    "resource_type": "texture2d",
                    "width": int(row["width"]),
                    "height": int(row["height"]),
                    "level_count": int(row["levels"]),
                    "usage": int(row["usage"]),
                    "format": int(row["format"]),
                    "pool": int(row["pool"]),
                    "frame": row.get("frame"),
                    "event_index": row.get("event_index", event_index),
                    "line": row.get("_line"),
                }
            else:
                resource = {
                    "texture_ptr": pointer,
                    "resource_type": "cube_texture",
                    "edge_length": int(row["edge_length"]),
                    "width": int(row["edge_length"]),
                    "height": int(row["edge_length"]),
                    "level_count": int(row["levels"]),
                    "usage": int(row["usage"]),
                    "format": int(row["format"]),
                    "pool": int(row["pool"]),
                    "frame": row.get("frame"),
                    "event_index": row.get("event_index", event_index),
                    "line": row.get("_line"),
                }
            resources[pointer] = resource
        elif event == "set_texture":
            pointer = _ptr(row.get("texture_ptr"))
            binding = {
                "source_index": event_index,
                "stage": int(row["stage"]),
                "texture_ptr": pointer,
                "frame": row.get("frame"),
                "event_index": row.get("event_index", event_index),
                "line": row.get("_line"),
            }
            if pointer is None:
                binding["resource_creation_status"] = "null"
            else:
                creation = resources.get(pointer)
                binding["resource_creation_status"] = (
                    "observed" if creation is not None else "not-observed"
                )
                if creation is not None:
                    binding["resource_creation"] = dict(creation)
            bindings.append(binding)

    observed_bindings = sum(
        1 for row in bindings if row.get("resource_creation_status") == "observed"
    )
    nonnull_bindings = sum(
        1 for row in bindings if row.get("texture_ptr") is not None
    )
    status = "match" if nonnull_bindings == observed_bindings else (
        "partial" if observed_bindings else ("not-observed" if not bindings else "unresolved")
    )
    return {
        "format": FORMAT,
        "status": status,
        "ready": nonnull_bindings == observed_bindings and nonnull_bindings > 0 and not blockers,
        "resource_count": len(resources),
        "set_texture_count": len(bindings),
        "observed_pointer_bindings": observed_bindings,
        "unresolved_pointer_bindings": nonnull_bindings - observed_bindings,
        "resources": list(resources.values()),
        "bindings": bindings,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "boundary": {
            "pointer_to_creation_instance": "proven" if observed_bindings else "not-proven",
            "dds_identity": "not-proven",
        },
    }
