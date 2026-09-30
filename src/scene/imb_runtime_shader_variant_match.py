"""Match IMB runtime shader targets against draw-local D3D9 evidence.

This matcher is per exact IMB resource runtime report. Attribution requires the
D3D9 same-instance gate, exact primitive draw range and one uniquely matching
static shader candidate variant. Pixel-only hits remain prefilter evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from runtime_resource_identity import match_resource_identity

FORMAT = "SHIFT.IMBRuntimeShaderVariantMatch/1"
TARGET_FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"
RUNTIME_FORMAT = "SHIFT.D3D9RuntimeBindingEvidence/1"


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _runtime_resource_identity(
    runtime: Mapping[str, Any],
) -> dict[str, Any] | None:
    correlation = runtime.get("resource_correlation")
    if not isinstance(correlation, Mapping):
        correlation = runtime.get("meb_correlation")
    if not isinstance(correlation, Mapping):
        return None
    identity = correlation.get("resource_identity")
    if not isinstance(identity, Mapping):
        return None
    path = identity.get("resource_path")
    sha = identity.get("resource_sha256")
    if not path or not sha:
        return None
    return {
        "resource_path": str(path).replace("\\", "/"),
        "resource_sha256": str(sha).lower(),
    }


def _runtime_hashes(state: Mapping[str, Any]) -> dict[str, str | None]:
    identity = state.get("shader_permutation_identity") or {}
    if not isinstance(identity, Mapping):
        identity = {}
    payload = identity.get("payload") or {}
    if not isinstance(payload, Mapping):
        payload = {}
    vertex = payload.get("vertex") or {}
    pixel = payload.get("pixel") or {}
    if not isinstance(vertex, Mapping):
        vertex = {}
    if not isinstance(pixel, Mapping):
        pixel = {}
    return {
        "permutation": (
            str(identity.get("identity_sha256"))
            if identity.get("identity_sha256") else None
        ),
        "pair": (
            str(identity.get("pair_byte_sha256"))
            if identity.get("pair_byte_sha256") else None
        ),
        "vertex": (
            str(identity.get("vertex_byte_sha256"))
            if identity.get("vertex_byte_sha256")
            else str(vertex.get("byte_sha256"))
            if vertex.get("byte_sha256") else None
        ),
        "pixel": (
            str(identity.get("pixel_byte_sha256"))
            if identity.get("pixel_byte_sha256")
            else str(pixel.get("byte_sha256"))
            if pixel.get("byte_sha256") else None
        ),
    }


def _variant_key(variant: Mapping[str, Any]) -> tuple[str, ...]:
    permutation = variant.get("permutation_identity_sha256")
    if permutation:
        return ("permutation", str(permutation))
    pair = variant.get("pair_byte_sha256")
    if pair:
        return ("pair", str(pair))
    vertex = variant.get("vertex_byte_sha256")
    pixel = variant.get("pixel_byte_sha256")
    return ("stages", str(vertex or ""), str(pixel or ""))


def _variant_score(
    variant: Mapping[str, Any],
    hashes: Mapping[str, str | None],
) -> tuple[int, list[str]]:
    permutation = variant.get("permutation_identity_sha256")
    if permutation and hashes.get("permutation") == permutation:
        return 100, ["permutation_identity_sha256"]
    pair = variant.get("pair_byte_sha256")
    if pair and hashes.get("pair") == pair:
        return 90, ["pair_byte_sha256"]

    vertex = bool(
        variant.get("vertex_byte_sha256")
        and hashes.get("vertex") == variant.get("vertex_byte_sha256")
    )
    pixel = bool(
        variant.get("pixel_byte_sha256")
        and hashes.get("pixel") == variant.get("pixel_byte_sha256")
    )
    evidence: list[str] = []
    if vertex:
        evidence.append("vertex_byte_sha256")
    if pixel:
        evidence.append("pixel_byte_sha256")
    if vertex and pixel:
        return 80, evidence
    if pixel:
        return 40, evidence
    if vertex:
        return 35, evidence
    return 0, []


def _gate_rows(runtime: Mapping[str, Any]) -> dict[tuple[Any, Any], Mapping[str, Any]]:
    gate = runtime.get("same_instance_gate") or {}
    if not isinstance(gate, Mapping) or gate.get("ready") is not True:
        return {}
    rows: dict[tuple[Any, Any], Mapping[str, Any]] = {}
    for row in gate.get("candidate_frames") or []:
        if not isinstance(row, Mapping):
            continue
        same_resource = (
            row.get("same_resource") is True
            or row.get("same_meb_resource") is True
        )
        if not same_resource:
            continue
        if row.get("bound_declaration_valid") is not True:
            continue
        descriptors = row.get("descriptor_matches")
        if not isinstance(descriptors, list) or not descriptors:
            continue
        if row.get("snapshot_schema_status") not in (None, "valid"):
            continue
        rows[(row.get("frame"), row.get("draw_index"))] = row
    return rows


def _draw_snapshots(
    runtime: Mapping[str, Any],
) -> Iterable[tuple[Mapping[str, Any], Mapping[str, Any]]]:
    for frame in runtime.get("frames") or []:
        if not isinstance(frame, Mapping):
            continue
        for snapshot in frame.get("draw_snapshots") or []:
            if not isinstance(snapshot, Mapping):
                continue
            if snapshot.get("format") not in (None, "SHIFT.D3D9DrawStateSnapshot/1"):
                continue
            yield frame, snapshot


def _draw_matches(
    draw: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> bool:
    try:
        start_index = int(draw.get("start_index"))
        primitive_count = int(draw.get("primitive_count"))
        first_index = int(expected.get("first_index"))
        index_count = int(expected.get("index_count"))
    except (TypeError, ValueError):
        return False
    return (
        index_count > 0
        and index_count % 3 == 0
        and start_index == first_index
        and primitive_count == index_count // 3
    )


def _target_variants(target: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = [
        row
        for row in (target.get("candidate_variants") or [])
        if isinstance(row, Mapping)
    ]
    return rows


def match_imb_runtime_shader_variants(
    target_set: Mapping[str, Any],
    runtime: Mapping[str, Any],
) -> dict[str, Any]:
    if target_set.get("format") != TARGET_FORMAT:
        raise ValueError(
            "target input must be SHIFT.IMBRuntimeShaderTargetSet/1"
        )
    if runtime.get("format") != RUNTIME_FORMAT:
        raise ValueError(
            "runtime input must be SHIFT.D3D9RuntimeBindingEvidence/1"
        )

    resource = _runtime_resource_identity(runtime)
    gate = runtime.get("same_instance_gate") or {}
    gate_rows = _gate_rows(runtime)
    blockers: list[str] = []
    if resource is None:
        blockers.append("runtime-resource-identity-missing")
    if not isinstance(gate, Mapping) or gate.get("ready") is not True:
        blockers.append("same-instance-gate-not-ready")
    elif not gate_rows:
        blockers.append("same-instance-gate-has-no-declaration-proven-draws")

    bindings: list[Mapping[str, Any]] = []
    if resource is not None:
        for row in target_set.get("binding_targets") or []:
            if not isinstance(row, Mapping):
                continue
            if (
                _norm(row.get("imb_path")) == _norm(resource["resource_path"])
                and str(row.get("imb_sha256") or "").lower()
                == resource["resource_sha256"]
            ):
                bindings.append(row)
    if resource is not None and not bindings:
        blockers.append("target-resource-not-found")

    matches: dict[int, list[dict[str, Any]]] = {
        int(row.get("binding_index")): []
        for row in bindings
    }

    for frame, snapshot in _draw_snapshots(runtime):
        frame_id = frame.get("frame")
        draw_index = snapshot.get("draw_index")
        gate_row = gate_rows.get((frame_id, draw_index))
        if gate_row is None:
            continue
        binding = snapshot.get("vertex_declaration") or {}
        if resource is None:
            continue
        same_resource, resource_status = match_resource_identity(
            binding,
            expected_sha256=resource["resource_sha256"],
            expected_path=resource["resource_path"],
        )
        if same_resource is not True:
            continue
        draw = snapshot.get("draw") or {}
        hashes = _runtime_hashes(snapshot)

        for target_binding in bindings:
            binding_index = int(target_binding.get("binding_index"))
            draw_range = target_binding.get("draw_range") or {}
            if not _draw_matches(draw, draw_range):
                continue

            variant_rows: list[dict[str, Any]] = []
            for target in target_binding.get("targets") or []:
                if not isinstance(target, Mapping):
                    continue
                for variant in _target_variants(target):
                    score, evidence = _variant_score(variant, hashes)
                    if score <= 0:
                        continue
                    variant_rows.append({
                        "score": score,
                        "evidence": evidence,
                        "variant_key": list(_variant_key(variant)),
                        "identity_kind": target.get("identity_kind"),
                        "identity_value": target.get("identity_value"),
                        "strength": target.get("strength"),
                        "permutation_identity_sha256": variant.get(
                            "permutation_identity_sha256"
                        ),
                        "pair_byte_sha256": variant.get("pair_byte_sha256"),
                        "vertex_byte_sha256": variant.get(
                            "vertex_byte_sha256"
                        ),
                        "pixel_byte_sha256": variant.get(
                            "pixel_byte_sha256"
                        ),
                        "candidate_file": variant.get("candidate_file"),
                        "candidate_program_offset": variant.get(
                            "candidate_program_offset"
                        ),
                    })

            if not variant_rows:
                continue
            matches[binding_index].append({
                "frame": frame_id,
                "draw_index": draw_index,
                "draw": dict(draw),
                "resource_identity_status": resource_status,
                "gate_descriptor_match_count": len(
                    gate_row.get("descriptor_matches") or []
                ),
                "runtime_hashes": dict(hashes),
                "variant_matches": sorted(
                    variant_rows,
                    key=lambda item: (-int(item["score"]), item["variant_key"]),
                ),
            })

    results: list[dict[str, Any]] = []
    attributed_count = 0
    observed_count = 0
    for target_binding in bindings:
        binding_index = int(target_binding.get("binding_index"))
        rows = matches.get(binding_index, [])
        if rows:
            observed_count += 1

        strong: list[dict[str, Any]] = []
        for row in rows:
            for variant in row["variant_matches"]:
                if int(variant["score"]) >= 80:
                    strong.append({
                        **variant,
                        "frame": row["frame"],
                        "draw_index": row["draw_index"],
                    })
        best_score = max(
            (int(row["score"]) for row in strong),
            default=None,
        )
        best = [
            row for row in strong
            if best_score is not None and int(row["score"]) == best_score
        ]
        keys = {tuple(row["variant_key"]) for row in best}
        attributed = (
            not blockers
            and best_score is not None
            and len(keys) == 1
        )

        reasons: list[str] = []
        if not rows:
            reasons.append("draw-or-shader-not-observed")
        elif not strong:
            reasons.append("only-prefilter-hash-matched")
        elif len(keys) != 1:
            reasons.append("multiple-strong-variants")
        if blockers:
            reasons.extend(blockers)

        selected = None
        if attributed:
            attributed_count += 1
            first = best[0]
            selected = {
                key: first.get(key)
                for key in (
                    "score",
                    "evidence",
                    "variant_key",
                    "permutation_identity_sha256",
                    "pair_byte_sha256",
                    "vertex_byte_sha256",
                    "pixel_byte_sha256",
                    "candidate_file",
                    "candidate_program_offset",
                )
            }

        results.append({
            "binding_index": binding_index,
            "primitive_index": target_binding.get("primitive_index"),
            "imb_path": target_binding.get("imb_path"),
            "imb_sha256": target_binding.get("imb_sha256"),
            "draw_range": target_binding.get("draw_range"),
            "material_reference": target_binding.get("material_reference"),
            "shader_family": target_binding.get("shader_family"),
            "observed": bool(rows),
            "attributed": attributed,
            "best_score": best_score,
            "selected_variant": selected,
            "match_count": len(rows),
            "strong_variant_match_count": len(strong),
            "blocking_reasons": list(dict.fromkeys(reasons)),
            "matches": rows,
        })

    ready = (
        bool(results)
        and attributed_count == len(results)
        and not blockers
    )
    status = (
        "ready" if ready
        else "partial" if observed_count
        else "blocked" if blockers
        else "not-found"
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "target_resource": resource,
        "summary": {
            "resource_binding_count": len(bindings),
            "observed_binding_count": observed_count,
            "attributed_binding_count": attributed_count,
            "blocked_binding_count": len(bindings) - attributed_count,
            "same_instance_candidate_draw_count": len(gate_rows),
        },
        "binding_results": results,
        "boundary": {
            "report_scope": "one exact IMB resource identity",
            "requires_same_instance_gate": True,
            "requires_declaration_descriptor_proof": True,
            "requires_exact_draw_range": True,
            "minimum_attribution_score": 80,
            "pixel_prefilter_score": 40,
            "selects_permutation_only_when_unique_strong_variant": True,
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
    return match_imb_runtime_shader_variants(target_set, runtime)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Match IMB shader variants against D3D9 draw evidence"
    )
    parser.add_argument("target_set")
    parser.add_argument("runtime_report")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_files(args.target_set, args.runtime_report)
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "
",
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
