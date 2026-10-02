"""Streaming capability audit for raw SHIFT D3D9 JSONL captures."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

FORMAT = "SHIFT.D3D9RawCaptureAudit/1"


def resolve_input_path(path: str | Path) -> Path:
    """Resolve a CLI input path without depending on the caller's cwd.

    Existing absolute paths and existing cwd-relative paths win. If a relative
    path does not exist from the current working directory, retry it from the
    repository root inferred from this module's location.
    """
    candidate = Path(path).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate

    repo_root = Path(__file__).resolve().parents[3]
    repo_candidate = repo_root / candidate
    if repo_candidate.exists():
        return repo_candidate

    raise FileNotFoundError(
        f"input file not found: {candidate} "
        f"(also tried {repo_candidate})"
    )


def _decode_line(text: str) -> tuple[Any, list[str]]:
    duplicate_keys: list[str] = []

    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                duplicate_keys.append(key)
            value[key] = item
        return value

    return json.loads(text, object_pairs_hook=hook), duplicate_keys


def _shader_digest(row: Mapping[str, Any]) -> str | None:
    raw = row.get("bytes_hex")
    if not isinstance(raw, str) or not raw or len(raw) % 2:
        return None
    try:
        payload = bytes.fromhex(raw)
    except ValueError:
        return None
    return hashlib.sha256(payload).hexdigest()


def _target_pixel_hashes(value: Mapping[str, Any] | None) -> set[str]:
    if not isinstance(value, Mapping):
        return set()

    hashes: set[str] = set()
    for family in value.get("families") or []:
        if not isinstance(family, Mapping):
            continue
        for digest in family.get("pixel_shader_sha256") or []:
            if isinstance(digest, str) and len(digest) == 64:
                hashes.add(digest.lower())

    for target in value.get("unique_targets") or []:
        if not isinstance(target, Mapping):
            continue
        digest = target.get("pixel_byte_sha256")
        if isinstance(digest, str) and len(digest) == 64:
            hashes.add(digest.lower())

    result = value.get("result")
    if isinstance(result, Mapping):
        for target in result.get("unique_targets") or []:
            if not isinstance(target, Mapping):
                continue
            digest = target.get("pixel_byte_sha256")
            if isinstance(digest, str) and len(digest) == 64:
                hashes.add(digest.lower())
    return hashes


def audit_capture_lines(
    lines: Iterable[str],
    *,
    target_inventory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    event_counts: Counter[str] = Counter()
    duplicate_key_counts: Counter[str] = Counter()
    duplicate_line_count = 0
    invalid_json_count = 0
    non_object_count = 0
    nonempty_line_count = 0

    frame_min: int | None = None
    frame_max: int | None = None
    event_index_min: int | None = None
    event_index_max: int | None = None
    tick_min: int | None = None
    tick_max: int | None = None

    resource_path_count = 0
    resource_sha256_count = 0
    resource_identity_pair_count = 0
    resource_signature_count = 0
    captured_texture_snapshot_count = 0
    captured_cube_snapshot_count = 0

    unique_vertex_shader_hashes: set[str] = set()
    unique_pixel_shader_hashes: set[str] = set()
    target_pixel_hash_set = _target_pixel_hashes(target_inventory)
    matched_target_pixel_hashes: set[str] = set()
    target_pixel_creation_count = 0

    for raw_line in lines:
        text = raw_line.strip()
        if not text:
            continue
        nonempty_line_count += 1
        try:
            value, duplicates = _decode_line(text)
        except json.JSONDecodeError:
            invalid_json_count += 1
            continue
        if not isinstance(value, dict):
            non_object_count += 1
            continue

        if duplicates:
            duplicate_line_count += 1
            duplicate_key_counts.update(duplicates)

        event = str(value.get("event") or "<missing>")
        event_counts[event] += 1

        for key, current_min_name, current_max_name in (
            ("frame", "frame_min", "frame_max"),
            ("event_index", "event_index_min", "event_index_max"),
            ("tick_ms", "tick_min", "tick_max"),
        ):
            item = value.get(key)
            if not isinstance(item, int):
                continue
            if current_min_name == "frame_min":
                frame_min = item if frame_min is None else min(frame_min, item)
                frame_max = item if frame_max is None else max(frame_max, item)
            elif current_min_name == "event_index_min":
                event_index_min = (
                    item if event_index_min is None else min(event_index_min, item)
                )
                event_index_max = (
                    item if event_index_max is None else max(event_index_max, item)
                )
            else:
                tick_min = item if tick_min is None else min(tick_min, item)
                tick_max = item if tick_max is None else max(tick_max, item)

        has_path = isinstance(value.get("resource_path"), str) and bool(
            value.get("resource_path")
        )
        has_sha = isinstance(value.get("resource_sha256"), str) and bool(
            value.get("resource_sha256")
        )
        if has_path:
            resource_path_count += 1
        if has_sha:
            resource_sha256_count += 1
        if has_path and has_sha:
            resource_identity_pair_count += 1
        if isinstance(value.get("resource_signature"), str) and value.get(
            "resource_signature"
        ):
            resource_signature_count += 1

        if event in {"create_vertex_shader", "create_pixel_shader"}:
            digest = _shader_digest(value)
            if digest:
                if event == "create_vertex_shader":
                    unique_vertex_shader_hashes.add(digest)
                else:
                    unique_pixel_shader_hashes.add(digest)
                    if digest in target_pixel_hash_set:
                        target_pixel_creation_count += 1
                        matched_target_pixel_hashes.add(digest)

        if event == "set_texture":
            paths = [
                path
                for path in (value.get("snapshot_paths") or [])
                if isinstance(path, str) and path
            ]
            captured = value.get("snapshot_status") == "captured" and bool(paths)
            if captured:
                captured_texture_snapshot_count += 1
                if (
                    value.get("resource_type_name") == "cube_texture"
                    and len(paths) >= 6
                ):
                    captured_cube_snapshot_count += 1

    shader_prefilter_ready = (
        event_counts["create_pixel_shader"] > 0
        and event_counts["set_pixel_shader"] > 0
        and event_counts["draw_indexed_primitive"] > 0
    )
    programmable_draw_state_observed = all(
        event_counts[name] > 0
        for name in (
            "create_vertex_declaration",
            "set_vertex_declaration",
            "set_stream_source",
            "set_indices",
            "set_vertex_shader",
            "set_pixel_shader",
            "set_vertex_shader_constant_f",
            "draw_indexed_primitive",
        )
    )
    exact_resource_identity_observed = resource_identity_pair_count > 0
    sampler2d_snapshot_input_observed = (
        event_counts["create_texture"] > 0
        and captured_texture_snapshot_count > 0
    )
    sampler_cube_snapshot_input_observed = (
        event_counts["create_cube_texture"] > 0
        and captured_cube_snapshot_count > 0
    )
    buffer_payload_input_observed = event_counts["buffer_payload"] > 0

    phase598_raw_input_candidate = (
        shader_prefilter_ready
        and programmable_draw_state_observed
        and exact_resource_identity_observed
        and event_counts["set_vertex_shader_constant_f"] > 0
    )

    blockers: list[str] = []
    if not shader_prefilter_ready:
        blockers.append("shader-prefilter:required-events-missing")
    if not exact_resource_identity_observed:
        blockers.append("resource-identity:path-sha-pair-not-observed")
    if not sampler2d_snapshot_input_observed:
        blockers.append("sampler2d-snapshot:captured-ppm-not-observed")
    if not sampler_cube_snapshot_input_observed:
        blockers.append("sampler-cube-snapshot:six-face-capture-not-observed")
    if not buffer_payload_input_observed:
        blockers.append("buffer-payload:not-observed")
    if duplicate_line_count:
        blockers.append("json:duplicate-object-keys-observed")
    if invalid_json_count:
        blockers.append("json:invalid-lines-observed")
    if non_object_count:
        blockers.append("json:non-object-lines-observed")

    duration_ms = None
    if tick_min is not None and tick_max is not None:
        duration_ms = max(0, tick_max - tick_min)

    if (
        shader_prefilter_ready
        and not exact_resource_identity_observed
        and not sampler2d_snapshot_input_observed
        and not buffer_payload_input_observed
    ):
        profile = "shader-draw-state-only"
    elif phase598_raw_input_candidate:
        profile = "attribution-candidate"
    else:
        profile = "mixed"

    return {
        "format": FORMAT,
        "version": 1,
        "status": "observed" if nonempty_line_count else "not-supplied",
        "capture_profile": profile,
        "summary": {
            "nonempty_line_count": nonempty_line_count,
            "valid_object_count": sum(event_counts.values()),
            "invalid_json_count": invalid_json_count,
            "non_object_count": non_object_count,
            "duplicate_key_line_count": duplicate_line_count,
            "frame_min": frame_min,
            "frame_max": frame_max,
            "event_index_min": event_index_min,
            "event_index_max": event_index_max,
            "tick_min": tick_min,
            "tick_max": tick_max,
            "duration_ms": duration_ms,
            "unique_vertex_shader_count": len(unique_vertex_shader_hashes),
            "unique_pixel_shader_count": len(unique_pixel_shader_hashes),
            "resource_path_event_count": resource_path_count,
            "resource_sha256_event_count": resource_sha256_count,
            "exact_resource_identity_event_count": resource_identity_pair_count,
            "resource_signature_event_count": resource_signature_count,
            "captured_texture_snapshot_event_count": (
                captured_texture_snapshot_count
            ),
            "captured_cube_snapshot_event_count": captured_cube_snapshot_count,
        },
        "event_counts": dict(sorted(event_counts.items())),
        "duplicate_key_counts": dict(sorted(duplicate_key_counts.items())),
        "target_inventory": {
            "supplied": target_inventory is not None,
            "pixel_target_hash_count": len(target_pixel_hash_set),
            "matched_pixel_target_hash_count": len(
                matched_target_pixel_hashes
            ),
            "target_pixel_shader_creation_count": target_pixel_creation_count,
            "matched_pixel_target_hashes": sorted(
                matched_target_pixel_hashes
            ),
        },
        "capabilities": {
            "phase569_shader_prefilter_input": shader_prefilter_ready,
            "programmable_draw_state_observed": (
                programmable_draw_state_observed
            ),
            "exact_resource_identity_observed": (
                exact_resource_identity_observed
            ),
            "buffer_payload_input_observed": buffer_payload_input_observed,
            "phase590_sampler2d_snapshot_input": (
                sampler2d_snapshot_input_observed
            ),
            "phase593_sampler_cube_snapshot_input": (
                sampler_cube_snapshot_input_observed
            ),
            "phase598_raw_input_candidate": phase598_raw_input_candidate,
        },
        "blocking_reasons": blockers,
        "boundary": {
            "phase569_input_only": (
                "shader/draw readiness does not claim an IMB match"
            ),
            "phase590_input_only": (
                "snapshot presence does not claim scene sampler admission"
            ),
            "phase593_input_only": (
                "six captured paths do not claim cube provenance"
            ),
            "phase598_input_only": (
                "raw-input candidate does not replace Phase 595-598 proof gates"
            ),
            "resource_identity_requirement": (
                "resource_path + resource_sha256 on the same capture event"
            ),
        },
    }


def audit_capture_file(
    capture_path: str | Path,
    *,
    target_inventory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    with Path(capture_path).open("r", encoding="utf-8") as handle:
        return audit_capture_lines(handle, target_inventory=target_inventory)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_jsonl")
    parser.add_argument("output")
    parser.add_argument(
        "--target-inventory",
        help=(
            "optional JSON containing families[].pixel_shader_sha256 or "
            "IMBRuntimeShaderTargetSet unique_targets"
        ),
    )
    args = parser.parse_args(argv)

    target_inventory = None
    if args.target_inventory:
        target_inventory_path = resolve_input_path(args.target_inventory)
        target_inventory = json.loads(
            target_inventory_path.read_text(encoding="utf-8")
        )
        if not isinstance(target_inventory, dict):
            raise ValueError("target inventory must be a JSON object")

    report = audit_capture_file(
        args.capture_jsonl,
        target_inventory=target_inventory,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "format": report["format"],
                "status": report["status"],
                "capture_profile": report["capture_profile"],
                "summary": report["summary"],
                "capabilities": report["capabilities"],
                "target_inventory": report["target_inventory"],
                "blocking_reasons": report["blocking_reasons"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
