"""Reconstruct capture-local D3D9 shader creation, bind and draw provenance.

The extractor deliberately separates three identities:

* shader byte identity (SHA-256 of Create*Shader bytecode),
* shader object generation (pointer + creation event), and
* shader use (the concrete Set*Shader event that made a generation active).

This prevents pointer reuse or later creation events from being mistaken for the
shader generation that was actually selected at a draw.  All identities remain
capture-local evidence and are not promoted to FX/FXO permutation or retail
resource identity.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from d3d9_raw_capture_audit import resolve_input_path
from d3d9_target_draw_signatures import (
    _canonical_hash,
    _ptr,
    _sha_bytes_hex,
    _target_families,
)

FORMAT = "SHIFT.D3D9ShaderUseEvidence/1"


def _event_int(row: Mapping[str, Any], key: str) -> int | None:
    value = row.get(key)
    return value if isinstance(value, int) else None


def _generation_key(device: str, stage: str, pointer: str) -> tuple[str, str, str]:
    return device, stage, pointer


def _resolve_generation(
    shaders: Mapping[tuple[str, str, str], Mapping[str, Any]],
    *,
    device: str,
    stage: str,
    pointer: str | None,
) -> tuple[Mapping[str, Any] | None, str]:
    if pointer is None:
        return None, "unbound"

    direct = shaders.get(_generation_key(device, stage, pointer))
    if direct is not None:
        return direct, "exact-device-stage-pointer"

    generic = shaders.get(_generation_key("", stage, pointer))
    if generic is not None:
        return generic, "generic-device-stage-pointer"

    matches = [
        generation
        for (candidate_device, candidate_stage, candidate_pointer), generation in shaders.items()
        if candidate_stage == stage and candidate_pointer == pointer
    ]
    if len(matches) == 1:
        return matches[0], "unique-stage-pointer-fallback"
    if len(matches) > 1:
        return None, "ambiguous-stage-pointer"
    return None, "creation-not-observed"


def _binding_from_set_event(
    shaders: Mapping[tuple[str, str, str], Mapping[str, Any]],
    row: Mapping[str, Any],
    *,
    device: str,
    stage: str,
) -> dict[str, Any]:
    pointer = _ptr(row.get("shader_ptr"))
    generation, resolution = _resolve_generation(
        shaders,
        device=device,
        stage=stage,
        pointer=pointer,
    )
    generation = generation or {}
    return {
        "stage": stage,
        "shader_ptr": pointer,
        "shader_sha256": generation.get("shader_sha256"),
        "generation_sha256": generation.get("generation_sha256"),
        "creation_event_index": generation.get("creation_event_index"),
        "creation_frame": generation.get("creation_frame"),
        "generation_ordinal": generation.get("generation_ordinal"),
        "bind_event_index": _event_int(row, "event_index"),
        "bind_frame": _event_int(row, "frame"),
        "resolution": resolution,
    }


def _empty_binding(stage: str) -> dict[str, Any]:
    return {
        "stage": stage,
        "shader_ptr": None,
        "shader_sha256": None,
        "generation_sha256": None,
        "creation_event_index": None,
        "creation_frame": None,
        "generation_ordinal": None,
        "bind_event_index": None,
        "bind_frame": None,
        "resolution": "no-bind-observed",
    }


def _pair_hash(vertex: Mapping[str, Any], pixel: Mapping[str, Any], field: str) -> str | None:
    vertex_value = vertex.get(field)
    pixel_value = pixel.get(field)
    if vertex_value is None or pixel_value is None:
        return None
    return _canonical_hash({
        "vertex": vertex_value,
        "pixel": pixel_value,
    })


def _use_pair_hash(vertex: Mapping[str, Any], pixel: Mapping[str, Any]) -> str | None:
    if (
        vertex.get("generation_sha256") is None
        or pixel.get("generation_sha256") is None
        or vertex.get("bind_event_index") is None
        or pixel.get("bind_event_index") is None
    ):
        return None
    return _canonical_hash({
        "vertex": {
            "generation_sha256": vertex.get("generation_sha256"),
            "bind_event_index": vertex.get("bind_event_index"),
        },
        "pixel": {
            "generation_sha256": pixel.get("generation_sha256"),
            "bind_event_index": pixel.get("bind_event_index"),
        },
    })


def _binding_missing(stage: str, binding: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    prefix = f"{stage}-shader"
    if binding.get("bind_event_index") is None:
        missing.append(f"{prefix}-bind-event-unresolved")
    if binding.get("shader_ptr") is None:
        missing.append(f"{prefix}-unbound")
        return missing
    if binding.get("shader_sha256") is None:
        missing.append(f"{prefix}-creation-unresolved")
    if binding.get("generation_sha256") is None:
        missing.append(f"{prefix}-generation-unresolved")
    return missing


def build_shader_use_evidence(
    lines: Iterable[str],
    *,
    target_inventory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    target_hashes: set[str] = set()
    target_families: dict[str, set[str]] = {}
    if target_inventory is not None:
        target_hashes, target_families = _target_families(target_inventory)
        if not target_hashes:
            raise ValueError("target inventory contains no pixel shader hashes")

    shaders: dict[tuple[str, str, str], dict[str, Any]] = {}
    generation_ordinals: Counter[tuple[str, str, str]] = Counter()
    states: dict[str, dict[str, dict[str, Any]]] = defaultdict(
        lambda: {
            "vertex": _empty_binding("vertex"),
            "pixel": _empty_binding("pixel"),
        }
    )

    event_counts: Counter[str] = Counter()
    resolution_counts: Counter[str] = Counter()
    source_line_count = 0
    invalid_json_count = 0
    non_object_count = 0
    pointer_reuse_creation_count = 0
    generations: list[dict[str, Any]] = []
    draws: list[dict[str, Any]] = []
    byte_pair_ids: set[str] = set()
    generation_pair_ids: set[str] = set()
    use_pair_ids: set[str] = set()
    exact_draw_count = 0

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

        if event in {"reset", "device_reset"}:
            states[device] = {
                "vertex": _empty_binding("vertex"),
                "pixel": _empty_binding("pixel"),
            }
            continue

        if event in {"create_vertex_shader", "create_pixel_shader"}:
            stage = "vertex" if event == "create_vertex_shader" else "pixel"
            pointer = _ptr(row.get("shader_ptr"))
            digest = _sha_bytes_hex(row)
            if pointer is None or digest is None:
                continue
            key = _generation_key(device, stage, pointer)
            if key in shaders:
                pointer_reuse_creation_count += 1
            generation_ordinals[key] += 1
            generation_payload = {
                "device_ptr": device or None,
                "stage": stage,
                "shader_ptr": pointer,
                "creation_event_index": _event_int(row, "event_index"),
                "creation_frame": _event_int(row, "frame"),
                "generation_ordinal": generation_ordinals[key],
                "shader_sha256": digest,
            }
            generation = {
                **generation_payload,
                "generation_sha256": _canonical_hash(generation_payload),
            }
            shaders[key] = generation
            generations.append(generation)
            continue

        if event in {"set_vertex_shader", "set_pixel_shader"}:
            stage = "vertex" if event == "set_vertex_shader" else "pixel"
            binding = _binding_from_set_event(
                shaders,
                row,
                device=device,
                stage=stage,
            )
            states[device][stage] = binding
            resolution_counts[str(binding["resolution"])] += 1
            continue

        if event != "draw_indexed_primitive":
            continue

        vertex = dict(states[device]["vertex"])
        pixel = dict(states[device]["pixel"])
        pixel_sha = pixel.get("shader_sha256")
        if target_inventory is not None and pixel_sha not in target_hashes:
            continue

        byte_pair_sha = _pair_hash(vertex, pixel, "shader_sha256")
        generation_pair_sha = _pair_hash(vertex, pixel, "generation_sha256")
        use_pair_sha = _use_pair_hash(vertex, pixel)
        if byte_pair_sha:
            byte_pair_ids.add(byte_pair_sha)
        if generation_pair_sha:
            generation_pair_ids.add(generation_pair_sha)
        if use_pair_sha:
            use_pair_ids.add(use_pair_sha)

        missing = _binding_missing("vertex", vertex) + _binding_missing("pixel", pixel)
        exact = not missing
        if exact:
            exact_draw_count += 1
        confidence = "exact-capture-local" if exact else "partial-capture-local"
        draws.append({
            "frame": _event_int(row, "frame"),
            "event_index": _event_int(row, "event_index"),
            "device_ptr": device or None,
            "families": sorted(target_families.get(str(pixel_sha), set())),
            "classification": confidence,
            "missing_shader_use_state": missing,
            "vertex_shader": vertex,
            "pixel_shader": pixel,
            "shader_pair": {
                "vertex_shader_sha256": vertex.get("shader_sha256"),
                "pixel_shader_sha256": pixel_sha,
            },
            "shader_pair_sha256": byte_pair_sha,
            "shader_generation_pair_sha256": generation_pair_sha,
            "shader_use_pair_sha256": use_pair_sha,
            "provenance": {
                "source": "raw-d3d9-create-set-draw-history",
                "confidence": confidence,
                "draw_event_index": _event_int(row, "event_index"),
            },
        })

    target_draw_count = len(draws)
    return {
        "format": FORMAT,
        "version": 1,
        "status": "observed" if target_draw_count else "not-observed",
        "summary": {
            "source_line_count": source_line_count,
            "invalid_json_count": invalid_json_count,
            "non_object_count": non_object_count,
            "shader_creation_count": len(generations),
            "vertex_shader_creation_count": event_counts["create_vertex_shader"],
            "pixel_shader_creation_count": event_counts["create_pixel_shader"],
            "shader_bind_event_count": (
                event_counts["set_vertex_shader"] + event_counts["set_pixel_shader"]
            ),
            "pointer_reuse_creation_count": pointer_reuse_creation_count,
            "draw_count": target_draw_count,
            "exact_capture_local_draw_count": exact_draw_count,
            "partial_capture_local_draw_count": target_draw_count - exact_draw_count,
            "unique_shader_pair_count": len(byte_pair_ids),
            "unique_shader_generation_pair_count": len(generation_pair_ids),
            "unique_shader_use_pair_count": len(use_pair_ids),
            "target_filter_supplied": target_inventory is not None,
            "target_pixel_hash_count": len(target_hashes),
        },
        "event_counts": dict(sorted(event_counts.items())),
        "bind_resolution_counts": dict(sorted(resolution_counts.items())),
        "shader_generations": sorted(
            generations,
            key=lambda item: (
                item.get("creation_event_index") is None,
                item.get("creation_event_index") or -1,
                str(item.get("stage") or ""),
                str(item.get("shader_ptr") or ""),
            ),
        ),
        "draws": draws,
        "boundary": {
            "shader_byte_identity": "exact SHA-256 of captured CreateVertexShader/CreatePixelShader bytecode",
            "shader_generation_identity": "capture-local device/stage/pointer creation generation only",
            "shader_use_identity": "capture-local SetVertexShader/SetPixelShader event provenance retained at each draw",
            "shader_pair": "exact captured VS/PS byte pair; does not by itself prove an FXO permutation name",
            "pointer_reuse": "creation event and generation hash prevent reused COM addresses from collapsing generations",
            "retail_resource_identity": "not claimed",
            "fxo_permutation_selection": "not claimed",
            "render_admission": False,
        },
    }


def build_shader_use_evidence_file(
    capture_path: str | Path,
    *,
    target_inventory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    with Path(capture_path).open("r", encoding="utf-8") as handle:
        return build_shader_use_evidence(handle, target_inventory=target_inventory)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_jsonl")
    parser.add_argument("output")
    parser.add_argument("--target-inventory")
    args = parser.parse_args(argv)

    capture_path = resolve_input_path(args.capture_jsonl)
    inventory = None
    if args.target_inventory:
        inventory_path = resolve_input_path(args.target_inventory)
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        if not isinstance(inventory, dict):
            raise ValueError("target inventory must be a JSON object")

    report = build_shader_use_evidence_file(
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
