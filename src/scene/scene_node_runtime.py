"""Evidence-backed scene object semantics recovered from SHIFT.exe.c.

This module models the SCENE XML object dispatch around FUN_006a4160 and the
NODE/TRANSFORM helpers. It does not claim that these object records are the
same thing as the opaque SGB NODE/FLAT/SUMM chunk payloads.
"""
from __future__ import annotations

import math
from typing import Any, Iterable

FORMAT = "SHIFT.SceneNodeRuntime/1"

OBJECT_TYPES = {
    "TRANSFORM": "transform",
    "NODE": "node",
    "TERRAIN": "terrain",
    "PARTICLES": "particles",
    "OCCLUDER": "occluder",
    "LIGHT": "light",
}

NODE_ATTRIBUTES = {
    "Merged": "merged",
    "Animated": "animated",
    "Dynamic": "dynamic",
    "VariationIndex": "variation_index",
    "Instances": "instances",
    "Resource": "resource",
    "VariationPaletteFile": "variation_palette_file",
}

LIGHT_TYPES = {
    "Ambient": 1,
    "Directional": 2,
    "Spotlight": 3,
    "Point": 4,
}


def _bool_text(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    text = str(value).strip().upper()
    if text == "TRUE":
        return True
    if text == "FALSE":
        return False
    raise ValueError(f"invalid scene boolean {value!r}")


def _float_list(values: Iterable[Any], count: int) -> list[float]:
    result = [float(x) for x in values]
    if len(result) != count:
        raise ValueError(f"expected {count} float values, got {len(result)}")
    return result


def parse_integer_reference_list(value: str | None) -> list[int]:
    """Reconstruct FUN_006a40e0's permissive decimal/0x integer list scan."""
    if value is None:
        return []
    text = str(value)
    end = len(text) - 1
    while end >= 0 and not text[end].isdigit():
        end -= 1
    if end < 0:
        return []

    start = 0
    out: list[int] = []
    while start <= end:
        p = start
        while p <= end and not (text[p].isdigit() or text[p] in "+-xXaAbBcCdDeEfF"):
            p += 1
        if p > end:
            break
        try:
            number = int(text[p:].split()[0].rstrip(",;"), 0)
        except ValueError:
            # Match the source's strtol-style behavior by advancing to a
            # following delimiter instead of fabricating a number.
            q = p
            while q <= end and text[q] not in ",; \t\r\n":
                q += 1
            start = q + 1
            continue
        out.append(number)
        q = p
        while q <= end and text[q] not in ",; \t\r\n":
            q += 1
        start = q + 1
    return out


def parse_transform(
    *,
    position: Iterable[Any] | None = None,
    orientation: Iterable[Any] | None = None,
    scale: Any | None = None,
) -> dict[str, Any]:
    """Normalize TRANSFORM attributes from FUN_006a3b40."""
    pos = [0.0, 0.0, 0.0] if position is None else _float_list(position, 3)
    orient = [1.0, 0.0, 0.0, 0.0] if orientation is None else _float_list(orientation, 4)
    scalar = 1.0 if scale is None else float(scale)
    return {
        "format": "SHIFT.SceneTransform/1",
        "position": pos,
        "orientation": orient,
        "scale": scalar,
        "source_function": "FUN_006a3b40",
    }


def parse_node(
    *,
    name: str,
    attributes: dict[str, Any] | None = None,
    transform: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize a NODE record using only fields observed in FUN_0069ba40."""
    attrs = attributes or {}
    instances = int(attrs.get("Instances", 1))
    if instances < 1:
        raise ValueError("scene NODE Instances must be >= 1")
    variation_index = int(attrs.get("VariationIndex", 0))

    resource = attrs.get("Resource")
    palette = attrs.get("VariationPaletteFile")
    return {
        "format": FORMAT,
        "version": 1,
        "type": "node",
        "name": str(name),
        "flags": {
            "merged": _bool_text(attrs.get("Merged"), False),
            "animated": _bool_text(attrs.get("Animated"), False),
            "dynamic": _bool_text(attrs.get("Dynamic"), False),
        },
        "variation_index": variation_index,
        "instances": instances,
        "resource": None if resource is None else str(resource),
        "variation_palette_file": None if palette is None else str(palette),
        "transform": transform,
        "evidence": {
            "node_parser": "FUN_0069ba40",
            "object_dispatch": "FUN_006a4160",
        },
    }


def parse_light(
    *,
    light_type: str | None = None,
    position: Iterable[Any] | None = None,
    direction: Iterable[Any] | None = None,
    colour: Iterable[Any] | None = None,
    intensity: Any | None = None,
    range_value: Any | None = None,
    inner_angle: Any | None = None,
    outer_angle: Any | None = None,
    casts_shadows: Any | None = None,
) -> dict[str, Any]:
    kind = None
    if light_type is not None:
        try:
            kind = LIGHT_TYPES[str(light_type)]
        except KeyError as exc:
            raise ValueError(f"unknown scene light type {light_type!r}") from exc

    inner = 0.0 if inner_angle is None else float(inner_angle)
    outer = 0.0 if outer_angle is None else float(outer_angle)
    return {
        "format": "SHIFT.SceneLight/1",
        "type": str(light_type) if light_type is not None else None,
        "type_code": kind,
        "position": [0.0, 0.0, 0.0] if position is None else _float_list(position, 3),
        "direction": [0.0, 0.0, 0.0] if direction is None else _float_list(direction, 3),
        "colour": [0.0, 0.0, 0.0] if colour is None else _float_list(colour, 3),
        "intensity": 0.0 if intensity is None else float(intensity),
        "range": 0.0 if range_value is None else float(range_value),
        "inner_angle_radians": math.radians(inner * 0.5),
        "outer_angle_radians": math.radians(outer * 0.5),
        "casts_shadows": _bool_text(casts_shadows, False),
        "source_function": "FUN_006a3e00",
        "angle_conversion": "degrees_to_radians after multiplying by 0.5",
    }


def parse_scene_partition(
    *,
    partition_id: int | str | None = None,
    aabbox_min: Iterable[Any] | None = None,
    aabbox_max: Iterable[Any] | None = None,
    child_partitions: str | None = None,
    child_objects: str | None = None,
) -> dict[str, Any]:
    """Normalize partition fields consumed by FUN_006a4160/FUN_006a450d."""
    return {
        "format": "SHIFT.ScenePartition/1",
        "partition_id": None if partition_id is None else int(partition_id),
        "aabbox_min": None if aabbox_min is None else _float_list(aabbox_min, 3),
        "aabbox_max": None if aabbox_max is None else _float_list(aabbox_max, 3),
        "child_partitions": parse_integer_reference_list(child_partitions),
        "child_objects": parse_integer_reference_list(child_objects),
        "child_partitions_source": child_partitions,
        "child_objects_source": child_objects,
        "evidence": {
            "partition_consumer": "FUN_006a4160/FUN_006a450d",
            "id_list_parser": "FUN_006a40e0",
        },
    }


def classify_object_type(tag: str) -> dict[str, Any]:
    normalized = str(tag).upper()
    kind = OBJECT_TYPES.get(normalized)
    return {
        "format": "SHIFT.SceneObjectType/1",
        "tag": normalized,
        "kind": kind,
        "recognized": kind is not None,
        "evidence": "FUN_006a4160",
    }


def build_scene_manifest(
    objects: Iterable[dict[str, Any]],
    *,
    file_version: str | int | None = None,
    merged: bool = False,
) -> dict[str, Any]:
    rows = [dict(x) for x in objects]
    counts: dict[str, int] = {}
    unknown: list[str] = []
    for row in rows:
        tag = str(row.get("tag") or row.get("type") or "").upper()
        classification = classify_object_type(tag)
        if not classification["recognized"]:
            unknown.append(tag)
        else:
            counts[classification["kind"]] = counts.get(classification["kind"], 0) + 1
        row["classification"] = classification

    return {
        "format": FORMAT,
        "version": 1,
        "scene_file_version": None if file_version is None else str(file_version),
        "merged": bool(merged),
        "objects": rows,
        "object_counts": counts,
        "unknown_object_types": sorted(set(unknown)),
        "evidence": {
            "scene_entry": "FUN_006a4160",
            "node_builder": "FUN_0069ba40",
            "transform_builder": "FUN_006a3b40",
        },
        "limitations": [
            "This manifest does not decode opaque SGB NODE/FLAT/SUMM chunk payloads.",
            "Parent-child transform composition is not inferred here.",
        ],
    }
