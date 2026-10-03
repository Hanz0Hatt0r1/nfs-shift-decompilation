"""Extract draw-local texture binding and sampler-state provenance for target draws.

The report keeps portable resource identity, capture-local COM generations,
SetTexture use provenance, and explicit SetSamplerState writes separate.  A
missing sampler-state event is recorded as an observation gap; it is not treated
as proof that the draw is unusable because D3D9 sampler defaults may remain in
effect.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from d3d9_raw_capture_audit import resolve_input_path
from d3d9_target_draw_local_evidence import _shader_reflection
from d3d9_target_draw_signatures import (
    _canonical_hash,
    _ptr,
    _sha_bytes_hex,
    _target_families,
)

FORMAT = "SHIFT.D3D9TargetTextureSamplerEvidence/1"

_SAMPLER_STATE_NAMES = {
    1: "D3DSAMP_ADDRESSU",
    2: "D3DSAMP_ADDRESSV",
    3: "D3DSAMP_ADDRESSW",
    4: "D3DSAMP_BORDERCOLOR",
    5: "D3DSAMP_MAGFILTER",
    6: "D3DSAMP_MINFILTER",
    7: "D3DSAMP_MIPFILTER",
    8: "D3DSAMP_MIPMAPLODBIAS",
    9: "D3DSAMP_MAXMIPLEVEL",
    10: "D3DSAMP_MAXANISOTROPY",
    11: "D3DSAMP_SRGBTEXTURE",
    12: "D3DSAMP_ELEMENTINDEX",
    13: "D3DSAMP_DMAPOFFSET",
}


def _event_int(row: Mapping[str, Any], key: str) -> int | None:
    value = row.get(key)
    return value if isinstance(value, int) else None


def _portable_identity(row: Mapping[str, Any]) -> dict[str, Any]:
    path = row.get("resource_path")
    digest = row.get("resource_sha256")
    return {
        "resource_path": path if isinstance(path, str) and path else None,
        "resource_sha256": digest if isinstance(digest, str) and digest else None,
        "resource_signature": row.get("resource_signature"),
    }


def _texture_descriptor(row: Mapping[str, Any], *, kind: str | None = None) -> dict[str, Any]:
    resource_type_name = row.get("resource_type_name") or kind
    width = row.get("width")
    height = row.get("height")
    edge_length = row.get("edge_length")
    if resource_type_name == "cube_texture" and edge_length is not None:
        width = edge_length
        height = edge_length
    return {
        "resource_type_name": resource_type_name,
        "width": width,
        "height": height,
        "depth": row.get("depth"),
        "edge_length": edge_length,
        "format": row.get("format"),
        "pool": row.get("pool"),
        "level_count": row.get("level_count", row.get("levels")),
        "usage": row.get("usage"),
    }


def _texture_key(device: str, pointer: str) -> tuple[str, str]:
    return device, pointer


def _resolve_texture(
    textures: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    device: str,
    pointer: str | None,
) -> tuple[Mapping[str, Any] | None, str]:
    if pointer is None:
        return None, "unbound"
    direct = textures.get(_texture_key(device, pointer))
    if direct is not None:
        return direct, "exact-device-pointer"
    generic = textures.get(_texture_key("", pointer))
    if generic is not None:
        return generic, "generic-device-pointer"
    matches = [
        value
        for (candidate_device, candidate_pointer), value in textures.items()
        if candidate_pointer == pointer
    ]
    if len(matches) == 1:
        return matches[0], "unique-pointer-fallback"
    if len(matches) > 1:
        return None, "ambiguous-pointer"
    return None, "creation-not-observed"


def _resolve_shader(
    shaders: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    device: str,
    pointer: str | None,
) -> Mapping[str, Any] | None:
    if pointer is None:
        return None
    direct = shaders.get((device, pointer))
    if direct is not None:
        return direct
    generic = shaders.get(("", pointer))
    if generic is not None:
        return generic
    matches = [
        value
        for (candidate_device, candidate_pointer), value in shaders.items()
        if candidate_pointer == pointer
    ]
    return matches[0] if len(matches) == 1 else None


def _texture_scope(binding: Mapping[str, Any]) -> str:
    if binding.get("texture_ptr") is None:
        return "unbound"
    portable = binding.get("portable_resource_identity") or {}
    if portable.get("resource_path") and portable.get("resource_sha256"):
        return "portable-resource-identified"
    if binding.get("snapshot_status") == "captured" and binding.get("snapshot_paths"):
        return "captured-snapshot-backed"
    if binding.get("texture_generation_sha256"):
        return "runtime-object-generation-only"
    return "runtime-pointer-only"


def _sampler_rows(
    reflection: Mapping[str, Any] | None,
    textures: Mapping[int, Mapping[str, Any]],
    sampler_states: Mapping[int, Mapping[int, Mapping[str, Any]]],
) -> tuple[list[tuple[int, str | None]], str]:
    if isinstance(reflection, Mapping) and reflection.get("status") == "reflected":
        stages: list[tuple[int, str | None]] = []
        seen: set[int] = set()
        for sampler in reflection.get("samplers") or []:
            if not isinstance(sampler, Mapping):
                continue
            register = sampler.get("register")
            count = sampler.get("count", 1)
            if not isinstance(register, int) or not isinstance(count, int) or count <= 0:
                continue
            name = sampler.get("name")
            for offset in range(count):
                stage = register + offset
                if stage in seen:
                    continue
                seen.add(stage)
                item_name = f"{name}[{offset}]" if count > 1 and name else name
                stages.append((stage, item_name))
        return stages, "ctab-reflected"

    fallback_stages = sorted(
        set(stage for stage in textures if isinstance(stage, int))
        | set(stage for stage in sampler_states if isinstance(stage, int))
    )
    return [(stage, None) for stage in fallback_stages], "reflection-unavailable-fallback"


def _capture_observation(count: int, *, missing_event: str) -> dict[str, Any]:
    return {
        "status": "observed" if count else "not-observed-in-capture",
        "observed_count": count,
        "minimal_missing_event": None if count else missing_event,
    }


def build_target_texture_sampler_evidence(
    lines: Iterable[str],
    *,
    target_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    target_hashes, target_families = _target_families(target_inventory)
    if not target_hashes:
        raise ValueError("target inventory contains no pixel shader hashes")

    shaders: dict[tuple[str, str], dict[str, Any]] = {}
    textures: dict[tuple[str, str], dict[str, Any]] = {}
    texture_ordinals: Counter[tuple[str, str]] = Counter()
    states: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "pixel_shader": None,
            "textures": {},
            "sampler_states": {},
        }
    )

    event_counts: Counter[str] = Counter()
    source_line_count = invalid_json_count = non_object_count = 0
    portable_identity_event_count = 0
    captured_snapshot_event_count = 0
    texture_pointer_reuse_creation_count = 0
    exact_draw_count = 0
    reflected_draw_count = 0
    explicit_sampler_state_draw_count = 0
    unresolved_texture_binding_count = 0
    target_draw_counts: Counter[str] = Counter()
    sampler_use_ids: set[str] = set()
    texture_generation_ids: set[str] = set()
    texture_use_ids: set[str] = set()
    draws: list[dict[str, Any]] = []

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

        if (
            isinstance(row.get("resource_path"), str)
            and row.get("resource_path")
            and isinstance(row.get("resource_sha256"), str)
            and row.get("resource_sha256")
        ):
            portable_identity_event_count += 1
        if row.get("snapshot_status") == "captured" and row.get("snapshot_paths"):
            captured_snapshot_event_count += 1

        if event in {"reset", "device_reset"}:
            states[device] = {
                "pixel_shader": None,
                "textures": {},
                "sampler_states": {},
            }
            continue

        if event == "create_pixel_shader":
            pointer = _ptr(row.get("shader_ptr"))
            digest = _sha_bytes_hex(row)
            if pointer and digest:
                shaders[(device, pointer)] = {
                    "shader_sha256": digest,
                    "creation_event_index": _event_int(row, "event_index"),
                    "reflection": _shader_reflection(row, stage="pixel"),
                }
            continue

        if event == "set_pixel_shader":
            pointer = _ptr(row.get("shader_ptr"))
            shader = _resolve_shader(shaders, device=device, pointer=pointer)
            state["pixel_shader"] = {
                "shader_ptr": pointer,
                "shader_sha256": shader.get("shader_sha256") if shader else None,
                "creation_event_index": shader.get("creation_event_index") if shader else None,
                "bind_event_index": _event_int(row, "event_index"),
                "bind_frame": _event_int(row, "frame"),
                "reflection": shader.get("reflection") if shader else None,
            }
            continue

        if event in {"create_texture", "create_cube_texture"}:
            pointer = _ptr(row.get("texture_ptr"))
            if pointer is None:
                continue
            key = _texture_key(device, pointer)
            if key in textures:
                texture_pointer_reuse_creation_count += 1
            texture_ordinals[key] += 1
            kind = "cube_texture" if event == "create_cube_texture" else "texture2d"
            descriptor = _texture_descriptor(row, kind=kind)
            generation_payload = {
                "device_ptr": device or None,
                "texture_ptr": pointer,
                "creation_event_index": _event_int(row, "event_index"),
                "generation_ordinal": texture_ordinals[key],
                "descriptor": descriptor,
            }
            texture = {
                **generation_payload,
                "creation_frame": _event_int(row, "frame"),
                "texture_generation_sha256": _canonical_hash(generation_payload),
                "portable_resource_identity": _portable_identity(row),
                "snapshot_status": row.get("snapshot_status"),
                "snapshot_paths": list(row.get("snapshot_paths") or []),
            }
            textures[key] = texture
            texture_generation_ids.add(texture["texture_generation_sha256"])
            continue

        if event == "set_texture":
            stage = row.get("stage")
            if not isinstance(stage, int):
                continue
            pointer = _ptr(row.get("texture_ptr"))
            if pointer is None:
                state["textures"].pop(stage, None)
                continue
            generation, resolution = _resolve_texture(
                textures,
                device=device,
                pointer=pointer,
            )
            generation = generation or {}
            descriptor = dict(generation.get("descriptor") or {})
            observed_descriptor = _texture_descriptor(row)
            for key, value in observed_descriptor.items():
                if value is not None:
                    descriptor[key] = value
            portable = dict(generation.get("portable_resource_identity") or {})
            set_portable = _portable_identity(row)
            for key, value in set_portable.items():
                if value is not None:
                    portable[key] = value
            snapshot_status = row.get("snapshot_status", generation.get("snapshot_status"))
            snapshot_paths = list(row.get("snapshot_paths") or generation.get("snapshot_paths") or [])
            binding = {
                "stage": stage,
                "texture_ptr": pointer,
                "texture_generation_sha256": generation.get("texture_generation_sha256"),
                "texture_creation_event_index": generation.get("creation_event_index"),
                "texture_creation_frame": generation.get("creation_frame"),
                "texture_generation_ordinal": generation.get("generation_ordinal"),
                "texture_bind_event_index": _event_int(row, "event_index"),
                "texture_bind_frame": _event_int(row, "frame"),
                "resolution": resolution,
                "descriptor": descriptor,
                "portable_resource_identity": portable,
                "snapshot_status": snapshot_status,
                "snapshot_paths": snapshot_paths,
            }
            binding["resource_scope"] = _texture_scope(binding)
            binding["texture_use_sha256"] = _canonical_hash({
                "texture_generation_sha256": binding.get("texture_generation_sha256"),
                "texture_bind_event_index": binding.get("texture_bind_event_index"),
                "stage": stage,
            })
            texture_use_ids.add(binding["texture_use_sha256"])
            state["textures"][stage] = binding
            continue

        if event == "set_sampler_state":
            sampler = row.get("sampler")
            state_type = row.get("state")
            if not isinstance(sampler, int) or not isinstance(state_type, int):
                continue
            state["sampler_states"].setdefault(sampler, {})[state_type] = {
                "state": state_type,
                "state_name": _SAMPLER_STATE_NAMES.get(state_type),
                "value": row.get("value"),
                "write_event_index": _event_int(row, "event_index"),
                "write_frame": _event_int(row, "frame"),
            }
            continue

        if event != "draw_indexed_primitive":
            continue

        pixel = state.get("pixel_shader") or {}
        pixel_sha = pixel.get("shader_sha256")
        if pixel_sha not in target_hashes:
            continue
        target_draw_counts[str(pixel_sha)] += 1

        reflection = pixel.get("reflection")
        stages, stage_source = _sampler_rows(
            reflection,
            state.get("textures") or {},
            state.get("sampler_states") or {},
        )
        reflected = stage_source == "ctab-reflected"
        if reflected:
            reflected_draw_count += 1

        bindings: list[dict[str, Any]] = []
        draw_missing: list[str] = []
        any_explicit_sampler_state = False
        for stage, sampler_name in stages:
            texture_binding = dict((state.get("textures") or {}).get(stage) or {})
            if not texture_binding:
                texture_binding = {
                    "stage": stage,
                    "texture_ptr": None,
                    "texture_generation_sha256": None,
                    "texture_creation_event_index": None,
                    "texture_creation_frame": None,
                    "texture_generation_ordinal": None,
                    "texture_bind_event_index": None,
                    "texture_bind_frame": None,
                    "resolution": "unbound",
                    "descriptor": {},
                    "portable_resource_identity": {
                        "resource_path": None,
                        "resource_sha256": None,
                        "resource_signature": None,
                    },
                    "snapshot_status": None,
                    "snapshot_paths": [],
                    "resource_scope": "unbound",
                    "texture_use_sha256": None,
                }
            sampler_state_map = (state.get("sampler_states") or {}).get(stage) or {}
            sampler_state_rows = [
                dict(sampler_state_map[key])
                for key in sorted(sampler_state_map)
            ]
            if sampler_state_rows:
                any_explicit_sampler_state = True
            sampler_state_signature = _canonical_hash({
                "stage": stage,
                "states": [
                    {"state": item.get("state"), "value": item.get("value")}
                    for item in sampler_state_rows
                ],
            })
            binding = {
                **texture_binding,
                "sampler_name": sampler_name,
                "sampler_state_status": (
                    "explicit-writes-observed"
                    if sampler_state_rows
                    else "no-explicit-write-observed"
                ),
                "sampler_state_signature_sha256": sampler_state_signature,
                "sampler_states": sampler_state_rows,
            }
            if binding.get("texture_ptr") is None:
                draw_missing.append(f"sampler-{stage}-texture-unbound")
                unresolved_texture_binding_count += 1
            elif binding.get("texture_generation_sha256") is None:
                draw_missing.append(f"sampler-{stage}-texture-generation-unresolved")
                unresolved_texture_binding_count += 1
            elif binding.get("texture_bind_event_index") is None:
                draw_missing.append(f"sampler-{stage}-texture-bind-event-unresolved")
                unresolved_texture_binding_count += 1
            bindings.append(binding)

        if any_explicit_sampler_state:
            explicit_sampler_state_draw_count += 1
        if not reflected:
            draw_missing.append("pixel-ctab-sampler-reflection-unavailable")

        exact = not draw_missing
        if exact:
            exact_draw_count += 1
        classification = "exact-capture-local" if exact else "partial-capture-local"
        signature_payload = {
            "pixel_shader_sha256": pixel_sha,
            "samplers": [
                {
                    "stage": item.get("stage"),
                    "texture_generation_sha256": item.get("texture_generation_sha256"),
                    "texture_bind_event_index": item.get("texture_bind_event_index"),
                    "sampler_state_signature_sha256": item.get("sampler_state_signature_sha256"),
                }
                for item in bindings
            ],
        }
        sampler_use_sha = _canonical_hash(signature_payload)
        sampler_use_ids.add(sampler_use_sha)
        draws.append({
            "frame": _event_int(row, "frame"),
            "event_index": _event_int(row, "event_index"),
            "device_ptr": device or None,
            "families": sorted(target_families.get(str(pixel_sha), set())),
            "classification": classification,
            "missing_capture_local_state": draw_missing,
            "pixel_shader": {
                "shader_ptr": pixel.get("shader_ptr"),
                "shader_sha256": pixel_sha,
                "creation_event_index": pixel.get("creation_event_index"),
                "bind_event_index": pixel.get("bind_event_index"),
            },
            "sampler_stage_source": stage_source,
            "explicit_sampler_state_observed": any_explicit_sampler_state,
            "sampler_bindings": bindings,
            "sampler_use_signature_sha256": sampler_use_sha,
            "provenance": {
                "source": "raw-d3d9-create-texture-set-texture-set-sampler-state-draw-history",
                "confidence": classification,
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
            "target_hash_count": len(target_hashes),
            "target_draw_hash_count": len(target_draw_counts),
            "target_draw_count": target_draw_count,
            "exact_capture_local_draw_count": exact_draw_count,
            "partial_capture_local_draw_count": target_draw_count - exact_draw_count,
            "ctab_reflected_target_draw_count": reflected_draw_count,
            "explicit_sampler_state_target_draw_count": explicit_sampler_state_draw_count,
            "unresolved_sampler_texture_binding_count": unresolved_texture_binding_count,
            "unique_texture_generation_count": len(texture_generation_ids),
            "unique_texture_use_count": len(texture_use_ids),
            "unique_sampler_use_signature_count": len(sampler_use_ids),
            "texture_pointer_reuse_creation_count": texture_pointer_reuse_creation_count,
            "portable_resource_identity_event_count": portable_identity_event_count,
            "captured_snapshot_event_count": captured_snapshot_event_count,
        },
        "event_counts": dict(sorted(event_counts.items())),
        "capture_observations": {
            "texture_creation_history": _capture_observation(
                event_counts["create_texture"] + event_counts["create_cube_texture"],
                missing_event="create_texture/create_cube_texture",
            ),
            "texture_bind_history": _capture_observation(
                event_counts["set_texture"],
                missing_event="set_texture",
            ),
            "explicit_sampler_state_history": _capture_observation(
                event_counts["set_sampler_state"],
                missing_event="set_sampler_state",
            ),
            "portable_resource_path_sha_identity": _capture_observation(
                portable_identity_event_count,
                missing_event="resource_path + resource_sha256 on one resource event",
            ),
            "captured_texture_snapshot": _capture_observation(
                captured_snapshot_event_count,
                missing_event="snapshot_status=captured + snapshot_paths",
            ),
            "buffer_payload": _capture_observation(
                event_counts["buffer_payload"],
                missing_event="buffer_payload",
            ),
        },
        "draws": draws,
        "boundary": {
            "target_filter": "draws require an active captured pixel-shader byte SHA-256 present in the supplied target inventory",
            "texture_generation": "device + COM pointer + creation event is capture-local identity only",
            "texture_use": "SetTexture event provenance is frozen at bind time so later COM pointer reuse cannot rewrite an earlier draw",
            "sampler_state": "only explicit SetSamplerState writes are reported; no explicit write does not prove an unknown state or require a recapture because D3D9 defaults may apply",
            "resource_scope": "portable identity is claimed only when resource_path and resource_sha256 are both observed; otherwise runtime-object labels remain capture-local",
            "external_texture_classification": "not inferred from absence of a retail path",
            "material_identity": "not claimed",
            "retail_texture_identity": "not claimed without portable path/SHA or another exact payload join",
            "render_admission": False,
        },
    }


def build_target_texture_sampler_evidence_file(
    capture_path: str | Path,
    *,
    target_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    with Path(capture_path).open("r", encoding="utf-8") as handle:
        return build_target_texture_sampler_evidence(
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

    report = build_target_texture_sampler_evidence_file(
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
