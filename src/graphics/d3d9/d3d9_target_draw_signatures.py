"""Streaming draw-signature catalogue for target SHIFT D3D9 pixel shaders."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from d3d9_raw_capture_audit import resolve_input_path

_SHADER_DIR = Path(__file__).resolve().parents[1] / "shader"
if str(_SHADER_DIR) not in sys.path:
    sys.path.insert(0, str(_SHADER_DIR))

from shader_ir import parse_shader_blobs

FORMAT = "SHIFT.D3D9TargetDrawSignatureCatalog/1"


def _ptr(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, int):
        return f"0x{value:x}"
    text = str(value).strip().lower()
    return text or None


def _sha_bytes_hex(row: Mapping[str, Any]) -> str | None:
    raw = row.get("bytes_hex")
    if not isinstance(raw, str) or not raw or len(raw) % 2:
        return None
    try:
        payload = bytes.fromhex(raw)
    except ValueError:
        return None
    return hashlib.sha256(payload).hexdigest()


def _pixel_shader_reflection(
    row: Mapping[str, Any],
) -> dict[str, Any]:
    raw = row.get("bytes_hex")
    if not isinstance(raw, str) or not raw or len(raw) % 2:
        return {"status": "unavailable", "samplers": [], "sampler_registers": []}
    try:
        payload = bytes.fromhex(raw)
    except ValueError:
        return {"status": "unavailable", "samplers": [], "sampler_registers": []}

    try:
        blobs = parse_shader_blobs(payload)
    except Exception:
        return {"status": "error", "samplers": [], "sampler_registers": []}

    pixel_blobs = [blob for blob in blobs if blob.stage == "pixel"]
    if not pixel_blobs:
        return {"status": "unavailable", "samplers": [], "sampler_registers": []}

    samplers: list[dict[str, Any]] = []
    registers: set[int] = set()
    for blob in pixel_blobs:
        for sampler in blob.ctab_samplers:
            if not isinstance(sampler, Mapping):
                continue
            register = sampler.get("register")
            count = sampler.get("count", 1)
            try:
                register = int(register)
                count = int(count)
            except (TypeError, ValueError):
                continue
            if register < 0 or count <= 0:
                continue
            for offset in range(count):
                registers.add(register + offset)
            samplers.append({
                "name": sampler.get("name"),
                "register": register,
                "count": count,
            })

    return {
        "status": "reflected",
        "samplers": samplers,
        "sampler_registers": sorted(registers),
    }


def _target_families(
    inventory: Mapping[str, Any],
) -> tuple[set[str], dict[str, set[str]]]:
    hashes: set[str] = set()
    by_hash: dict[str, set[str]] = defaultdict(set)

    for family in inventory.get("families") or []:
        if not isinstance(family, Mapping):
            continue
        name = str(family.get("family") or "").strip()
        for digest in family.get("pixel_shader_sha256") or []:
            if not isinstance(digest, str) or len(digest) != 64:
                continue
            digest = digest.lower()
            hashes.add(digest)
            if name:
                by_hash[digest].add(name)

    for target in inventory.get("unique_targets") or []:
        if not isinstance(target, Mapping):
            continue
        digest = target.get("pixel_byte_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            continue
        digest = digest.lower()
        hashes.add(digest)
        for family in target.get("shader_families") or []:
            name = str(family).strip()
            if name:
                by_hash[digest].add(name)

    result = inventory.get("result")
    if isinstance(result, Mapping):
        for target in result.get("unique_targets") or []:
            if not isinstance(target, Mapping):
                continue
            digest = target.get("pixel_byte_sha256")
            if not isinstance(digest, str) or len(digest) != 64:
                continue
            digest = digest.lower()
            hashes.add(digest)
            for family in target.get("shader_families") or []:
                name = str(family).strip()
                if name:
                    by_hash[digest].add(name)

    return hashes, by_hash


def _canonical_hash(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _lookup(
    table: Mapping[tuple[str, str], Mapping[str, Any]],
    device: str,
    pointer: str | None,
) -> Mapping[str, Any] | None:
    if pointer is None:
        return None
    direct = table.get((device, pointer))
    if direct is not None:
        return direct
    generic = table.get(("", pointer))
    if generic is not None:
        return generic
    matches = [
        value
        for (candidate_device, candidate_pointer), value in table.items()
        if candidate_pointer == pointer
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _texture_shape(
    row: Mapping[str, Any] | None,
    *,
    stage: int,
) -> dict[str, Any]:
    row = row or {}
    return {
        "stage": stage,
        "resource_type_name": row.get("resource_type_name"),
        "width": row.get("width"),
        "height": row.get("height"),
        "depth": row.get("depth"),
        "edge_length": row.get("edge_length"),
        "format": row.get("format"),
        "pool": row.get("pool"),
        "level_count": row.get("level_count", row.get("levels")),
        "usage": row.get("usage"),
    }


def _aggregate_signature(
    table: dict[str, dict[str, Any]],
    signature_hash: str,
    payload: Mapping[str, Any],
    *,
    frame: int | None,
    event_index: int | None,
    families: Iterable[str],
    draw: Mapping[str, Any],
    stream_offsets: Mapping[int, Any] | None = None,
) -> None:
    row = table.get(signature_hash)
    if row is None:
        row = {
            "signature_sha256": signature_hash,
            "signature": dict(payload),
            "draw_count": 0,
            "primitive_count_sum": 0,
            "first_frame": frame,
            "last_frame": frame,
            "families": [],
            "target_pixel_hashes": [],
            "_families": set(),
            "_target_pixel_hashes": set(),
            "_ranges": Counter(),
            "_stream_offsets": defaultdict(Counter),
            "sample_draws": [],
        }
        table[signature_hash] = row

    row["draw_count"] += 1
    primitive_count = draw.get("primitive_count")
    if isinstance(primitive_count, int):
        row["primitive_count_sum"] += primitive_count
    if isinstance(frame, int):
        if row["first_frame"] is None:
            row["first_frame"] = frame
        else:
            row["first_frame"] = min(row["first_frame"], frame)
        if row["last_frame"] is None:
            row["last_frame"] = frame
        else:
            row["last_frame"] = max(row["last_frame"], frame)

    row["_families"].update(families)
    pixel_sha = payload.get("pixel_shader_sha256")
    if isinstance(pixel_sha, str):
        row["_target_pixel_hashes"].add(pixel_sha)

    range_key = (
        draw.get("primitive_type"),
        draw.get("base_vertex_index"),
        draw.get("start_index"),
        draw.get("primitive_count"),
    )
    row["_ranges"][range_key] += 1

    if stream_offsets:
        for stream, offset in stream_offsets.items():
            if isinstance(stream, int) and isinstance(offset, int):
                row["_stream_offsets"][stream][offset] += 1

    if len(row["sample_draws"]) < 8:
        row["sample_draws"].append({
            "frame": frame,
            "event_index": event_index,
            "primitive_type": draw.get("primitive_type"),
            "base_vertex_index": draw.get("base_vertex_index"),
            "start_index": draw.get("start_index"),
            "primitive_count": draw.get("primitive_count"),
        })


def _finalize_signature_rows(
    table: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for source in table.values():
        row = dict(source)
        families = row.pop("_families")
        target_hashes = row.pop("_target_pixel_hashes")
        ranges = row.pop("_ranges")
        stream_offsets = row.pop("_stream_offsets")
        row["families"] = sorted(families)
        row["target_pixel_hashes"] = sorted(target_hashes)
        row["distinct_draw_range_count"] = len(ranges)
        if stream_offsets:
            row["stream_offset_observations"] = [
                {
                    "stream": stream,
                    "unique_offset_count": len(offset_counts),
                    "min_offset_in_bytes": min(offset_counts),
                    "max_offset_in_bytes": max(offset_counts),
                    "top_offsets": [
                        {
                            "offset_in_bytes": offset,
                            "draw_count": count,
                        }
                        for offset, count in offset_counts.most_common(8)
                    ],
                }
                for stream, offset_counts in sorted(stream_offsets.items())
                if offset_counts
            ]
        row["top_draw_ranges"] = [
            {
                "primitive_type": key[0],
                "base_vertex_index": key[1],
                "start_index": key[2],
                "primitive_count": key[3],
                "draw_count": count,
            }
            for key, count in ranges.most_common(8)
        ]
        result.append(row)
    result.sort(
        key=lambda item: (
            -int(item.get("draw_count") or 0),
            str(item.get("signature_sha256") or ""),
        )
    )
    return result


def _build_layout_cohorts(
    pipeline_rows: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    cohorts: dict[str, dict[str, Any]] = {}
    for row in pipeline_rows.values():
        signature = row.get("signature") or {}
        layout = {
            "declaration_sha256": signature.get("declaration_sha256"),
            "stream_layout": list(signature.get("stream_layout") or []),
            "index_format": signature.get("index_format"),
        }
        layout_sha = _canonical_hash(layout)
        cohort = cohorts.setdefault(layout_sha, {
            "layout_sha256": layout_sha,
            "layout": layout,
            "draw_count": 0,
            "pipeline_signature_sha256s": set(),
            "vertex_shader_sha256s": set(),
            "pixel_shader_sha256s": set(),
            "families": set(),
        })
        cohort["draw_count"] += int(row.get("draw_count") or 0)
        cohort["pipeline_signature_sha256s"].add(
            str(row.get("signature_sha256") or "")
        )
        vertex = signature.get("vertex_shader_sha256")
        pixel = signature.get("pixel_shader_sha256")
        if vertex:
            cohort["vertex_shader_sha256s"].add(str(vertex))
        if pixel:
            cohort["pixel_shader_sha256s"].add(str(pixel))
        cohort["families"].update(row.get("_families") or [])

    result = []
    for source in cohorts.values():
        row = dict(source)
        for key in (
            "pipeline_signature_sha256s",
            "vertex_shader_sha256s",
            "pixel_shader_sha256s",
            "families",
        ):
            row[key] = sorted(row[key])
        result.append(row)
    result.sort(
        key=lambda row: (
            -int(row.get("draw_count") or 0),
            str(row.get("layout_sha256") or ""),
        )
    )
    return result


def catalog_target_draw_signatures(
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

    event_counts: Counter[str] = Counter()
    target_draw_counts: Counter[str] = Counter()
    pipeline_rows: dict[str, dict[str, Any]] = {}
    shape_rows: dict[str, dict[str, Any]] = {}
    invalid_json_count = 0
    non_object_count = 0
    source_line_count = 0
    first_target_frame: int | None = None
    last_target_frame: int | None = None
    reflected_target_draw_count = 0
    fallback_texture_state_draw_count = 0

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
        event_counts[event] += 1
        device = _ptr(row.get("device_ptr")) or ""
        state = states[device]

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
                    key: row.get(key)
                    for key in ("length", "usage", "fvf", "pool")
                }
            continue

        if event == "create_index_buffer":
            pointer = _ptr(row.get("index_buffer_ptr"))
            if pointer:
                index_buffers[(device, pointer)] = {
                    key: row.get(key)
                    for key in ("length", "usage", "format", "pool")
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
                    creation = dict(
                        _lookup(textures, device, pointer) or {}
                    )
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

        frame = row.get("frame")
        event_index = row.get("event_index")
        if isinstance(frame, int):
            first_target_frame = (
                frame
                if first_target_frame is None
                else min(first_target_frame, frame)
            )
            last_target_frame = (
                frame
                if last_target_frame is None
                else max(last_target_frame, frame)
            )
        target_draw_counts[pixel_sha] += 1

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
        stream_offsets: dict[int, int] = {}
        for stream, binding in sorted(state["streams"].items()):
            pointer = binding.get("pointer")
            buffer_shape = dict(
                _lookup(vertex_buffers, device, pointer) or {}
            )
            stream_layout.append({
                "stream": stream,
                "stride": binding.get("stride"),
            })
            offset = binding.get("offset_in_bytes")
            if isinstance(offset, int):
                stream_offsets[stream] = offset
            stream_shapes.append({
                "stream": stream,
                "stride": binding.get("stride"),
                **buffer_shape,
            })

        index_shape = dict(
            _lookup(
                index_buffers,
                device,
                state.get("index_buffer_ptr"),
            )
            or {}
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
        reflected_sampler_registers = (
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

        texture_shapes = [
            _texture_shape(
                binding.get("descriptor"),
                stage=stage,
            )
            for stage, binding in sorted(state["textures"].items())
            if (
                reflection_status != "reflected"
                or stage in reflected_sampler_registers
            )
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
        resource_shape_sha = _canonical_hash(resource_shape)

        families = sorted(target_families.get(pixel_sha, set()))
        _aggregate_signature(
            pipeline_rows,
            pipeline_sha,
            pipeline,
            frame=frame if isinstance(frame, int) else None,
            event_index=(
                event_index if isinstance(event_index, int) else None
            ),
            families=families,
            draw=row,
        )
        _aggregate_signature(
            shape_rows,
            resource_shape_sha,
            resource_shape,
            frame=frame if isinstance(frame, int) else None,
            event_index=(
                event_index if isinstance(event_index, int) else None
            ),
            families=families,
            draw=row,
            stream_offsets=stream_offsets,
        )

    target_draw_count = sum(target_draw_counts.values())
    layout_cohorts = _build_layout_cohorts(pipeline_rows)
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
            "first_target_frame": first_target_frame,
            "last_target_frame": last_target_frame,
            "unique_pipeline_signature_count": len(pipeline_rows),
            "unique_layout_cohort_count": len(layout_cohorts),
            "unique_resource_shape_signature_count": len(shape_rows),
            "reflected_target_draw_count": reflected_target_draw_count,
            "fallback_texture_state_draw_count": (
                fallback_texture_state_draw_count
            ),
        },
        "target_draw_hashes": [
            {
                "pixel_byte_sha256": digest,
                "draw_count": count,
                "families": sorted(target_families.get(digest, set())),
            }
            for digest, count in sorted(
                target_draw_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        "pipeline_signatures": _finalize_signature_rows(pipeline_rows),
        "layout_cohorts": layout_cohorts,
        "resource_shape_signatures": _finalize_signature_rows(shape_rows),
        "boundary": {
            "pipeline_signature": (
                "observational VS/PS/declaration/stream-stride/index-format "
                "state at target draws; not a material or primitive identity"
            ),
            "layout_cohort": (
                "groups pipeline signatures by declaration/stream-stride/"
                "index-format only; shader and resource identity are not claimed"
            ),
            "resource_shape_signature": (
                "adds runtime buffer/texture descriptor shapes while excluding "
                "pointer identity, payload proof and transient stream offsets"
            ),
            "stream_offset_observations": (
                "offsets are retained diagnostically per normalized shape but "
                "do not participate in its stable identity"
            ),
            "texture_stage_filter": (
                "when pixel-shader CTAB reflection is available, only reflected "
                "sampler registers participate in resource-shape texture state; "
                "otherwise all bound stages are preserved as a fallback"
            ),
            "resource_identity": "not claimed",
            "primitive_identity": "not claimed",
            "same_instance_identity": "not claimed",
        },
    }


def catalog_target_draw_signatures_file(
    capture_path: str | Path,
    *,
    target_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    with Path(capture_path).open("r", encoding="utf-8") as handle:
        return catalog_target_draw_signatures(
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

    report = catalog_target_draw_signatures_file(
        capture_path,
        target_inventory=inventory,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
