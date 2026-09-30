"""Disambiguate repeated scene instances with exact draw-local VS constants.

Phase 591 does not assign a retail world-matrix register. It scans every
contiguous four-register window in the strong-attributed draw-local vertex
constant state and compares exact IEEE-754 float32 bytes against each candidate
scene world matrix in row-major and transpose layouts.

A repeated binding is resolved only when every usable runtime observation
supports exactly one scene draw identity. Register/layout witnesses remain
observational evidence.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.NativeSceneInstanceTransformMatch/1"
SCENE_FORMAT = "SHIFT.NativeSceneBundle/1"
PIPELINE_FORMAT = "SHIFT.IMBRuntimeCapturePipeline/1"
OBSERVATION_CONTRACT = "selected-strong-variant-vertex-constants-v1"


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _matrix16(value: Any) -> list[float] | None:
    rows: list[Any]
    if isinstance(value, list) and len(value) == 16:
        rows = list(value)
    elif (
        isinstance(value, list)
        and len(value) == 4
        and all(isinstance(row, list) and len(row) == 4 for row in value)
    ):
        rows = [item for row in value for item in row]
    else:
        return None
    out: list[float] = []
    for item in rows:
        if not isinstance(item, (int, float)):
            return None
        number = float(item)
        if not math.isfinite(number):
            return None
        out.append(number)
    return out


def _f32_bytes(values: list[float]) -> bytes:
    return struct.pack("<16f", *[float(value) for value in values])


def _transpose(values: list[float]) -> list[float]:
    return [
        values[row + column * 4]
        for row in range(4)
        for column in range(4)
    ]


def _vertex_constant_windows(
    constant_state: Mapping[str, Any],
) -> list[dict[str, Any]]:
    vertex = constant_state.get("vertex")
    if not isinstance(vertex, Mapping):
        return []

    registers: dict[int, list[float]] = {}
    for raw_register, raw_values in vertex.items():
        register = _safe_int(raw_register)
        if register is None or register < 0:
            continue
        if (
            not isinstance(raw_values, list)
            or len(raw_values) != 4
            or not all(isinstance(value, (int, float)) for value in raw_values)
        ):
            continue
        values = [float(value) for value in raw_values]
        if not all(math.isfinite(value) for value in values):
            continue
        registers[register] = values

    windows: list[dict[str, Any]] = []
    for start in sorted(registers):
        if not all(start + offset in registers for offset in range(4)):
            continue
        values = [
            value
            for offset in range(4)
            for value in registers[start + offset]
        ]
        windows.append({
            "start_register": start,
            "registers": [start + offset for offset in range(4)],
            "values": values,
            "float32_hex": _f32_bytes(values).hex(),
        })
    return windows


def _pipeline_observations(
    pipeline: Mapping[str, Any],
) -> dict[int, list[dict[str, Any]]]:
    by_binding: dict[int, list[dict[str, Any]]] = {}
    for resource in pipeline.get("resource_results") or []:
        if not isinstance(resource, Mapping):
            continue
        for row in resource.get("attributed_texture_observations") or []:
            if not isinstance(row, Mapping):
                continue
            binding_index = _safe_int(row.get("binding_index"))
            if binding_index is None:
                continue
            by_binding.setdefault(binding_index, []).append(dict(row))
    return by_binding


def _scene_draws_by_binding(
    scene_bundle: Mapping[str, Any],
) -> dict[int, list[dict[str, Any]]]:
    by_binding: dict[int, list[dict[str, Any]]] = {}
    for row in scene_bundle.get("draws") or []:
        if not isinstance(row, Mapping):
            continue
        binding_index = _safe_int(row.get("binding_index"))
        if binding_index is None:
            continue
        by_binding.setdefault(binding_index, []).append(dict(row))
    return by_binding


def _observation_matches(
    draws: list[dict[str, Any]],
    observation: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    reasons: list[str] = []
    constant_state = observation.get("constant_state")
    if not isinstance(constant_state, Mapping):
        return [], ["vertex-constant-state-missing"]

    windows = _vertex_constant_windows(constant_state)
    if not windows:
        return [], ["vertex-constant-window-missing"]

    witnesses: list[dict[str, Any]] = []
    for draw in draws:
        world = _matrix16(draw.get("world_matrix"))
        if world is None:
            continue
        row_bytes = _f32_bytes(world)
        transpose_bytes = _f32_bytes(_transpose(world))
        draw_order = _safe_int(draw.get("draw_order"))
        draw_sha = (
            (draw.get("hashes") or {}).get("draw_identity_sha256")
            if isinstance(draw.get("hashes"), Mapping)
            else None
        )
        for window in windows:
            raw = bytes.fromhex(str(window["float32_hex"]))
            layouts: list[str] = []
            if raw == row_bytes:
                layouts.append("row-major")
            if raw == transpose_bytes:
                layouts.append("transpose")
            if not layouts:
                continue
            witnesses.append({
                "draw_order": draw_order,
                "draw_identity_sha256": draw_sha,
                "start_register": window["start_register"],
                "registers": list(window["registers"]),
                "layouts": layouts,
                "float32_hex": window["float32_hex"],
            })

    if not witnesses:
        reasons.append("world-matrix-constant-window-not-found")
    return witnesses, reasons


def build_scene_instance_transform_match(
    scene_bundle: Mapping[str, Any],
    capture_pipeline: Mapping[str, Any],
) -> dict[str, Any]:
    if scene_bundle.get("format") != SCENE_FORMAT:
        raise ValueError("scene input must be SHIFT.NativeSceneBundle/1")
    if capture_pipeline.get("format") != PIPELINE_FORMAT:
        raise ValueError(
            "capture input must be SHIFT.IMBRuntimeCapturePipeline/1"
        )

    blockers: list[str] = []
    if scene_bundle.get("ready") is not True:
        blockers.append("scene-instance-match:scene-bundle-not-ready")
    if capture_pipeline.get("pipeline_ready") is not True:
        blockers.append("scene-instance-match:capture-pipeline-not-ready")

    boundary = capture_pipeline.get("boundary")
    if (
        not isinstance(boundary, Mapping)
        or boundary.get("attributed_instance_transform_observation_contract")
        != OBSERVATION_CONTRACT
    ):
        blockers.append(
            "scene-instance-match:transform-observation-contract-missing"
        )

    scene_by_binding = _scene_draws_by_binding(scene_bundle)
    observations_by_binding = _pipeline_observations(capture_pipeline)

    rows: list[dict[str, Any]] = []
    repeated_binding_count = 0
    resolved_binding_count = 0

    for binding_index in sorted(scene_by_binding):
        draws = scene_by_binding[binding_index]
        if len(draws) <= 1:
            continue
        repeated_binding_count += 1
        observations = observations_by_binding.get(binding_index, [])
        row_reasons: list[str] = []
        observation_rows: list[dict[str, Any]] = []
        selected_draw_orders: set[int] = set()

        if not observations:
            row_reasons.append("strong-runtime-observation-missing")

        for observation in observations:
            witnesses, reasons = _observation_matches(draws, observation)
            draw_orders = {
                int(witness["draw_order"])
                for witness in witnesses
                if isinstance(witness.get("draw_order"), int)
            }
            if len(draw_orders) == 1:
                selected_draw_orders.update(draw_orders)
            elif len(draw_orders) == 0 and not reasons:
                reasons.append("scene-draw-not-matched")
            elif len(draw_orders) > 1:
                reasons.append(
                    f"scene-draw-constant-ambiguous:{len(draw_orders)}"
                )

            observation_rows.append({
                "frame": observation.get("frame"),
                "draw_index": observation.get("draw_index"),
                "status": "matched" if len(draw_orders) == 1 and not reasons else "blocked",
                "candidate_scene_draw_orders": sorted(draw_orders),
                "witness_count": len(witnesses),
                "witnesses": witnesses,
                "blocking_reasons": reasons,
            })
            row_reasons.extend(reasons)

        if len(selected_draw_orders) > 1:
            row_reasons.append(
                f"runtime-observations-disagree:{len(selected_draw_orders)}"
            )
        if observations and any(
            row.get("status") != "matched" for row in observation_rows
        ):
            row_reasons.append("runtime-observation-unresolved")

        selected_draw_order = (
            next(iter(selected_draw_orders))
            if len(selected_draw_orders) == 1 and not row_reasons
            else None
        )
        selected_draw = None
        if selected_draw_order is not None:
            selected_draw = next(
                (
                    draw for draw in draws
                    if _safe_int(draw.get("draw_order")) == selected_draw_order
                ),
                None,
            )
            if selected_draw is None:
                row_reasons.append("selected-scene-draw-not-found")
                selected_draw_order = None

        row_ready = selected_draw_order is not None and not row_reasons
        if row_ready:
            resolved_binding_count += 1
        else:
            blockers.extend(
                f"scene-instance-match:binding-{binding_index}:{reason}"
                for reason in row_reasons
            )

        rows.append({
            "binding_index": binding_index,
            "scene_draw_count": len(draws),
            "runtime_observation_count": len(observations),
            "status": "resolved" if row_ready else "blocked",
            "ready": row_ready,
            "selected_draw_order": selected_draw_order,
            "selected_draw_identity_sha256": (
                (selected_draw.get("hashes") or {}).get(
                    "draw_identity_sha256"
                )
                if isinstance(selected_draw, Mapping)
                and isinstance(selected_draw.get("hashes"), Mapping)
                else None
            ),
            "selected_world_matrix": (
                list(selected_draw.get("world_matrix") or [])
                if isinstance(selected_draw, Mapping)
                else None
            ),
            "observations": observation_rows,
            "blocking_reasons": list(dict.fromkeys(row_reasons)),
        })

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers and resolved_binding_count == repeated_binding_count
    return {
        "format": FORMAT,
        "version": 1,
        "status": (
            "not-needed"
            if ready and repeated_binding_count == 0
            else "ready"
            if ready
            else "blocked"
        ),
        "ready": ready,
        "blocking_reasons": blockers,
        "repeated_binding_count": repeated_binding_count,
        "resolved_binding_count": resolved_binding_count,
        "rows": rows,
        "boundary": {
            "observation_contract": OBSERVATION_CONTRACT,
            "matrix_comparison": "exact-ieee754-float32-bytes",
            "accepted_layouts": ["row-major", "transpose"],
            "register_semantics_assigned": False,
            "requires_strong_shader_attribution": True,
            "requires_all_observations_resolved": True,
            "manual_instance_selection": False,
        },
    }


def validate_files(
    scene_bundle_path: str | Path,
    capture_pipeline_path: str | Path,
) -> dict[str, Any]:
    scene = json.loads(Path(scene_bundle_path).read_text(encoding="utf-8"))
    capture = json.loads(
        Path(capture_pipeline_path).read_text(encoding="utf-8")
    )
    if not isinstance(scene, Mapping) or not isinstance(capture, Mapping):
        raise ValueError("inputs must be JSON objects")
    return build_scene_instance_transform_match(scene, capture)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene_bundle")
    parser.add_argument("capture_pipeline")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    result = validate_files(args.scene_bundle, args.capture_pipeline)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": result["format"],
        "status": result["status"],
        "ready": result["ready"],
        "repeated_binding_count": result["repeated_binding_count"],
        "resolved_binding_count": result["resolved_binding_count"],
        "blocking_reasons": result["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
