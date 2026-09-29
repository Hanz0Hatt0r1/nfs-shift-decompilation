"""Match BMW runtime shader targets against same-instance D3D9 draws."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from bmw_runtime_shader_join import _runtime_draw_states
from runtime_resource_identity import match_resource_identity

FORMAT = "SHIFT.BMWRuntimeShaderTargetMatch/1"
TARGET_FORMAT = "SHIFT.BMWRuntimeShaderTargetSet/1"
RUNTIME_FORMAT = "SHIFT.D3D9RuntimeBindingEvidence/1"


def _runtime_hashes(state: Mapping[str, Any]) -> dict[str, str | None]:
    identity = state.get("shader_permutation_identity") or {}
    payload = identity.get("payload") if isinstance(identity, Mapping) else {}
    vertex = payload.get("vertex") if isinstance(payload, Mapping) else {}
    pixel = payload.get("pixel") if isinstance(payload, Mapping) else {}
    return {
        "permutation": (
            str(identity.get("identity_sha256"))
            if isinstance(identity, Mapping)
            and identity.get("identity_sha256")
            else None
        ),
        "pair": (
            str(identity.get("pair_byte_sha256"))
            if isinstance(identity, Mapping)
            and identity.get("pair_byte_sha256")
            else None
        ),
        "vertex": (
            str(vertex.get("byte_sha256"))
            if isinstance(vertex, Mapping) and vertex.get("byte_sha256")
            else None
        ),
        "pixel": (
            str(pixel.get("byte_sha256"))
            if isinstance(pixel, Mapping) and pixel.get("byte_sha256")
            else None
        ),
    }


def _target_match(
    target: Mapping[str, Any],
    hashes: Mapping[str, str | None],
) -> tuple[int, list[str]]:
    evidence: list[str] = []
    exact_pair_target = target.get("strength") == "exact-pair"
    if (
        exact_pair_target
        and hashes.get("permutation")
        and target.get("permutation_identity_sha256")
        and hashes["permutation"] == target["permutation_identity_sha256"]
    ):
        return 100, ["permutation_identity_sha256"]
    if (
        exact_pair_target
        and hashes.get("pair")
        and target.get("pair_byte_sha256")
        and hashes["pair"] == target["pair_byte_sha256"]
    ):
        return 90, ["pair_byte_sha256"]

    vertex = bool(
        hashes.get("vertex")
        and target.get("vertex_byte_sha256")
        and hashes["vertex"] == target["vertex_byte_sha256"]
    )
    pixel = bool(
        hashes.get("pixel")
        and target.get("pixel_byte_sha256")
        and hashes["pixel"] == target["pixel_byte_sha256"]
    )
    if vertex:
        evidence.append("vertex_byte_sha256")
    if pixel:
        evidence.append("pixel_byte_sha256")
    if exact_pair_target and vertex and pixel:
        return 80, evidence
    if vertex or pixel:
        return 40, evidence
    return 0, []


def _draw_rows(
    state: Mapping[str, Any],
    source: str,
) -> list[tuple[int | None, Mapping[str, Any]]]:
    if source == "draw-snapshot":
        draw = state.get("draw")
        return [
            (state.get("draw_index"), draw)
        ] if isinstance(draw, Mapping) else []
    return [
        (index, draw)
        for index, draw in enumerate(state.get("draws") or [])
        if isinstance(draw, Mapping)
    ]


def _same_instance_draws(runtime: Mapping[str, Any]) -> set[tuple[Any, Any]]:
    gate = runtime.get("same_instance_gate") or {}
    return {
        (row.get("frame"), row.get("draw_index"))
        for row in (gate.get("candidate_frames") or [])
        if isinstance(row, Mapping)
    }


def match_bmw_runtime_shader_targets(
    target_set: Mapping[str, Any],
    runtime_report: Mapping[str, Any],
) -> dict[str, Any]:
    if target_set.get("format") != TARGET_FORMAT:
        raise ValueError("target input must be SHIFT.BMWRuntimeShaderTargetSet/1")
    if runtime_report.get("format") != RUNTIME_FORMAT:
        raise ValueError("runtime input must be SHIFT.D3D9RuntimeBindingEvidence/1")

    resource = target_set.get("target_resource") or {}
    expected_path = resource.get("path")
    expected_sha = resource.get("sha256")
    same_instance = _same_instance_draws(runtime_report)
    same_instance_gate = runtime_report.get("same_instance_gate") or {}

    primitive_targets = [
        row
        for row in (target_set.get("primitive_targets") or [])
        if isinstance(row, Mapping)
    ]
    matches_by_primitive: dict[int, list[dict[str, Any]]] = {
        int(row["primitive_index"]): []
        for row in primitive_targets
    }

    for frame, state, source in _runtime_draw_states(
        runtime_report,
        reject_invalid_snapshots=True,
    ):
        binding = state.get("vertex_declaration") or state.get("binding") or {}
        resource_match, resource_status = match_resource_identity(
            binding,
            expected_sha256=expected_sha,
            expected_path=expected_path,
        )
        if resource_match is not True:
            continue

        hashes = _runtime_hashes(state)
        if not any(hashes.values()):
            continue

        for draw_index, draw in _draw_rows(state, source):
            try:
                start_index = int(draw.get("start_index"))
                primitive_count = int(draw.get("primitive_count"))
            except (TypeError, ValueError, AttributeError):
                continue
            index_count = primitive_count * 3

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
                    score, evidence = _target_match(target, hashes)
                    if score <= 0:
                        continue
                    proven_same_instance = (
                        (frame.get("frame"), draw_index) in same_instance
                    )
                    matches_by_primitive[primitive_index].append({
                        "frame": frame.get("frame"),
                        "draw_index": draw_index,
                        "source": source,
                        "start_index": start_index,
                        "index_count": index_count,
                        "resource_identity_status": resource_status,
                        "same_instance": proven_same_instance,
                        "score": score,
                        "evidence": evidence,
                        "target_identity_kind": target.get("identity_kind"),
                        "target_identity_value": target.get("identity_value"),
                        "target_strength": target.get("strength"),
                        "runtime_hashes": dict(hashes),
                    })

    primitive_results: list[dict[str, Any]] = []
    top_blockers: list[str] = []
    attributed_count = 0
    observed_count = 0

    for primitive in primitive_targets:
        primitive_index = int(primitive["primitive_index"])
        rows = matches_by_primitive.get(primitive_index, [])
        if rows:
            observed_count += 1

        proven = [
            row
            for row in rows
            if row["same_instance"] and int(row["score"]) >= 80
        ]
        best_score = max(
            (int(row["score"]) for row in proven),
            default=None,
        )
        best = [
            row for row in proven
            if best_score is not None and int(row["score"]) == best_score
        ]
        unique_identities = {
            (
                row.get("target_identity_kind"),
                row.get("target_identity_value"),
            )
            for row in best
        }

        attributed = (
            same_instance_gate.get("ready") is True
            and best_score is not None
            and len(unique_identities) == 1
        )
        reasons: list[str] = []
        if not rows:
            reasons.append(
                f"runtime-target:primitive-{primitive_index}:draw-hash-not-observed"
            )
        elif not any(row["same_instance"] for row in rows):
            reasons.append(
                f"runtime-target:primitive-{primitive_index}:same-instance-not-proven"
            )
        elif not proven:
            reasons.append(
                f"runtime-target:primitive-{primitive_index}:only-prefilter-hash-matched"
            )
        elif len(unique_identities) != 1:
            reasons.append(
                f"runtime-target:primitive-{primitive_index}:multiple-strong-identities"
            )
        if same_instance_gate.get("ready") is not True:
            reasons.append("runtime-target:same-instance-gate-not-ready")

        if attributed:
            attributed_count += 1
        else:
            top_blockers.extend(reasons)

        selected_identity = None
        if attributed and best:
            selected_identity = {
                "kind": best[0]["target_identity_kind"],
                "value": best[0]["target_identity_value"],
                "score": best_score,
                "evidence": best[0]["evidence"],
            }

        primitive_results.append({
            "primitive_index": primitive_index,
            "material_ref": primitive.get("material_ref"),
            "draw_range": primitive.get("draw_range"),
            "observed": bool(rows),
            "attributed": attributed,
            "selected_identity": selected_identity,
            "best_score": best_score,
            "match_count": len(rows),
            "strong_same_instance_match_count": len(proven),
            "blocking_reasons": list(dict.fromkeys(reasons)),
            "matches": rows,
        })

    complete = (
        bool(primitive_results)
        and attributed_count == len(primitive_results)
        and target_set.get("capture_ready") is True
        and same_instance_gate.get("ready") is True
        and not top_blockers
    )
    status = (
        "ready"
        if complete
        else ("partial" if observed_count else "not-found")
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": complete,
        "blocking_reasons": list(dict.fromkeys(top_blockers)),
        "target_resource": dict(resource),
        "runtime": {
            "same_instance_gate_ready": same_instance_gate.get("ready") is True,
            "same_instance_candidate_count": len(same_instance),
            "frame_count": len(runtime_report.get("frames") or []),
        },
        "summary": {
            "primitive_count": len(primitive_results),
            "observed_primitive_count": observed_count,
            "attributed_primitive_count": attributed_count,
            "blocked_primitive_count": len(primitive_results) - attributed_count,
        },
        "primitive_results": primitive_results,
        "boundary": {
            "requires_exact_draw_range": True,
            "requires_exact_resource_identity": True,
            "requires_same_instance_gate_for_attribution": True,
            "minimum_attribution_score": 80,
            "prefilter_only_score": 40,
        },
    }


def validate_files(
    target_set_path: str | Path,
    runtime_report_path: str | Path,
) -> dict[str, Any]:
    target_set = json.loads(
        Path(target_set_path).read_text(encoding="utf-8")
    )
    runtime = json.loads(
        Path(runtime_report_path).read_text(encoding="utf-8")
    )
    return match_bmw_runtime_shader_targets(target_set, runtime)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Match BMW shader target set against D3D9 draw snapshots"
    )
    parser.add_argument("target_set")
    parser.add_argument("runtime_report")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_files(args.target_set, args.runtime_report)
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "summary": report["summary"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
