"""Capture-local resource-pointer observations for target SHIFT D3D9 draws.

Phase 613 reconstructs the same stable resource-shape SHA used by
``d3d9_target_draw_signatures.py`` while retaining capture-local COM pointer
identity outside that stable signature.  Pointer values and creation generations
are diagnostic/session-local evidence only; they never become portable resource
identity on their own.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from d3d9_raw_capture_audit import resolve_input_path
from d3d9_target_draw_signatures import (
    FORMAT as TARGET_CATALOG_FORMAT,
    _canonical_hash,
    _lookup,
    _pixel_shader_reflection,
    _ptr,
    _sha_bytes_hex,
    _target_families,
    _texture_shape,
)

FORMAT = "SHIFT.D3D9TargetPointerObservations/1"


def _observe(
    table: dict[str, dict[str, Any]],
    payload: Mapping[str, Any],
    *,
    frame: int | None,
) -> str:
    digest = _canonical_hash(payload)
    row = table.get(digest)
    if row is None:
        row = {
            "identity_sha256": digest,
            "identity": dict(payload),
            "draw_count": 0,
            "first_frame": frame,
            "last_frame": frame,
        }
        table[digest] = row
    row["draw_count"] += 1
    if isinstance(frame, int):
        if row["first_frame"] is None:
            row["first_frame"] = frame
        else:
            row["first_frame"] = min(int(row["first_frame"]), frame)
        if row["last_frame"] is None:
            row["last_frame"] = frame
        else:
            row["last_frame"] = max(int(row["last_frame"]), frame)
    return digest


def _finalize_observations(
    table: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = [dict(row) for row in table.values()]
    rows.sort(
        key=lambda row: (
            -int(row.get("draw_count") or 0),
            str(row.get("identity_sha256") or ""),
        )
    )
    return rows


def _buffer_shape(
    table: Mapping[tuple[str, str], Mapping[str, Any]],
    device: str,
    pointer: str | None,
    *,
    vertex: bool,
) -> dict[str, Any]:
    row = _lookup(table, device, pointer) or {}
    keys = (
        ("length", "usage", "fvf", "pool")
        if vertex
        else ("length", "usage", "format", "pool")
    )
    return {key: row.get(key) for key in keys}


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


def _catalog_alignment(
    observed_rows: Mapping[str, Mapping[str, Any]],
    target_catalog: Mapping[str, Any] | None,
) -> dict[str, Any]:
    observed = set(observed_rows)
    if target_catalog is None:
        return {
            "status": "not-evaluated",
            "expected_resource_shape_count": None,
            "observed_resource_shape_count": len(observed),
            "missing_resource_shape_sha256s": [],
            "extra_resource_shape_sha256s": [],
        }
    if target_catalog.get("format") != TARGET_CATALOG_FORMAT:
        raise ValueError(
            "target catalog must be SHIFT.D3D9TargetDrawSignatureCatalog/1"
        )
    expected = {
        str(row.get("signature_sha256"))
        for row in (target_catalog.get("resource_shape_signatures") or [])
        if isinstance(row, Mapping) and row.get("signature_sha256")
    }
    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    return {
        "status": "exact" if not missing and not extra else "mismatch",
        "expected_resource_shape_count": len(expected),
        "observed_resource_shape_count": len(observed),
        "missing_resource_shape_sha256s": missing,
        "extra_resource_shape_sha256s": extra,
    }


def build_target_pointer_observations(
    lines: Iterable[str],
    *,
    target_inventory: Mapping[str, Any],
    target_catalog: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    target_hashes, target_families = _target_families(target_inventory)
    if not target_hashes:
        raise ValueError("target inventory contains no pixel shader hashes")

    shaders: dict[tuple[str, str], dict[str, Any]] = {}
    declarations: dict[tuple[str, str], dict[str, Any]] = {}
    vertex_buffers: dict[tuple[str, str], dict[str, Any]] = {}
    index_buffers: dict[tuple[str, str], dict[str, Any]] = {}
    textures: dict[tuple[str, str], dict[str, Any]] = {}
    states: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "vertex_shader_ptr": None,
            "pixel_shader_ptr": None,
            "declaration_ptr": None,
            "streams": {},
            "index_buffer_ptr": None,
            "textures": {},
        }
    )

    resource_rows: dict[str, dict[str, Any]] = {}
    global_geometry: dict[str, dict[str, Any]] = {}
    global_material: dict[str, dict[str, Any]] = {}
    global_combined: dict[str, dict[str, Any]] = {}
    target_draw_counts: Counter[str] = Counter()
    source_line_count = 0
    invalid_json_count = 0
    non_object_count = 0
    reflected_target_draw_count = 0
    fallback_texture_state_draw_count = 0
    complete_geometry_pointer_draw_count = 0

    for raw_line in lines:
        if not raw_line.strip():
            continue
        source_line_count += 1
        try:
            row = json.loads(raw_line)
        except json.JSONDecodeError:
            invalid_json_count += 1
            continue
        if not isinstance(row, dict):
            non_object_count += 1
            continue

        event = str(row.get("event") or "<missing>")
        device = _ptr(row.get("device_ptr")) or ""
        state = states[device]
        event_index = row.get("event_index")
        creation_index = event_index if isinstance(event_index, int) else None

        if event in {"create_vertex_shader", "create_pixel_shader"}:
            pointer = _ptr(row.get("shader_ptr"))
            digest = _sha_bytes_hex(row)
            if pointer and digest:
                shader = {
                    "sha256": digest,
                    "stage": (
                        "vertex"
                        if event == "create_vertex_shader"
                        else "pixel"
                    ),
                }
                if event == "create_pixel_shader":
                    shader["reflection"] = _pixel_shader_reflection(row)
                shaders[(device, pointer)] = shader
            continue

        if event == "create_vertex_declaration":
            pointer = _ptr(row.get("declaration_ptr"))
            if pointer:
                declarations[(device, pointer)] = {
                    "sha256": _sha_bytes_hex(row),
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
                    "creation_event_index": creation_index,
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
                state["streams"][stream] = {
                    "pointer": _ptr(row.get("vertex_buffer_ptr")),
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
                    creation = dict(_lookup(textures, device, pointer) or {})
                    for key in (
                        "resource_type_name",
                        "width",
                        "height",
                        "depth",
                        "format",
                        "pool",
                        "level_count",
                        "usage",
                    ):
                        if row.get(key) is not None:
                            creation[key] = row.get(key)
                    state["textures"][stage] = {
                        "pointer": pointer,
                        "descriptor": creation,
                    }
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

        frame = row.get("frame")
        frame_value = frame if isinstance(frame, int) else None
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
        declaration = _lookup(
            declarations,
            device,
            state.get("declaration_ptr"),
        )
        declaration_sha = (
            declaration.get("sha256")
            if isinstance(declaration, Mapping)
            else None
        )

        stream_layout = []
        stream_shapes = []
        for stream, binding in sorted(state["streams"].items()):
            pointer = binding.get("pointer")
            stream_layout.append({
                "stream": stream,
                "stride": binding.get("stride"),
            })
            stream_shapes.append({
                "stream": stream,
                "stride": binding.get("stride"),
                **_buffer_shape(
                    vertex_buffers,
                    device,
                    pointer,
                    vertex=True,
                ),
            })

        index_pointer = state.get("index_buffer_ptr")
        index_shape = _buffer_shape(
            index_buffers,
            device,
            index_pointer,
            vertex=False,
        )
        reflection = (
            pixel_shader.get("reflection")
            if isinstance(pixel_shader, Mapping)
            else None
        )
        reflection_status = (
            reflection.get("status")
            if isinstance(reflection, Mapping)
            else "unavailable"
        )
        reflected_registers = (
            {
                int(value)
                for value in (reflection.get("sampler_registers") or [])
                if isinstance(value, int)
            }
            if isinstance(reflection, Mapping)
            else set()
        )
        if reflection_status == "reflected":
            reflected_target_draw_count += 1
        else:
            fallback_texture_state_draw_count += 1

        active_texture_bindings = [
            (stage, binding)
            for stage, binding in sorted(state["textures"].items())
            if (
                reflection_status != "reflected"
                or stage in reflected_registers
            )
        ]
        texture_shapes = [
            _texture_shape(binding.get("descriptor"), stage=stage)
            for stage, binding in active_texture_bindings
        ]

        pipeline = {
            "vertex_shader_sha256": vertex_sha,
            "pixel_shader_sha256": pixel_sha,
            "declaration_sha256": declaration_sha,
            "stream_layout": stream_layout,
            "index_format": index_shape.get("format"),
        }
        pipeline_sha = _canonical_hash(pipeline)
        resource_shape = {
            **pipeline,
            "stream_resource_shapes": stream_shapes,
            "index_resource_shape": index_shape,
            "texture_stages": texture_shapes,
        }
        resource_sha = _canonical_hash(resource_shape)

        stream0 = state["streams"].get(0) or {}
        stream0_pointer = stream0.get("pointer")
        geometry_identity = {
            "device_ptr": device or None,
            "stream0_vertex_buffer_ptr": stream0_pointer,
            "stream0_vertex_buffer_creation_event_index": (
                _creation_event_index(
                    vertex_buffers,
                    device,
                    stream0_pointer,
                )
            ),
            "index_buffer_ptr": index_pointer,
            "index_buffer_creation_event_index": _creation_event_index(
                index_buffers,
                device,
                index_pointer,
            ),
            "draw_range": {
                "primitive_type": row.get("primitive_type"),
                "base_vertex_index": row.get("base_vertex_index"),
                "start_index": row.get("start_index"),
                "primitive_count": row.get("primitive_count"),
            },
        }
        geometry_complete = bool(
            stream0_pointer
            and index_pointer
            and geometry_identity[
                "stream0_vertex_buffer_creation_event_index"
            ] is not None
            and geometry_identity[
                "index_buffer_creation_event_index"
            ] is not None
        )
        geometry_identity["creation_identity_complete"] = geometry_complete
        if geometry_complete:
            complete_geometry_pointer_draw_count += 1

        material_identity = {
            "device_ptr": device or None,
            "reflection_status": reflection_status,
            "texture_stages": [
                {
                    "stage": stage,
                    "texture_ptr": binding.get("pointer"),
                    "texture_creation_event_index": _creation_event_index(
                        textures,
                        device,
                        binding.get("pointer"),
                    ),
                }
                for stage, binding in active_texture_bindings
            ],
        }
        combined_identity = {
            "geometry": geometry_identity,
            "material": material_identity,
        }

        geometry_sha = _observe(
            global_geometry,
            geometry_identity,
            frame=frame_value,
        )
        material_sha = _observe(
            global_material,
            material_identity,
            frame=frame_value,
        )
        combined_sha = _observe(
            global_combined,
            combined_identity,
            frame=frame_value,
        )

        aggregate = resource_rows.get(resource_sha)
        if aggregate is None:
            aggregate = {
                "resource_shape_sha256": resource_sha,
                "pipeline_signature_sha256": pipeline_sha,
                "draw_count": 0,
                "first_frame": frame_value,
                "last_frame": frame_value,
                "families": set(),
                "target_pixel_hashes": set(),
                "_geometry_ids": Counter(),
                "_material_ids": Counter(),
                "_combined_ids": Counter(),
            }
            resource_rows[resource_sha] = aggregate
        aggregate["draw_count"] += 1
        if isinstance(frame_value, int):
            if aggregate["first_frame"] is None:
                aggregate["first_frame"] = frame_value
            else:
                aggregate["first_frame"] = min(
                    int(aggregate["first_frame"]), frame_value
                )
            if aggregate["last_frame"] is None:
                aggregate["last_frame"] = frame_value
            else:
                aggregate["last_frame"] = max(
                    int(aggregate["last_frame"]), frame_value
                )
        aggregate["families"].update(
            target_families.get(str(pixel_sha), set())
        )
        aggregate["target_pixel_hashes"].add(str(pixel_sha))
        aggregate["_geometry_ids"][geometry_sha] += 1
        aggregate["_material_ids"][material_sha] += 1
        aggregate["_combined_ids"][combined_sha] += 1

    rows: list[dict[str, Any]] = []
    for source in resource_rows.values():
        row = dict(source)
        geometry_ids = row.pop("_geometry_ids")
        material_ids = row.pop("_material_ids")
        combined_ids = row.pop("_combined_ids")
        row["families"] = sorted(row["families"])
        row["target_pixel_hashes"] = sorted(row["target_pixel_hashes"])
        row["geometry_pointer_identity_count"] = len(geometry_ids)
        row["material_pointer_identity_count"] = len(material_ids)
        row["combined_pointer_identity_count"] = len(combined_ids)
        row["geometry_pointer_observations"] = [
            {
                **dict(global_geometry[digest]),
                "draw_count_in_resource_shape": count,
            }
            for digest, count in geometry_ids.most_common()
        ]
        row["material_pointer_observations"] = [
            {
                **dict(global_material[digest]),
                "draw_count_in_resource_shape": count,
            }
            for digest, count in material_ids.most_common()
        ]
        row["combined_pointer_observations"] = [
            {
                **dict(global_combined[digest]),
                "draw_count_in_resource_shape": count,
            }
            for digest, count in combined_ids.most_common()
        ]
        rows.append(row)
    rows.sort(
        key=lambda row: (
            -int(row.get("draw_count") or 0),
            str(row.get("resource_shape_sha256") or ""),
        )
    )

    alignment = _catalog_alignment(resource_rows, target_catalog)
    target_draw_count = sum(target_draw_counts.values())
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
            "resource_shape_observation_count": len(resource_rows),
            "unique_geometry_pointer_identity_count": len(global_geometry),
            "unique_material_pointer_identity_count": len(global_material),
            "unique_combined_pointer_identity_count": len(global_combined),
            "complete_geometry_pointer_draw_count": (
                complete_geometry_pointer_draw_count
            ),
            "reflected_target_draw_count": reflected_target_draw_count,
            "fallback_texture_state_draw_count": (
                fallback_texture_state_draw_count
            ),
            "catalog_alignment_status": alignment["status"],
        },
        "catalog_alignment": alignment,
        "resource_shapes": rows,
        "boundary": {
            "capture_local_only": True,
            "resource_shape_sha": (
                "recomputed with the same pointer-free descriptor contract as "
                "SHIFT.D3D9TargetDrawSignatureCatalog/1"
            ),
            "geometry_pointer_identity": (
                "device + stream-0 VB pointer/creation generation + IB pointer/"
                "creation generation + exact draw range; capture-local only"
            ),
            "material_pointer_identity": (
                "device + CTAB-filtered bound texture pointers/creation "
                "generations; capture-local only"
            ),
            "stream1_instance_buffer": (
                "intentionally excluded from geometry pointer identity because "
                "it is dynamic instance data rather than static mesh content"
            ),
            "pointer_reuse": (
                "creation event index is included so a reused COM address is "
                "not treated as the same resource generation"
            ),
            "runtime_resource_path": "not evaluated",
            "payload_identity": "not evaluated",
            "render_admission": False,
            "purpose": (
                "detect same-object relationships inside one historical capture "
                "before deciding whether a new payload capture is required"
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_jsonl")
    parser.add_argument("output")
    parser.add_argument("--target-inventory", required=True)
    parser.add_argument("--target-catalog")
    args = parser.parse_args(argv)

    capture_path = resolve_input_path(args.capture_jsonl)
    inventory_path = resolve_input_path(args.target_inventory)
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if not isinstance(inventory, dict):
        raise ValueError("target inventory must be a JSON object")

    catalog = None
    if args.target_catalog:
        catalog_path = resolve_input_path(args.target_catalog)
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        if not isinstance(catalog, dict):
            raise ValueError("target catalog must be a JSON object")

    with capture_path.open("r", encoding="utf-8") as handle:
        report = build_target_pointer_observations(
            handle,
            target_inventory=inventory,
            target_catalog=catalog,
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["catalog_alignment"]["status"] != "mismatch" else 2


if __name__ == "__main__":
    raise SystemExit(main())
