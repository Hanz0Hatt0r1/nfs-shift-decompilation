"""Extract draw-local evidence for target SHIFT D3D9 pixel shaders.

This stage is intentionally conservative. It reconstructs capture-local shader,
buffer, texture and float-constant state at target draws without promoting any
observation to retail resource, primitive, scene-instance or FXO-permutation
identity.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from d3d9_raw_capture_audit import resolve_input_path
from d3d9_target_draw_signatures import (
    _canonical_hash,
    _lookup,
    _ptr,
    _sha_bytes_hex,
    _target_families,
)

_SHADER_DIR = Path(__file__).resolve().parents[1] / "shader"
if str(_SHADER_DIR) not in sys.path:
    sys.path.insert(0, str(_SHADER_DIR))

from shader_ir import parse_shader_blobs

FORMAT = "SHIFT.D3D9TargetDrawLocalEvidence/1"
_FLOAT_REGISTER_SET = 2
_SAMPLER_REGISTER_SET = 3
_TRANSFORM_NAME_RE = re.compile(r"(?:world|model|object|instance)", re.IGNORECASE)


def _shader_reflection(
    row: Mapping[str, Any],
    *,
    stage: str,
) -> dict[str, Any]:
    raw = row.get("bytes_hex")
    if not isinstance(raw, str) or not raw or len(raw) % 2:
        return {
            "status": "unavailable",
            "float_constants": [],
            "samplers": [],
        }
    try:
        payload = bytes.fromhex(raw)
    except ValueError:
        return {
            "status": "unavailable",
            "float_constants": [],
            "samplers": [],
        }
    try:
        blobs = parse_shader_blobs(payload)
    except Exception:
        return {
            "status": "error",
            "float_constants": [],
            "samplers": [],
        }

    stage_blobs = [blob for blob in blobs if blob.stage == stage]
    if not stage_blobs:
        return {
            "status": "unavailable",
            "float_constants": [],
            "samplers": [],
        }

    ctab_observed = any(
        getattr(blob, "ctab_offset", None) is not None
        or bool(blob.ctab_constants)
        or bool(blob.ctab_samplers)
        for blob in stage_blobs
    )
    if not ctab_observed:
        return {
            "status": "unavailable",
            "float_constants": [],
            "samplers": [],
        }

    float_constants: dict[tuple[str, int, int], dict[str, Any]] = {}
    samplers: dict[tuple[str, int, int], dict[str, Any]] = {}
    for blob in stage_blobs:
        for source in blob.ctab_constants or []:
            if not isinstance(source, Mapping):
                continue
            try:
                register_set = int(source.get("register_set"))
                register_index = int(source.get("register_index"))
                register_count = int(source.get("register_count"))
            except (TypeError, ValueError):
                continue
            if register_index < 0 or register_count <= 0:
                continue
            name = str(source.get("name") or "")
            if register_set == _FLOAT_REGISTER_SET:
                key = (name, register_index, register_count)
                float_constants[key] = {
                    "name": name or None,
                    "register_index": register_index,
                    "register_count": register_count,
                }
            elif register_set == _SAMPLER_REGISTER_SET:
                key = (name, register_index, register_count)
                samplers[key] = {
                    "name": name or None,
                    "register": register_index,
                    "count": register_count,
                }

        for source in blob.ctab_samplers or []:
            if not isinstance(source, Mapping):
                continue
            try:
                register_index = int(source.get("register"))
                register_count = int(source.get("count", 1))
            except (TypeError, ValueError):
                continue
            if register_index < 0 or register_count <= 0:
                continue
            name = str(source.get("name") or "")
            key = (name, register_index, register_count)
            samplers[key] = {
                "name": name or None,
                "register": register_index,
                "count": register_count,
            }

    return {
        "status": "reflected",
        "float_constants": [
            float_constants[key] for key in sorted(
                float_constants,
                key=lambda item: (item[1], item[2], item[0]),
            )
        ],
        "samplers": [
            samplers[key] for key in sorted(
                samplers,
                key=lambda item: (item[1], item[2], item[0]),
            )
        ],
    }


def _new_constant_state() -> dict[str, Any]:
    return {
        "values": {},
        "write_event_index": {},
        "write_frame": {},
    }


def _new_device_state() -> dict[str, Any]:
    return {
        "vertex_shader_ptr": None,
        "pixel_shader_ptr": None,
        "declaration_ptr": None,
        "streams": {},
        "index_buffer_ptr": None,
        "textures": {},
        "vertex_constants": _new_constant_state(),
        "pixel_constants": _new_constant_state(),
    }


def _update_constant_state(
    state: dict[str, Any],
    row: Mapping[str, Any],
) -> bool:
    start = row.get("start_register")
    count = row.get("vector4f_count")
    values = row.get("values")
    if (
        not isinstance(start, int)
        or start < 0
        or not isinstance(count, int)
        or count <= 0
        or not isinstance(values, list)
        or len(values) < count * 4
    ):
        return False

    normalized: list[float] = []
    for value in values[: count * 4]:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        number = float(value)
        if not math.isfinite(number):
            return False
        normalized.append(number)

    event_index = row.get("event_index")
    frame = row.get("frame")
    for offset in range(count):
        register = start + offset
        base = offset * 4
        state["values"][register] = normalized[base : base + 4]
        state["write_event_index"][register] = (
            event_index if isinstance(event_index, int) else None
        )
        state["write_frame"][register] = frame if isinstance(frame, int) else None
    return True


def _constant_snapshot(
    reflection: Mapping[str, Any] | None,
    state: Mapping[str, Any],
) -> dict[str, Any]:
    reflection = reflection or {}
    reflection_status = str(reflection.get("status") or "unavailable")
    if reflection_status != "reflected":
        return {
            "status": "reflection-unavailable",
            "complete": False,
            "variable_count": 0,
            "missing_registers": [],
            "signature_sha256": None,
            "provenance_sha256": None,
            "transform_signature_sha256": None,
            "transform_name_match_count": 0,
            "variables": [],
        }

    values = state.get("values") or {}
    event_indexes = state.get("write_event_index") or {}
    frames = state.get("write_frame") or {}
    variables: list[dict[str, Any]] = []
    signature_variables: list[dict[str, Any]] = []
    provenance_variables: list[dict[str, Any]] = []
    missing_registers: set[int] = set()
    transform_signature_variables: list[dict[str, Any]] = []
    transform_name_match_count = 0
    transform_complete = True

    for source in reflection.get("float_constants") or []:
        if not isinstance(source, Mapping):
            continue
        register_index = source.get("register_index")
        register_count = source.get("register_count")
        if not isinstance(register_index, int) or not isinstance(register_count, int):
            continue
        name = source.get("name")
        name_text = str(name or "")
        registers: list[dict[str, Any]] = []
        signature_registers: list[dict[str, Any]] = []
        variable_complete = True
        for register in range(register_index, register_index + register_count):
            current = values.get(register)
            if current is None:
                variable_complete = False
                missing_registers.add(register)
                current_values = None
            else:
                current_values = list(current)
            registers.append({
                "register": register,
                "values": current_values,
                "last_write_event_index": event_indexes.get(register),
                "last_write_frame": frames.get(register),
            })
            signature_registers.append({
                "register": register,
                "values": current_values,
            })

        variable = {
            "name": name,
            "register_index": register_index,
            "register_count": register_count,
            "complete": variable_complete,
            "registers": registers,
        }
        variables.append(variable)
        signature_variable = {
            "name": name,
            "register_index": register_index,
            "register_count": register_count,
            "registers": signature_registers,
        }
        signature_variables.append(signature_variable)
        provenance_variables.append(variable)

        if _TRANSFORM_NAME_RE.search(name_text):
            transform_name_match_count += 1
            if variable_complete:
                transform_signature_variables.append(signature_variable)
            else:
                transform_complete = False

    complete = not missing_registers
    signature_payload = {"variables": signature_variables}
    provenance_payload = {"variables": provenance_variables}
    transform_signature = None
    if transform_name_match_count and transform_complete:
        transform_signature = _canonical_hash({
            "variables": transform_signature_variables,
        })

    return {
        "status": "complete" if complete else "incomplete",
        "complete": complete,
        "variable_count": len(variables),
        "missing_registers": sorted(missing_registers),
        "signature_sha256": _canonical_hash(signature_payload),
        "provenance_sha256": _canonical_hash(provenance_payload),
        "transform_signature_sha256": transform_signature,
        "transform_name_match_count": transform_name_match_count,
        "variables": variables,
    }


def _creation_event_index(
    table: Mapping[tuple[str, str], Mapping[str, Any]],
    device: str,
    pointer: str | None,
) -> int | None:
    row = _lookup(table, device, pointer)
    if not isinstance(row, Mapping):
        return None
    value = row.get("creation_event_index")
    return int(value) if isinstance(value, int) else None


def _portable_resource_identity(row: Mapping[str, Any] | None) -> dict[str, Any]:
    row = row or {}
    path = row.get("resource_path")
    digest = row.get("resource_sha256")
    return {
        "resource_path": path if isinstance(path, str) and path else None,
        "resource_sha256": (
            digest if isinstance(digest, str) and digest else None
        ),
        "resource_signature": row.get("resource_signature"),
    }


def _stream_binding(
    table: Mapping[tuple[str, str], Mapping[str, Any]],
    device: str,
    stream: int,
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    pointer = binding.get("pointer")
    creation = _lookup(table, device, pointer) or {}
    return {
        "stream": stream,
        "vertex_buffer_ptr": pointer,
        "vertex_buffer_creation_event_index": _creation_event_index(
            table,
            device,
            pointer,
        ),
        "offset_in_bytes": binding.get("offset_in_bytes"),
        "stride": binding.get("stride"),
        "descriptor": {
            key: creation.get(key)
            for key in ("length", "usage", "fvf", "pool")
        },
        "portable_resource_identity": _portable_resource_identity(creation),
    }


def _sampler_bindings(
    reflection: Mapping[str, Any] | None,
    state: Mapping[str, Any],
    textures: Mapping[tuple[str, str], Mapping[str, Any]],
    device: str,
) -> tuple[list[dict[str, Any]], int, int]:
    reflection = reflection or {}
    reflection_status = str(reflection.get("status") or "unavailable")
    stages: list[tuple[int, str | None]] = []
    if reflection_status == "reflected":
        for sampler in reflection.get("samplers") or []:
            if not isinstance(sampler, Mapping):
                continue
            register = sampler.get("register")
            count = sampler.get("count", 1)
            if not isinstance(register, int) or not isinstance(count, int):
                continue
            name = sampler.get("name")
            for offset in range(max(0, count)):
                item_name = name
                if count > 1 and name:
                    item_name = f"{name}[{offset}]"
                stages.append((register + offset, item_name))
    else:
        stages = [
            (stage, None)
            for stage in sorted((state.get("textures") or {}).keys())
            if isinstance(stage, int)
        ]

    result: list[dict[str, Any]] = []
    missing_binding_count = 0
    missing_creation_count = 0
    seen: set[int] = set()
    for stage, name in stages:
        if stage in seen:
            continue
        seen.add(stage)
        binding = (state.get("textures") or {}).get(stage) or {}
        pointer = binding.get("pointer")
        creation = _lookup(textures, device, pointer) or {}
        if pointer is None:
            missing_binding_count += 1
        creation_index = _creation_event_index(textures, device, pointer)
        if pointer is not None and creation_index is None:
            missing_creation_count += 1
        descriptor = dict(creation)
        descriptor.update(binding.get("descriptor") or {})
        result.append({
            "stage": stage,
            "sampler_name": name,
            "texture_ptr": pointer,
            "texture_creation_event_index": creation_index,
            "descriptor": {
                key: descriptor.get(key)
                for key in (
                    "resource_type_name",
                    "width",
                    "height",
                    "depth",
                    "edge_length",
                    "format",
                    "pool",
                    "level_count",
                    "levels",
                    "usage",
                )
            },
            "portable_resource_identity": _portable_resource_identity(descriptor),
            "snapshot_status": descriptor.get("snapshot_status"),
            "snapshot_paths": list(descriptor.get("snapshot_paths") or []),
        })
    return result, missing_binding_count, missing_creation_count


def _capture_requirement(
    observed_count: int,
    *,
    required_for: str,
    missing_event: str,
) -> dict[str, Any]:
    return {
        "status": "observed" if observed_count > 0 else "missing",
        "observed_count": observed_count,
        "required_for": required_for,
        "minimal_missing_event": missing_event if observed_count == 0 else None,
    }


def _finalize_geometry_groups(
    groups: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for digest, source in groups.items():
        row = dict(source)
        signals: list[str] = []
        instance_ids = row.pop("_instance_stream_ids")
        shader_pair_ids = row.pop("_shader_pair_ids")
        texture_ids = row.pop("_texture_ids")
        vertex_constant_ids = row.pop("_vertex_constant_ids")
        pixel_constant_ids = row.pop("_pixel_constant_ids")
        transform_ids = row.pop("_transform_ids")
        evidence_ids = row.pop("_evidence_ids")

        if len(instance_ids) > 1:
            signals.append("instance-stream")
        if len(transform_ids) > 1:
            signals.append("name-suggested-transform-constants")
        if len(vertex_constant_ids) > 1:
            signals.append("vertex-float-constants")
        if len(pixel_constant_ids) > 1:
            signals.append("pixel-float-constants")
        if len(texture_ids) > 1:
            signals.append("texture-object-state")
        if len(shader_pair_ids) > 1:
            signals.append("shader-pair")

        draw_count = int(row.get("draw_count") or 0)
        incomplete_count = int(row.get("incomplete_draw_count") or 0)
        if draw_count <= 1:
            status = "single-observation"
        elif signals:
            status = "distinguished-by-existing-capture"
        elif incomplete_count:
            status = "insufficient-capture-local-state"
        else:
            status = "not-distinguished-by-existing-capture"

        row.update({
            "geometry_identity_sha256": digest,
            "disambiguation_status": status,
            "disambiguation_signals": signals,
            "unique_instance_stream_identity_count": len(instance_ids),
            "unique_shader_pair_count": len(shader_pair_ids),
            "unique_texture_identity_count": len(texture_ids),
            "unique_vertex_constant_signature_count": len(vertex_constant_ids),
            "unique_pixel_constant_signature_count": len(pixel_constant_ids),
            "unique_transform_signature_count": len(transform_ids),
            "unique_draw_evidence_count": len(evidence_ids),
        })
        result.append(row)

    result.sort(
        key=lambda row: (
            -int(row.get("draw_count") or 0),
            str(row.get("geometry_identity_sha256") or ""),
        )
    )
    return result


def build_target_draw_local_evidence(
    lines: Iterable[str],
    *,
    target_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    target_hashes, target_families = _target_families(target_inventory)
    if not target_hashes:
        raise ValueError("target inventory contains no pixel shader hashes")

    shaders: dict[tuple[str, str], dict[str, Any]] = {}
    declarations: dict[tuple[str, str], dict[str, Any]] = {}
    vertex_buffers: dict[tuple[str, str], dict[str, Any]] = {}
    index_buffers: dict[tuple[str, str], dict[str, Any]] = {}
    textures: dict[tuple[str, str], dict[str, Any]] = {}
    states: dict[str, dict[str, Any]] = defaultdict(_new_device_state)

    event_counts: Counter[str] = Counter()
    gap_counts: Counter[str] = Counter()
    target_draw_counts: Counter[str] = Counter()
    source_line_count = 0
    invalid_json_count = 0
    non_object_count = 0
    malformed_constant_write_count = 0
    resource_identity_pair_count = 0
    captured_texture_snapshot_count = 0

    draws: list[dict[str, Any]] = []
    geometry_groups: dict[str, dict[str, Any]] = {}
    shader_pair_ids: set[str] = set()
    shader_object_pair_ids: set[str] = set()
    geometry_ids: set[str] = set()
    instance_stream_ids: set[str] = set()
    texture_ids: set[str] = set()
    vertex_constant_ids: set[str] = set()
    pixel_constant_ids: set[str] = set()
    transform_ids: set[str] = set()
    strong_draw_count = 0

    for raw_line in lines:
        text = raw_line.strip()
        if not text:
            continue
        source_line_count += 1
        try:
            row = json.loads(text)
        except json.JSONDecodeError:
            invalid_json_count += 1
            continue
        if not isinstance(row, dict):
            non_object_count += 1
            continue

        event = str(row.get("event") or "<missing>")
        event_counts[event] += 1
        device = _ptr(row.get("device_ptr")) or ""
        state = states[device]
        event_index = row.get("event_index")
        creation_index = event_index if isinstance(event_index, int) else None

        if (
            isinstance(row.get("resource_path"), str)
            and row.get("resource_path")
            and isinstance(row.get("resource_sha256"), str)
            and row.get("resource_sha256")
        ):
            resource_identity_pair_count += 1
        if (
            event == "set_texture"
            and row.get("snapshot_status") == "captured"
            and bool(row.get("snapshot_paths"))
        ):
            captured_texture_snapshot_count += 1

        if event in {"reset", "device_reset"}:
            states[device] = _new_device_state()
            continue

        if event in {"create_vertex_shader", "create_pixel_shader"}:
            pointer = _ptr(row.get("shader_ptr"))
            digest = _sha_bytes_hex(row)
            if pointer and digest:
                stage = "vertex" if event == "create_vertex_shader" else "pixel"
                shaders[(device, pointer)] = {
                    "sha256": digest,
                    "stage": stage,
                    "creation_event_index": creation_index,
                    "reflection": _shader_reflection(row, stage=stage),
                }
            continue

        if event == "create_vertex_declaration":
            pointer = _ptr(row.get("declaration_ptr"))
            if pointer:
                declarations[(device, pointer)] = {
                    "sha256": _sha_bytes_hex(row),
                    "creation_event_index": creation_index,
                }
            continue

        if event == "create_vertex_buffer":
            pointer = _ptr(row.get("vertex_buffer_ptr"))
            if pointer:
                vertex_buffers[(device, pointer)] = {
                    "length": row.get("length"),
                    "usage": row.get("usage"),
                    "fvf": row.get("fvf"),
                    "pool": row.get("pool"),
                    "creation_event_index": creation_index,
                    **_portable_resource_identity(row),
                }
            continue

        if event == "create_index_buffer":
            pointer = _ptr(row.get("index_buffer_ptr"))
            if pointer:
                index_buffers[(device, pointer)] = {
                    "length": row.get("length"),
                    "usage": row.get("usage"),
                    "format": row.get("format"),
                    "pool": row.get("pool"),
                    "creation_event_index": creation_index,
                    **_portable_resource_identity(row),
                }
            continue

        if event in {"create_texture", "create_cube_texture"}:
            pointer = _ptr(row.get("texture_ptr"))
            if pointer:
                texture = {
                    "resource_type_name": (
                        "cube_texture"
                        if event == "create_cube_texture"
                        else "texture2d"
                    ),
                    "usage": row.get("usage"),
                    "format": row.get("format"),
                    "pool": row.get("pool"),
                    "levels": row.get("levels"),
                    "level_count": row.get("level_count", row.get("levels")),
                    "creation_event_index": creation_index,
                    **_portable_resource_identity(row),
                }
                if event == "create_cube_texture":
                    texture["edge_length"] = row.get("edge_length")
                    texture["width"] = row.get("edge_length")
                    texture["height"] = row.get("edge_length")
                else:
                    texture["width"] = row.get("width")
                    texture["height"] = row.get("height")
                textures[(device, pointer)] = texture
            continue

        if event == "set_vertex_shader":
            state["vertex_shader_ptr"] = _ptr(row.get("shader_ptr"))
            continue
        if event == "set_pixel_shader":
            state["pixel_shader_ptr"] = _ptr(row.get("shader_ptr"))
            continue
        if event == "set_vertex_declaration":
            state["declaration_ptr"] = _ptr(row.get("declaration_ptr"))
            continue
        if event == "set_stream_source":
            stream = row.get("stream")
            if isinstance(stream, int):
                pointer = _ptr(row.get("vertex_buffer_ptr"))
                if pointer is None:
                    state["streams"].pop(stream, None)
                else:
                    state["streams"][stream] = {
                        "pointer": pointer,
                        "offset_in_bytes": row.get("offset_in_bytes"),
                        "stride": row.get("stride"),
                    }
            continue
        if event == "set_indices":
            state["index_buffer_ptr"] = _ptr(row.get("index_buffer_ptr"))
            continue
        if event == "set_texture":
            stage = row.get("stage")
            if isinstance(stage, int):
                pointer = _ptr(row.get("texture_ptr"))
                if pointer is None:
                    state["textures"].pop(stage, None)
                else:
                    descriptor = dict(_lookup(textures, device, pointer) or {})
                    for key in (
                        "resource_type_name",
                        "width",
                        "height",
                        "depth",
                        "edge_length",
                        "format",
                        "pool",
                        "level_count",
                        "levels",
                        "usage",
                        "resource_path",
                        "resource_sha256",
                        "resource_signature",
                        "snapshot_status",
                        "snapshot_paths",
                    ):
                        if row.get(key) is not None:
                            descriptor[key] = row.get(key)
                    state["textures"][stage] = {
                        "pointer": pointer,
                        "descriptor": descriptor,
                    }
            continue
        if event == "set_vertex_shader_constant_f":
            if not _update_constant_state(state["vertex_constants"], row):
                malformed_constant_write_count += 1
            continue
        if event == "set_pixel_shader_constant_f":
            if not _update_constant_state(state["pixel_constants"], row):
                malformed_constant_write_count += 1
            continue
        if event != "draw_indexed_primitive":
            continue

        pixel_shader = _lookup(
            shaders,
            device,
            state.get("pixel_shader_ptr"),
        )
        pixel_sha = (
            pixel_shader.get("sha256")
            if isinstance(pixel_shader, Mapping)
            else None
        )
        if pixel_sha not in target_hashes:
            continue
        target_draw_counts[str(pixel_sha)] += 1

        vertex_shader = _lookup(
            shaders,
            device,
            state.get("vertex_shader_ptr"),
        )
        vertex_sha = (
            vertex_shader.get("sha256")
            if isinstance(vertex_shader, Mapping)
            else None
        )
        vertex_pointer = state.get("vertex_shader_ptr")
        pixel_pointer = state.get("pixel_shader_ptr")
        shader_pair = {
            "vertex_shader_sha256": vertex_sha,
            "pixel_shader_sha256": pixel_sha,
        }
        shader_pair_sha = (
            _canonical_hash(shader_pair) if vertex_sha and pixel_sha else None
        )
        if shader_pair_sha:
            shader_pair_ids.add(shader_pair_sha)
        shader_objects = {
            "vertex_shader_ptr": vertex_pointer,
            "vertex_shader_creation_event_index": _creation_event_index(
                shaders,
                device,
                vertex_pointer,
            ),
            "pixel_shader_ptr": pixel_pointer,
            "pixel_shader_creation_event_index": _creation_event_index(
                shaders,
                device,
                pixel_pointer,
            ),
        }
        shader_object_pair_sha = _canonical_hash(shader_objects)
        shader_object_pair_ids.add(shader_object_pair_sha)

        declaration_pointer = state.get("declaration_ptr")
        declaration = _lookup(declarations, device, declaration_pointer) or {}
        declaration_identity = {
            "declaration_ptr": declaration_pointer,
            "declaration_creation_event_index": _creation_event_index(
                declarations,
                device,
                declaration_pointer,
            ),
            "declaration_sha256": declaration.get("sha256"),
        }

        streams = [
            _stream_binding(vertex_buffers, device, stream, binding)
            for stream, binding in sorted(state["streams"].items())
        ]
        stream0 = next(
            (binding for binding in streams if binding.get("stream") == 0),
            {},
        )
        instance_streams = [
            binding for binding in streams if binding.get("stream") != 0
        ]
        instance_stream_sha = _canonical_hash({"streams": instance_streams})
        instance_stream_ids.add(instance_stream_sha)

        index_pointer = state.get("index_buffer_ptr")
        index_creation = _lookup(index_buffers, device, index_pointer) or {}
        index_binding = {
            "index_buffer_ptr": index_pointer,
            "index_buffer_creation_event_index": _creation_event_index(
                index_buffers,
                device,
                index_pointer,
            ),
            "descriptor": {
                key: index_creation.get(key)
                for key in ("length", "usage", "format", "pool")
            },
            "portable_resource_identity": _portable_resource_identity(
                index_creation
            ),
        }
        draw_range = {
            "primitive_type": row.get("primitive_type"),
            "base_vertex_index": row.get("base_vertex_index"),
            "min_vertex_index": row.get("min_vertex_index"),
            "num_vertices": row.get("num_vertices"),
            "start_index": row.get("start_index"),
            "primitive_count": row.get("primitive_count"),
        }
        geometry_identity = {
            "device_ptr": device or None,
            "stream0_vertex_buffer_ptr": stream0.get("vertex_buffer_ptr"),
            "stream0_vertex_buffer_creation_event_index": stream0.get(
                "vertex_buffer_creation_event_index"
            ),
            "index_buffer_ptr": index_pointer,
            "index_buffer_creation_event_index": index_binding.get(
                "index_buffer_creation_event_index"
            ),
            "draw_range": {
                key: draw_range.get(key)
                for key in (
                    "primitive_type",
                    "base_vertex_index",
                    "start_index",
                    "primitive_count",
                )
            },
        }
        geometry_sha = _canonical_hash(geometry_identity)
        geometry_ids.add(geometry_sha)

        vertex_reflection = (
            vertex_shader.get("reflection")
            if isinstance(vertex_shader, Mapping)
            else None
        )
        pixel_reflection = (
            pixel_shader.get("reflection")
            if isinstance(pixel_shader, Mapping)
            else None
        )
        vertex_constants = _constant_snapshot(
            vertex_reflection,
            state["vertex_constants"],
        )
        pixel_constants = _constant_snapshot(
            pixel_reflection,
            state["pixel_constants"],
        )
        if vertex_constants.get("signature_sha256"):
            vertex_constant_ids.add(str(vertex_constants["signature_sha256"]))
        if pixel_constants.get("signature_sha256"):
            pixel_constant_ids.add(str(pixel_constants["signature_sha256"]))
        for snapshot in (vertex_constants, pixel_constants):
            transform_sha = snapshot.get("transform_signature_sha256")
            if transform_sha:
                transform_ids.add(str(transform_sha))

        sampler_bindings, missing_sampler_bindings, missing_texture_creations = (
            _sampler_bindings(
                pixel_reflection,
                state,
                textures,
                device,
            )
        )
        texture_identity = {
            "reflection_status": (
                pixel_reflection.get("status")
                if isinstance(pixel_reflection, Mapping)
                else "unavailable"
            ),
            "samplers": [
                {
                    "stage": binding.get("stage"),
                    "texture_ptr": binding.get("texture_ptr"),
                    "texture_creation_event_index": binding.get(
                        "texture_creation_event_index"
                    ),
                }
                for binding in sampler_bindings
            ],
        }
        texture_sha = _canonical_hash(texture_identity)
        texture_ids.add(texture_sha)

        missing: list[str] = []
        if not vertex_sha:
            missing.append("vertex-shader-creation-unresolved")
        if not pixel_sha:
            missing.append("pixel-shader-creation-unresolved")
        if stream0.get("vertex_buffer_ptr") is None:
            missing.append("stream0-vertex-buffer-unbound")
        elif stream0.get("vertex_buffer_creation_event_index") is None:
            missing.append("stream0-vertex-buffer-creation-unresolved")
        if index_pointer is None:
            missing.append("index-buffer-unbound")
        elif index_binding.get("index_buffer_creation_event_index") is None:
            missing.append("index-buffer-creation-unresolved")
        if vertex_constants.get("status") == "incomplete":
            missing.append("vertex-reflected-float-constants-incomplete")
        if pixel_constants.get("status") == "incomplete":
            missing.append("pixel-reflected-float-constants-incomplete")
        if missing_sampler_bindings:
            missing.append("reflected-sampler-unbound")
        if missing_texture_creations:
            missing.append("texture-creation-unresolved")
        gap_counts.update(missing)

        strong = not missing
        if strong:
            strong_draw_count += 1
        frame = row.get("frame")
        frame_value = frame if isinstance(frame, int) else None
        draw_event_index = row.get("event_index")
        draw_event_index = (
            draw_event_index if isinstance(draw_event_index, int) else None
        )
        evidence_payload = {
            "shader_pair_sha256": shader_pair_sha,
            "shader_object_pair_sha256": shader_object_pair_sha,
            "geometry_identity_sha256": geometry_sha,
            "instance_stream_identity_sha256": instance_stream_sha,
            "texture_identity_sha256": texture_sha,
            "vertex_constant_signature_sha256": vertex_constants.get(
                "signature_sha256"
            ),
            "pixel_constant_signature_sha256": pixel_constants.get(
                "signature_sha256"
            ),
            "vertex_transform_signature_sha256": vertex_constants.get(
                "transform_signature_sha256"
            ),
            "pixel_transform_signature_sha256": pixel_constants.get(
                "transform_signature_sha256"
            ),
        }
        evidence_sha = _canonical_hash(evidence_payload)
        draw_record = {
            "frame": frame_value,
            "event_index": draw_event_index,
            "device_ptr": device or None,
            "families": sorted(target_families.get(str(pixel_sha), set())),
            "classification": (
                "strong-capture-local" if strong else "partial-capture-local"
            ),
            "missing_capture_local_state": missing,
            "shader_pair_sha256": shader_pair_sha,
            "shader_object_pair_sha256": shader_object_pair_sha,
            "shader_pair": shader_pair,
            "shader_objects": shader_objects,
            "declaration": declaration_identity,
            "geometry_identity_sha256": geometry_sha,
            "geometry_identity": geometry_identity,
            "streams": streams,
            "instance_stream_identity_sha256": instance_stream_sha,
            "index_binding": index_binding,
            "draw_range": draw_range,
            "texture_identity_sha256": texture_sha,
            "sampler_bindings": sampler_bindings,
            "vertex_constants": vertex_constants,
            "pixel_constants": pixel_constants,
            "draw_evidence_sha256": evidence_sha,
        }
        draws.append(draw_record)

        group = geometry_groups.get(geometry_sha)
        if group is None:
            group = {
                "geometry_identity": geometry_identity,
                "draw_count": 0,
                "first_frame": frame_value,
                "last_frame": frame_value,
                "incomplete_draw_count": 0,
                "_instance_stream_ids": set(),
                "_shader_pair_ids": set(),
                "_texture_ids": set(),
                "_vertex_constant_ids": set(),
                "_pixel_constant_ids": set(),
                "_transform_ids": set(),
                "_evidence_ids": set(),
            }
            geometry_groups[geometry_sha] = group
        group["draw_count"] += 1
        if not strong:
            group["incomplete_draw_count"] += 1
        if isinstance(frame_value, int):
            if group["first_frame"] is None:
                group["first_frame"] = frame_value
            else:
                group["first_frame"] = min(int(group["first_frame"]), frame_value)
            if group["last_frame"] is None:
                group["last_frame"] = frame_value
            else:
                group["last_frame"] = max(int(group["last_frame"]), frame_value)
        group["_instance_stream_ids"].add(instance_stream_sha)
        if shader_pair_sha:
            group["_shader_pair_ids"].add(shader_pair_sha)
        group["_texture_ids"].add(texture_sha)
        vertex_constant_sha = vertex_constants.get("signature_sha256")
        pixel_constant_sha = pixel_constants.get("signature_sha256")
        if vertex_constant_sha:
            group["_vertex_constant_ids"].add(vertex_constant_sha)
        if pixel_constant_sha:
            group["_pixel_constant_ids"].add(pixel_constant_sha)
        for snapshot in (vertex_constants, pixel_constants):
            transform_sha = snapshot.get("transform_signature_sha256")
            if transform_sha:
                group["_transform_ids"].add(transform_sha)
        group["_evidence_ids"].add(evidence_sha)

    target_draw_count = len(draws)
    groups = _finalize_geometry_groups(geometry_groups)
    repeated_groups = [row for row in groups if int(row.get("draw_count") or 0) > 1]
    distinguished_groups = [
        row
        for row in repeated_groups
        if row.get("disambiguation_status") == "distinguished-by-existing-capture"
    ]

    requirements = {
        "shader_creation_use_identity": _capture_requirement(
            event_counts["create_vertex_shader"] + event_counts["create_pixel_shader"],
            required_for="shader byte identity and creation generation",
            missing_event="create_vertex_shader/create_pixel_shader",
        ),
        "draw_local_vertex_float_constants": _capture_requirement(
            event_counts["set_vertex_shader_constant_f"],
            required_for="draw-local vertex constant reconstruction",
            missing_event="set_vertex_shader_constant_f",
        ),
        "draw_local_pixel_float_constants": _capture_requirement(
            event_counts["set_pixel_shader_constant_f"],
            required_for="draw-local pixel/material constant reconstruction",
            missing_event="set_pixel_shader_constant_f",
        ),
        "buffer_payload": _capture_requirement(
            event_counts["buffer_payload"],
            required_for="exact VB/IB payload equality against static IMB data",
            missing_event="buffer_payload",
        ),
        "resource_path_sha_identity": _capture_requirement(
            resource_identity_pair_count,
            required_for="portable runtime-resource path/SHA attribution",
            missing_event="resource_path + resource_sha256 on one resource event",
        ),
        "texture_snapshots": _capture_requirement(
            captured_texture_snapshot_count,
            required_for="exact captured sampler payload/snapshot correlation",
            missing_event="set_texture snapshot_status=captured + snapshot_paths",
        ),
    }

    return {
        "format": FORMAT,
        "version": 1,
        "status": "observed" if target_draw_count else "not-observed",
        "summary": {
            "source_line_count": source_line_count,
            "invalid_json_count": invalid_json_count,
            "non_object_count": non_object_count,
            "target_hash_count": len(target_hashes),
            "target_draw_hash_count": len(target_draw_counts),
            "target_draw_count": target_draw_count,
            "strong_capture_local_draw_count": strong_draw_count,
            "partial_capture_local_draw_count": target_draw_count - strong_draw_count,
            "unique_shader_pair_count": len(shader_pair_ids),
            "unique_shader_object_pair_count": len(shader_object_pair_ids),
            "unique_geometry_identity_count": len(geometry_ids),
            "unique_instance_stream_identity_count": len(instance_stream_ids),
            "unique_texture_identity_count": len(texture_ids),
            "unique_vertex_constant_signature_count": len(vertex_constant_ids),
            "unique_pixel_constant_signature_count": len(pixel_constant_ids),
            "unique_name_suggested_transform_signature_count": len(transform_ids),
            "repeated_geometry_group_count": len(repeated_groups),
            "distinguished_repeated_geometry_group_count": len(distinguished_groups),
            "malformed_constant_write_count": malformed_constant_write_count,
            "resource_identity_pair_event_count": resource_identity_pair_count,
            "captured_texture_snapshot_event_count": captured_texture_snapshot_count,
        },
        "event_counts": dict(sorted(event_counts.items())),
        "capture_local_gap_counts": dict(sorted(gap_counts.items())),
        "capture_requirements": requirements,
        "geometry_groups": groups,
        "draws": draws,
        "boundary": {
            "target_filter": (
                "draws are selected only when the currently bound pixel shader "
                "resolves to a byte SHA-256 present in the supplied target inventory"
            ),
            "shader_pair": (
                "VS/PS byte hashes are exact for captured shader bytecode; the "
                "pair does not select an FXO permutation without unique runtime proof"
            ),
            "constant_state": (
                "D3D9 float constant registers are reconstructed from observed "
                "Set*ShaderConstantF writes and intersected with CTAB float ranges"
            ),
            "transform_name_matching": (
                "world/model/object/instance CTAB names are a diagnostic label only; "
                "matrix semantics, multiplication order and scene-node identity are "
                "not inferred from the name"
            ),
            "instance_stream_identity": (
                "non-zero stream pointer generation + offset/stride state is "
                "capture-local repeated-instance evidence, not retail instance identity"
            ),
            "texture_identity": (
                "CTAB sampler stages preserve capture-local texture pointer generations; "
                "shared textures do not imply material identity"
            ),
            "strong_capture_local": (
                "all required capture-local shader, stream-0 VB, IB, reflected "
                "constant and sampler bindings resolved for the draw"
            ),
            "retail_resource_identity": "not claimed",
            "retail_primitive_identity": "not claimed",
            "scene_instance_identity": "not claimed",
            "fxo_permutation_selection": "not claimed",
            "render_admission": False,
        },
    }


def build_target_draw_local_evidence_file(
    capture_path: str | Path,
    *,
    target_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    with Path(capture_path).open("r", encoding="utf-8") as handle:
        return build_target_draw_local_evidence(
            handle,
            target_inventory=target_inventory,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_jsonl")
    parser.add_argument("output")
    parser.add_argument("--target-inventory", required=True)
    args = parser.parse_args(argv)

    capture_path = resolve_input_path(args.capture_jsonl)
    inventory_path = resolve_input_path(args.target_inventory)
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if not isinstance(inventory, dict):
        raise ValueError("target inventory must be a JSON object")

    report = build_target_draw_local_evidence_file(
        capture_path,
        target_inventory=inventory,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
