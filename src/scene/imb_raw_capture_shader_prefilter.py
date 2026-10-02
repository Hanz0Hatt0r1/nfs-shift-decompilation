"""Fast IMB/Silverstone shader prefilter for raw native D3D9 JSONL captures.

The prefilter consumes SHIFT.IMBRuntimeShaderTargetSet/1 and keeps only draws
whose active shader bytes match one or more capture targets. It deliberately
does not claim resource identity, draw-range identity or same-instance proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

FORMAT = "SHIFT.IMBRawCaptureShaderPrefilter/1"
TARGET_FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"

_CREATE_EVENTS = {
    "create_vertex_shader": "vertex",
    "create_pixel_shader": "pixel",
}
_SET_EVENTS = {
    "set_vertex_shader": "vertex",
    "set_pixel_shader": "pixel",
}


def _decode_shader_bytes(row: Mapping[str, Any]) -> bytes | None:
    raw = row.get("bytes_hex")
    if not isinstance(raw, str) or not raw or len(raw) % 2:
        return None
    try:
        return bytes.fromhex(raw)
    except ValueError:
        return None


def _unique_targets(
    target_set: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    return [
        row
        for row in (target_set.get("unique_targets") or [])
        if isinstance(row, Mapping)
    ]


def _score_target(
    target: Mapping[str, Any],
    vertex_sha: str | None,
    pixel_sha: str | None,
    pair_sha: str | None,
) -> tuple[int, list[str]]:
    exact_pair_target = target.get("strength") == "exact-pair"
    if (
        exact_pair_target
        and pair_sha
        and target.get("pair_byte_sha256") == pair_sha
    ):
        return 90, ["pair_byte_sha256"]

    vertex = bool(
        vertex_sha
        and target.get("vertex_byte_sha256")
        and target.get("vertex_byte_sha256") == vertex_sha
    )
    pixel = bool(
        pixel_sha
        and target.get("pixel_byte_sha256")
        and target.get("pixel_byte_sha256") == pixel_sha
    )
    evidence: list[str] = []
    if exact_pair_target:
        if vertex:
            evidence.append("vertex_byte_sha256")
        if pixel:
            evidence.append("pixel_byte_sha256")
        if vertex and pixel:
            return 80, evidence
        return (40, evidence) if evidence else (0, [])

    identity_kind = str(target.get("identity_kind") or "")
    identity_value = str(target.get("identity_value") or "")
    if identity_kind == "pixel" and pixel_sha == identity_value:
        return 40, ["pixel_byte_sha256"]
    if identity_kind == "vertex" and vertex_sha == identity_value:
        return 40, ["vertex_byte_sha256"]
    return 0, []


def _target_indexes(
    targets: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, list[Mapping[str, Any]]]]:
    result = {
        "vertex": {},
        "pixel": {},
        "pair": {},
    }
    for target in targets:
        strength = str(target.get("strength") or "")
        identity_kind = str(target.get("identity_kind") or "")
        identity_value = str(target.get("identity_value") or "")
        vertex = target.get("vertex_byte_sha256")
        pixel = target.get("pixel_byte_sha256")
        pair = target.get("pair_byte_sha256")

        if strength == "exact-pair":
            if vertex:
                result["vertex"].setdefault(
                    str(vertex), []
                ).append(target)
            if pixel:
                result["pixel"].setdefault(
                    str(pixel), []
                ).append(target)
            if pair:
                result["pair"].setdefault(
                    str(pair), []
                ).append(target)
            continue

        if identity_kind == "vertex" and identity_value:
            result["vertex"].setdefault(
                identity_value, []
            ).append(target)
        elif identity_kind == "pixel" and identity_value:
            result["pixel"].setdefault(
                identity_value, []
            ).append(target)
    return result


def _candidate_targets(
    indexes: Mapping[str, Mapping[str, list[Mapping[str, Any]]]],
    *,
    vertex_sha: str | None,
    pixel_sha: str | None,
    pair_sha: str | None,
) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for stage, digest in (
        ("pair", pair_sha),
        ("vertex", vertex_sha),
        ("pixel", pixel_sha),
    ):
        if not digest:
            continue
        for target in (indexes.get(stage) or {}).get(digest, []):
            key = (
                str(target.get("identity_kind") or ""),
                str(target.get("identity_value") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            rows.append(target)
    return rows


def prefilter_imb_raw_capture(
    target_set: Mapping[str, Any],
    events: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    if target_set.get("format") != TARGET_FORMAT:
        raise ValueError(
            "target input must be SHIFT.IMBRuntimeShaderTargetSet/1"
        )

    targets = _unique_targets(target_set)
    indexes = _target_indexes(targets)
    shader_objects: dict[tuple[str, str], dict[str, Any]] = {}
    active: dict[str, dict[str, str | None]] = {}

    target_vertex = set(indexes["vertex"])
    target_pixel = set(indexes["pixel"])
    creation_hits: list[dict[str, Any]] = []
    candidate_draws: list[dict[str, Any]] = []
    blockers: list[str] = []
    observed_target_keys: set[tuple[str, str]] = set()
    observed_binding_indices: set[int] = set()

    if not targets:
        blockers.append("imb-raw-prefilter:no-target-hashes")
    if target_set.get("capture_ready") is not True:
        blockers.append("imb-raw-prefilter:target-set-not-capture-ready")

    event_count = 0
    draw_count = 0
    draw_ordinal = 0

    for line_index, row in enumerate(events, 1):
        event_count += 1
        event = str(row.get("event") or "")
        device = str(row.get("device_ptr") or "<unknown-device>")

        if event in _CREATE_EVENTS:
            stage = _CREATE_EVENTS[event]
            pointer = row.get("shader_ptr")
            payload = _decode_shader_bytes(row)
            if not pointer or payload is None:
                blockers.append(
                    f"imb-raw-prefilter:line-{line_index}:"
                    f"{stage}-shader-create-invalid"
                )
                continue
            pointer = str(pointer)
            digest = hashlib.sha256(payload).hexdigest()
            key = (stage, pointer)
            previous = shader_objects.get(key)
            if (
                previous is not None
                and previous["byte_sha256"] != digest
            ):
                blockers.append(
                    f"imb-raw-prefilter:line-{line_index}:"
                    f"{stage}-shader-pointer-reused"
                )
            shader_objects[key] = {
                "stage": stage,
                "pointer": pointer,
                "byte_sha256": digest,
                "payload": payload,
                "line": line_index,
                "frame": row.get("frame"),
            }
            wanted = target_vertex if stage == "vertex" else target_pixel
            if digest in wanted:
                creation_hits.append({
                    "line": line_index,
                    "frame": row.get("frame"),
                    "event_index": row.get("event_index"),
                    "stage": stage,
                    "shader_ptr": pointer,
                    "byte_sha256": digest,
                })
            continue

        if event in _SET_EVENTS:
            stage = _SET_EVENTS[event]
            state = active.setdefault(
                device, {"vertex": None, "pixel": None}
            )
            pointer = row.get("shader_ptr")
            state[stage] = str(pointer) if pointer else None
            continue

        if event != "draw_indexed_primitive":
            continue

        draw_count += 1
        draw_ordinal += 1
        state = active.get(
            device, {"vertex": None, "pixel": None}
        )
        vertex_obj = (
            shader_objects.get(("vertex", state.get("vertex")))
            if state.get("vertex") else None
        )
        pixel_obj = (
            shader_objects.get(("pixel", state.get("pixel")))
            if state.get("pixel") else None
        )
        vertex_sha = (
            vertex_obj.get("byte_sha256") if vertex_obj else None
        )
        pixel_sha = (
            pixel_obj.get("byte_sha256") if pixel_obj else None
        )
        pair_sha = None
        if vertex_obj and pixel_obj:
            pair_sha = hashlib.sha256(
                vertex_obj["payload"] + pixel_obj["payload"]
            ).hexdigest()

        matched_targets: list[dict[str, Any]] = []
        binding_indices: set[int] = set()
        shader_families: set[str] = set()
        for target in _candidate_targets(
            indexes,
            vertex_sha=vertex_sha,
            pixel_sha=pixel_sha,
            pair_sha=pair_sha,
        ):
            score, evidence = _score_target(
                target, vertex_sha, pixel_sha, pair_sha
            )
            if score <= 0:
                continue

            kind = str(target.get("identity_kind") or "")
            value = str(target.get("identity_value") or "")
            observed_target_keys.add((kind, value))
            target_bindings = sorted({
                int(index)
                for index in (target.get("binding_indices") or [])
            })
            target_families = sorted({
                str(family)
                for family in (target.get("shader_families") or [])
                if family
            })
            binding_indices.update(target_bindings)
            shader_families.update(target_families)
            matched_targets.append({
                "score": score,
                "evidence": evidence,
                "identity_kind": kind,
                "identity_value": value,
                "strength": target.get("strength"),
                "binding_indices": target_bindings,
                "shader_families": target_families,
            })

        if not matched_targets:
            continue

        observed_binding_indices.update(binding_indices)
        candidate_draws.append({
            "line": line_index,
            "frame": row.get("frame"),
            "event_index": row.get("event_index"),
            "draw_ordinal": draw_ordinal,
            "device_ptr": row.get("device_ptr"),
            "primitive_type": row.get("primitive_type"),
            "base_vertex_index": row.get("base_vertex_index"),
            "min_vertex_index": row.get("min_vertex_index"),
            "num_vertices": row.get("num_vertices"),
            "start_index": row.get("start_index"),
            "primitive_count": row.get("primitive_count"),
            "vertex_shader_ptr": state.get("vertex"),
            "pixel_shader_ptr": state.get("pixel"),
            "vertex_byte_sha256": vertex_sha,
            "pixel_byte_sha256": pixel_sha,
            "pair_byte_sha256": pair_sha,
            "matched_target_count": len(matched_targets),
            "candidate_binding_indices": sorted(binding_indices),
            "shader_families": sorted(shader_families),
            "matches": sorted(
                matched_targets,
                key=lambda item: (
                    -int(item["score"]),
                    str(item["identity_kind"]),
                    str(item["identity_value"]),
                ),
            ),
        })

    prefilter_ready = (
        target_set.get("capture_ready") is True
        and bool(targets)
        and not blockers
    )
    status = (
        "blocked"
        if blockers
        else "matched"
        if candidate_draws
        else "not-found"
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "prefilter_ready": prefilter_ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "summary": {
            "event_count": event_count,
            "draw_count": draw_count,
            "created_shader_count": len(shader_objects),
            "target_shader_creation_hit_count": len(creation_hits),
            "candidate_draw_count": len(candidate_draws),
            "target_hash_count": len(targets),
            "observed_target_hash_count": len(observed_target_keys),
            "target_binding_count": int(
                target_set.get("binding_target_count") or 0
            ),
            "candidate_binding_index_count": len(
                observed_binding_indices
            ),
        },
        "shader_creation_hits": creation_hits,
        "candidate_draws": candidate_draws,
        "boundary": {
            "resource_identity_proven": False,
            "draw_range_identity_proven": False,
            "same_instance_proven": False,
            "selects_permutation": False,
            "purpose": (
                "reduce raw D3D9 capture to draws whose active shader "
                "bytes intersect the IMB runtime target whitelist"
            ),
            "next_stage": (
                "build SHIFT.D3D9RuntimeBindingEvidence/1 for candidate "
                "draws, then perform per-IMB same-instance attribution"
            ),
        },
    }


def iter_jsonl(
    path: str | Path,
    errors: list[str] | None = None,
) -> Iterable[dict[str, Any]]:
    """Yield JSONL objects while preserving non-fatal parse diagnostics."""
    diagnostics = errors if errors is not None else []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_index, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                diagnostics.append(
                    f"imb-raw-prefilter:line-{line_index}:json-invalid"
                )
                continue
            if not isinstance(value, dict):
                diagnostics.append(
                    f"imb-raw-prefilter:line-{line_index}:event-not-object"
                )
                continue
            yield value


def load_jsonl(
    path: str | Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    return list(iter_jsonl(path, errors)), errors


def validate_files(
    target_set_path: str | Path,
    capture_jsonl_path: str | Path,
) -> dict[str, Any]:
    target_set = json.loads(
        Path(target_set_path).read_text(encoding="utf-8")
    )
    load_errors: list[str] = []
    report = prefilter_imb_raw_capture(
        target_set,
        iter_jsonl(capture_jsonl_path, load_errors),
    )
    if load_errors:
        report["blocking_reasons"] = list(dict.fromkeys(
            [*load_errors, *report["blocking_reasons"]]
        ))
        report["prefilter_ready"] = False
        report["status"] = "blocked"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prefilter raw SHIFT D3D9 JSONL by IMB runtime shader targets"
        )
    )
    parser.add_argument("target_set")
    parser.add_argument("capture_jsonl")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_files(
        args.target_set,
        args.capture_jsonl,
    )
    Path(args.output).write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "prefilter_ready": report["prefilter_ready"],
        "summary": report["summary"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["prefilter_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
