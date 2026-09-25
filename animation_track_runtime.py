"""Evidence-backed TRACK/node runtime semantics recovered from SHIFT.exe.c.

This module models the semantic contract of the XML animation runtime rather
than assuming its track-form names are identical to numeric BAB channel ids.

Recovered parser/attachment functions:
- FUN_00a67540: usage + duration + track-form dispatch;
- FUN_00a63810 / FUN_00a63bd0: sampled Vec3/Quat attachment;
- FUN_00a63e70 / FUN_00a64190: keyed Vec3/Quat attachment;
- FUN_00a643d0 / FUN_00a64540 / FUN_00a65950: fixed Vec3/Quat/f32 attachment;
- FUN_00a670b0: node base-transform defaults;
- FUN_00a64630 / FUN_00a64d90: animation-node tree mapping/count checks.
"""
from __future__ import annotations

import struct
from typing import Any

FORMAT = "SHIFT.AnimationTrackRuntime/1"

TRACK_FORMS: dict[str, dict[str, Any]] = {
    "SampledVec3f": {"value_type": "vec3", "storage": "sampled", "parser": "FUN_00a671f0", "attachment": "FUN_00a63810"},
    "SampledQuatf": {"value_type": "quat", "storage": "sampled", "parser": "FUN_00a67320", "attachment": "FUN_00a63bd0"},
    "Sampledf32": {"value_type": "f32", "storage": "sampled", "parser": "FUN_00a66560", "attachment": "FUN_00a657b0"},
    "KeyedVec3f": {"value_type": "vec3", "storage": "keyed", "parser": "FUN_00a66c60", "attachment": "FUN_00a63e70"},
    "KeyedQuatf": {"value_type": "quat", "storage": "keyed", "parser": "FUN_00a66da0", "attachment": "FUN_00a64190"},
    "Keyedf32": {"value_type": "f32", "storage": "keyed", "parser": "FUN_00a66640", "attachment": "FUN_00a65820"},
    "FixedVec3f": {"value_type": "vec3", "storage": "fixed", "parser": "FUN_00a66f60", "attachment": "FUN_00a643d0"},
    "FixedQuatf": {"value_type": "quat", "storage": "fixed", "parser": "FUN_00a66f00", "attachment": "FUN_00a64540"},
    "FixedEulerf": {
        "value_type": "euler3",
        "storage": "fixed",
        "parser": "FUN_00a66f60",
        "attachment": "FUN_00a643d0",
        "conversion": "euler3_to_quaternion",
        "conversion_status": "runtime converter is known; axis/order convention remains unresolved",
    },
    "Fixedf32": {"value_type": "f32", "storage": "fixed", "parser": "FUN_00a66fa0", "attachment": "FUN_00a65950"},
}

USAGE_TARGETS = {0: "translation", 1: "rotation", 2: "scale", 3: "weight"}

DEFAULT_NODE_TRANSFORM = {
    "translation": [0.0, 0.0, 0.0],
    "rotation": [1.0, 0.0, 0.0, 0.0],
    "scale": [1.0, 1.0, 1.0],
}


def float_from_hex_word(word: int | str) -> float:
    """Interpret the XML runtime's %08X payload as an IEEE-754 bit-pattern."""
    value = int(word, 16) if isinstance(word, str) else int(word)
    return struct.unpack("<f", struct.pack("<I", value & 0xFFFFFFFF))[0]


def hex_word_from_float(value: float) -> str:
    """Return the exact 32-bit representation expected by the XML reader."""
    raw = struct.unpack("<I", struct.pack("<f", float(value)))[0]
    return f"{raw:08X}"


def usage_name(usage: int | str) -> str:
    if isinstance(usage, str):
        normalized = usage.strip().lower()
        if normalized.isdigit():
            usage = int(normalized)
        else:
            if normalized in {"translation", "rotation", "scale", "weight"}:
                return normalized
            raise ValueError(f"unknown TRACK usage {usage!r}")
    try:
        return USAGE_TARGETS[int(usage)]
    except KeyError as exc:
        raise ValueError(f"unknown TRACK usage code {usage!r}") from exc


def track_form(form: str) -> dict[str, Any]:
    try:
        spec = TRACK_FORMS[form]
    except KeyError as exc:
        raise ValueError(f"unknown TRACK form {form!r}") from exc
    return {"format": "SHIFT.AnimationTrackForm/1", "name": form, **spec}


def validate_track_binding(
    usage: int | str,
    form: str,
    *,
    node_name: str | None = None,
    existing_slots: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Reconstruct the attachment rules enforced by the recovered runtime."""
    target = usage_name(usage)
    spec = track_form(form)
    value_type = spec["value_type"]
    reasons: list[str] = []
    accepted = True

    if value_type == "vec3":
        if target == "rotation":
            accepted = False
            reasons.append("Vec3f cannot attach to rotation")
        elif target not in {"translation", "scale"}:
            accepted = False
            reasons.append(f"Vec3f attachment to {target} is not proven by the recovered node attachers")
    elif value_type == "quat":
        if target != "rotation":
            accepted = False
            reasons.append(f"Quatf cannot attach to {target}")
    elif value_type == "f32":
        if target != "weight":
            accepted = False
            reasons.append(f"f32 cannot attach to {target}")
    elif value_type == "euler3":
        if target not in {"translation", "scale"}:
            accepted = False
            reasons.append(f"Euler3 fixed track cannot attach to {target}")
    else:
        accepted = False
        reasons.append(f"unsupported runtime value type {value_type!r}")

    slots = existing_slots or {}
    if accepted and target in {"translation", "rotation", "scale"} and slots.get(target):
        accepted = False
        reasons.append(f"{target} track already exists")

    return {
        "format": FORMAT,
        "version": 1,
        "accepted": accepted,
        "usage": {
            "code": int(usage) if isinstance(usage, int) or (isinstance(usage, str) and usage.isdigit()) else None,
            "target": target,
        },
        "form": spec,
        "node_name": node_name,
        "existing_slots": dict(slots),
        "blocking_reasons": reasons,
        "evidence": {
            "usage_parser": "FUN_00a67540",
            "slot_attachers": {
                "vec3": "FUN_00a63810/FUN_00a63e70/FUN_00a643d0",
                "quat": "FUN_00a63bd0/FUN_00a64190/FUN_00a64540",
                "f32": "FUN_00a657b0/FUN_00a65820/FUN_00a65950",
            },
        },
    }


def build_track_contract(
    *,
    name: str,
    usage: int | str,
    form: str,
    duration: float = 0.0,
    node_name: str | None = None,
    sample_interval: float | None = None,
    values: list[Any] | None = None,
    keys: list[dict[str, Any]] | None = None,
    fixed_value: Any | None = None,
) -> dict[str, Any]:
    binding = validate_track_binding(usage, form, node_name=node_name)
    return {
        "format": FORMAT,
        "version": 1,
        "name": name,
        "usage": binding["usage"],
        "form": binding["form"],
        "duration": float(duration),
        "node_name": node_name,
        "sample_interval": sample_interval,
        "values": values,
        "keys": keys,
        "fixed_value": fixed_value,
        "binding": binding,
        "source_encoding": {
            "float_attributes": "XML decimal attributes when parsed through FUN_0063d460",
            "vector_values": "%08X bit-pattern words for vec3f/quatf child values",
            "value_word_size": 4,
        },
    }


def base_transform_defaults() -> dict[str, Any]:
    """Return the defaults established by FUN_00a670b0."""
    return {
        "format": "SHIFT.AnimationNodeBaseTransform/1",
        "translation": list(DEFAULT_NODE_TRANSFORM["translation"]),
        "rotation": list(DEFAULT_NODE_TRANSFORM["rotation"]),
        "scale": list(DEFAULT_NODE_TRANSFORM["scale"]),
        "source_function": "FUN_00a670b0",
    }


def validate_animation_node_tree(node_names: list[str], *, expected_count: int | None = None) -> dict[str, Any]:
    unique: list[str] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    for name in node_names:
        if name in seen:
            duplicates.append(name)
        else:
            seen.add(name)
            unique.append(name)

    reasons: list[str] = []
    if expected_count is not None and len(unique) != expected_count:
        reasons.append(f"expected {expected_count} nodes but only {len(unique)} were possible to add")
    if duplicates:
        reasons.append("duplicate animation node names")

    return {
        "format": "SHIFT.AnimationNodeTreeValidation/1",
        "ready": not reasons,
        "input_count": len(node_names),
        "unique_count": len(unique),
        "duplicates": duplicates,
        "expected_count": expected_count,
        "blocking_reasons": reasons,
        "evidence": {"tree_build": "FUN_00a64d90", "name_mapping": "FUN_00a64630"},
    }


def duration_compatibility(durations: list[float], *, tolerance: float = 0.001) -> dict[str, Any]:
    if not durations:
        return {
            "format": "SHIFT.AnimationDurationCompatibility/1",
            "compatible": True,
            "durations": [],
            "max_delta": 0.0,
            "tolerance": tolerance,
        }
    anchor = float(durations[0])
    deltas = [abs(float(value) - anchor) for value in durations[1:]]
    max_delta = max(deltas, default=0.0)
    return {
        "format": "SHIFT.AnimationDurationCompatibility/1",
        "compatible": max_delta <= tolerance,
        "durations": [float(x) for x in durations],
        "max_delta": max_delta,
        "tolerance": tolerance,
        "comparison": "absolute difference <= source tolerance",
        "evidence": "FUN_00a64be0",
    }


def summarize_track_forms(tracks: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"sampled": 0, "keyed": 0, "fixed": 0}
    value_types: dict[str, int] = {}
    usages: dict[str, int] = {}
    unknown: list[str] = []
    for track in tracks:
        form = str(track.get("form") or "")
        spec = TRACK_FORMS.get(form)
        if spec is None:
            unknown.append(form)
            continue
        counts[spec["storage"]] += 1
        value_types[spec["value_type"]] = value_types.get(spec["value_type"], 0) + 1
        target = usage_name(track.get("usage", 0))
        usages[target] = usages.get(target, 0) + 1
    return {
        "format": "SHIFT.AnimationTrackFormSummary/1",
        "form_counts": counts,
        "value_type_counts": value_types,
        "usage_counts": usages,
        "unknown_forms": unknown,
        "binary_channel_ids_not_assumed_equal": True,
    }
