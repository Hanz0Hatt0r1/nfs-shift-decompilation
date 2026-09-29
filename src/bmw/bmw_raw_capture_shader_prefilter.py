"""Fast BMW shader/draw prefilter for raw native D3D9 JSONL captures.

This layer intentionally does not establish resource or same-instance proof.
It only answers whether a capture contains shader bytes and indexed draw ranges
worth sending through the full runtime-evidence pipeline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

FORMAT = "SHIFT.BMWRawCaptureShaderPrefilter/1"
TARGET_FORMAT = "SHIFT.BMWRuntimeShaderTargetSet/1"

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


def _target_draws(target_set: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        row
        for row in (target_set.get("primitive_targets") or [])
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
    if vertex:
        evidence.append("vertex_byte_sha256")
    if pixel:
        evidence.append("pixel_byte_sha256")
    if exact_pair_target and vertex and pixel:
        return 80, evidence
    if vertex or pixel:
        return 40, evidence
    return 0, []


def prefilter_bmw_raw_capture(
    target_set: Mapping[str, Any],
    events: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    if target_set.get("format") != TARGET_FORMAT:
        raise ValueError(
            "target input must be SHIFT.BMWRuntimeShaderTargetSet/1"
        )

    primitive_targets = _target_draws(target_set)
    primitive_matches: dict[int, list[dict[str, Any]]] = {
        int(row["primitive_index"]): []
        for row in primitive_targets
    }

    shader_objects: dict[tuple[str, str], dict[str, Any]] = {}
    active: dict[str, dict[str, str | None]] = {}
    target_vertex = {
        str(target.get("vertex_byte_sha256"))
        for primitive in primitive_targets
        for target in (primitive.get("targets") or [])
        if isinstance(target, Mapping) and target.get("vertex_byte_sha256")
    }
    target_pixel = {
        str(target.get("pixel_byte_sha256"))
        for primitive in primitive_targets
        for target in (primitive.get("targets") or [])
        if isinstance(target, Mapping) and target.get("pixel_byte_sha256")
    }

    creation_hits: list[dict[str, Any]] = []
    blockers: list[str] = []
    event_count = 0
    draw_count = 0

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
                    f"raw-prefilter:line-{line_index}:{stage}-shader-create-invalid"
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
                    f"raw-prefilter:line-{line_index}:{stage}-shader-pointer-reused"
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
        try:
            start_index = int(row.get("start_index"))
            primitive_count = int(row.get("primitive_count"))
        except (TypeError, ValueError):
            blockers.append(
                f"raw-prefilter:line-{line_index}:draw-range-invalid"
            )
            continue
        index_count = primitive_count * 3
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

        for primitive in primitive_targets:
            primitive_index = int(primitive["primitive_index"])
            draw_range = primitive.get("draw_range") or {}
            try:
                expected_first = int(draw_range.get("first_index"))
                expected_count = int(draw_range.get("index_count"))
            except (TypeError, ValueError):
                continue
            if (
                start_index != expected_first
                or index_count != expected_count
            ):
                continue

            for target in primitive.get("targets") or []:
                if not isinstance(target, Mapping):
                    continue
                score, evidence = _score_target(
                    target, vertex_sha, pixel_sha, pair_sha
                )
                if score <= 0:
                    continue
                primitive_matches[primitive_index].append({
                    "line": line_index,
                    "frame": row.get("frame"),
                    "event_index": row.get("event_index"),
                    "device_ptr": row.get("device_ptr"),
                    "start_index": start_index,
                    "index_count": index_count,
                    "score": score,
                    "evidence": evidence,
                    "target_identity_kind": target.get("identity_kind"),
                    "target_identity_value": target.get("identity_value"),
                    "target_strength": target.get("strength"),
                    "vertex_shader_ptr": state.get("vertex"),
                    "pixel_shader_ptr": state.get("pixel"),
                    "vertex_byte_sha256": vertex_sha,
                    "pixel_byte_sha256": pixel_sha,
                    "pair_byte_sha256": pair_sha,
                })

    primitive_results: list[dict[str, Any]] = []
    covered = 0
    strong = 0
    for primitive in primitive_targets:
        primitive_index = int(primitive["primitive_index"])
        rows = primitive_matches.get(primitive_index, [])
        best_score = max(
            (int(row["score"]) for row in rows),
            default=None,
        )
        if rows:
            covered += 1
        if best_score is not None and best_score >= 80:
            strong += 1
        primitive_results.append({
            "primitive_index": primitive_index,
            "material_ref": primitive.get("material_ref"),
            "draw_range": primitive.get("draw_range"),
            "observed": bool(rows),
            "strong_pair_observed": (
                best_score is not None and best_score >= 80
            ),
            "best_score": best_score,
            "match_count": len(rows),
            "matches": rows,
        })

    coverage_ready = (
        bool(primitive_results)
        and covered == len(primitive_results)
        and not blockers
    )
    status = (
        "complete"
        if coverage_ready
        else ("partial" if covered else ("blocked" if blockers else "not-found"))
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "coverage_ready": coverage_ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "summary": {
            "event_count": event_count,
            "draw_count": draw_count,
            "created_shader_count": len(shader_objects),
            "target_shader_creation_hit_count": len(creation_hits),
            "primitive_count": len(primitive_results),
            "covered_primitive_count": covered,
            "strong_pair_primitive_count": strong,
        },
        "shader_creation_hits": creation_hits,
        "primitive_results": primitive_results,
        "boundary": {
            "resource_identity_proven": False,
            "same_instance_proven": False,
            "selects_permutation": False,
            "next_stage": "SHIFT.D3D9RuntimeBindingEvidence/1 -> Phase 539",
        },
    }


def load_jsonl(path: str | Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_index, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                errors.append(
                    f"raw-prefilter:line-{line_index}:json-invalid"
                )
                continue
            if not isinstance(value, dict):
                errors.append(
                    f"raw-prefilter:line-{line_index}:event-not-object"
                )
                continue
            rows.append(value)
    return rows, errors


def validate_files(
    target_set_path: str | Path,
    capture_jsonl_path: str | Path,
) -> dict[str, Any]:
    target_set = json.loads(
        Path(target_set_path).read_text(encoding="utf-8")
    )
    rows, load_errors = load_jsonl(capture_jsonl_path)
    report = prefilter_bmw_raw_capture(target_set, rows)
    if load_errors:
        report["blocking_reasons"] = list(dict.fromkeys(
            [*load_errors, *report["blocking_reasons"]]
        ))
        report["coverage_ready"] = False
        report["status"] = "blocked"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prefilter raw SHIFT D3D9 JSONL for BMW shader/draw targets"
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
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "coverage_ready": report["coverage_ready"],
        "summary": report["summary"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["coverage_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
