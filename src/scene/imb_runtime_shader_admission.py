"""Admit runtime-proven IMB shader variants back to exact static bindings.

This layer does not build RenderCommand objects. It validates that every
attributed Phase 572 result maps back to the exact Phase 571/570 binding and to
one preserved static shader-variant identity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

FORMAT = "SHIFT.IMBRuntimeShaderAdmission/1"
TARGET_FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"
MATCH_FORMAT = "SHIFT.IMBRuntimeShaderVariantMatch/1"


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _variant_key(row: Mapping[str, Any]) -> tuple[str, ...]:
    permutation = row.get("permutation_identity_sha256")
    if permutation:
        return ("permutation", str(permutation))
    pair = row.get("pair_byte_sha256")
    if pair:
        return ("pair", str(pair))
    vertex = row.get("vertex_byte_sha256")
    pixel = row.get("pixel_byte_sha256")
    return ("stages", str(vertex or ""), str(pixel or ""))


def _candidate_variants(binding: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for target in binding.get("targets") or []:
        if not isinstance(target, Mapping):
            continue
        for variant in target.get("candidate_variants") or []:
            if isinstance(variant, Mapping):
                rows.append(variant)
    return rows


def _draw_range_equal(left: Any, right: Any) -> bool:
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        return False
    try:
        return (
            int(left.get("first_index")) == int(right.get("first_index"))
            and int(left.get("index_count")) == int(right.get("index_count"))
            and int(left.get("primitive_count"))
            == int(right.get("primitive_count"))
        )
    except (TypeError, ValueError):
        return False


def build_imb_runtime_shader_admission(
    target_set: Mapping[str, Any],
    match_reports: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    if target_set.get("format") != TARGET_FORMAT:
        raise ValueError(
            "target input must be SHIFT.IMBRuntimeShaderTargetSet/1"
        )

    by_binding = {
        int(row.get("binding_index")): row
        for row in (target_set.get("binding_targets") or [])
        if isinstance(row, Mapping) and row.get("binding_index") is not None
    }

    admitted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    blockers: list[str] = []
    seen_results = 0
    attributed_results = 0

    for report_index, report in enumerate(match_reports):
        if report.get("format") != MATCH_FORMAT:
            blockers.append(
                f"match-{report_index}:format-invalid"
            )
            continue
        resource = report.get("target_resource") or {}
        report_path = _norm(resource.get("resource_path"))
        report_sha = str(resource.get("resource_sha256") or "").lower()

        for result in report.get("binding_results") or []:
            if not isinstance(result, Mapping):
                continue
            seen_results += 1
            raw_index = result.get("binding_index")
            try:
                binding_index = int(raw_index)
            except (TypeError, ValueError):
                rejected.append({
                    "match_index": report_index,
                    "binding_index": raw_index,
                    "blocking_reasons": ["binding-index-invalid"],
                })
                continue

            binding = by_binding.get(binding_index)
            reasons: list[str] = []
            if binding is None:
                reasons.append("binding-not-in-target-set")
            if result.get("attributed") is not True:
                reasons.append("runtime-result-not-attributed")

            selected = result.get("selected_variant")
            if not isinstance(selected, Mapping):
                reasons.append("selected-variant-missing")
                selected = {}

            try:
                score = int(selected.get("score"))
            except (TypeError, ValueError):
                score = 0
            if score < 80:
                reasons.append("selected-variant-not-strong")

            if binding is not None:
                binding_path = _norm(binding.get("imb_path"))
                binding_sha = str(binding.get("imb_sha256") or "").lower()
                if not report_path or report_path != binding_path:
                    reasons.append("runtime-resource-path-mismatch")
                if not report_sha or report_sha != binding_sha:
                    reasons.append("runtime-resource-sha256-mismatch")
                if _norm(result.get("imb_path")) != binding_path:
                    reasons.append("result-resource-path-mismatch")
                if str(result.get("imb_sha256") or "").lower() != binding_sha:
                    reasons.append("result-resource-sha256-mismatch")
                if result.get("primitive_index") != binding.get("primitive_index"):
                    reasons.append("primitive-index-mismatch")
                if not _draw_range_equal(
                    result.get("draw_range"),
                    binding.get("draw_range"),
                ):
                    reasons.append("draw-range-mismatch")
                if binding.get("same_instance_match_ready") is not True:
                    reasons.append("static-binding-not-match-ready")

            equivalent_variants: list[Mapping[str, Any]] = []
            selected_key = _variant_key(selected)
            if selected_key[-1] == "":
                reasons.append("selected-variant-identity-missing")
            elif binding is not None:
                equivalent_variants = [
                    variant
                    for variant in _candidate_variants(binding)
                    if _variant_key(variant) == selected_key
                ]
                if not equivalent_variants:
                    reasons.append(
                        "selected-variant-not-in-static-target-set"
                    )

            if reasons:
                rejected.append({
                    "match_index": report_index,
                    "binding_index": binding_index,
                    "blocking_reasons": list(dict.fromkeys(reasons)),
                    "selected_variant": dict(selected),
                })
                continue

            attributed_results += 1
            locations = sorted({
                (
                    str(row.get("candidate_file") or ""),
                    row.get("candidate_program_offset"),
                    row.get("candidate_vertex_program_offset"),
                )
                for row in equivalent_variants
            })
            admitted.append({
                "match_index": report_index,
                "binding_index": binding_index,
                "archive": binding.get("archive"),
                "imb_path": binding.get("imb_path"),
                "imb_sha256": binding.get("imb_sha256"),
                "primitive_index": binding.get("primitive_index"),
                "draw_range": dict(binding.get("draw_range") or {}),
                "material_reference": binding.get("material_reference"),
                "bmt": binding.get("bmt"),
                "bmt_sha256": binding.get("bmt_sha256"),
                "shader": binding.get("shader"),
                "shader_family": binding.get("shader_family"),
                "selected_variant": dict(selected),
                "selected_variant_key": list(selected_key),
                "equivalent_static_locations": [
                    {
                        "file": file,
                        "program_offset": offset,
                        "vertex_program_offset": vertex_offset,
                    }
                    for file, offset, vertex_offset in locations
                ],
                "shader_selection_admitted": True,
                "render_admission": False,
            })

    admitted.sort(key=lambda row: int(row["binding_index"]))
    rejected.sort(
        key=lambda row: (
            int(row["binding_index"])
            if isinstance(row.get("binding_index"), int)
            else 1 << 30
        )
    )

    if blockers:
        status = "blocked"
    elif admitted and not rejected:
        status = "ready"
    elif admitted:
        status = "partial"
    else:
        status = "not-admitted"

    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": status == "ready",
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "summary": {
            "match_result_count": seen_results,
            "runtime_attributed_result_count": attributed_results,
            "admitted_binding_count": len(admitted),
            "rejected_binding_count": len(rejected),
        },
        "admitted_bindings": admitted,
        "rejected_bindings": rejected,
        "boundary": {
            "requires_phase572_attribution": True,
            "requires_exact_static_binding_identity": True,
            "requires_static_variant_membership": True,
            "minimum_runtime_score": 80,
            "render_admission": False,
            "purpose": (
                "authorize one runtime-proven static shader identity for "
                "later MaterialBinding reconstruction"
            ),
        },
    }


def validate_files(
    target_set_path: str | Path,
    match_paths: Iterable[str | Path],
) -> dict[str, Any]:
    target_set = json.loads(
        Path(target_set_path).read_text(encoding="utf-8")
    )
    reports = [
        json.loads(Path(path).read_text(encoding="utf-8"))
        for path in match_paths
    ]
    return build_imb_runtime_shader_admission(target_set, reports)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target_set")
    parser.add_argument("matches", nargs="+")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args(argv)

    report = validate_files(args.target_set, args.matches)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
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
