"""Join observed D3D9 target pipelines to static IMB shader candidates.

This is a pre-admission narrowing layer.  A unique static VS+PS candidate is
not sufficient to prove runtime resource, primitive, or same-instance identity.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.IMBRuntimePipelineCandidateJoin/1"
RUNTIME_FORMAT = "SHIFT.D3D9TargetDrawSignatureCatalog/1"
TARGET_FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"


def _valid_sha(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def resolve_input_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate

    repo_root = Path(__file__).resolve().parents[2]
    repo_candidate = repo_root / candidate
    if repo_candidate.exists():
        return repo_candidate

    raise FileNotFoundError(
        f"input file not found: {candidate} "
        f"(also tried {repo_candidate})"
    )


def _variant_key(
    binding_index: int,
    variant: Mapping[str, Any],
) -> tuple[Any, ...]:
    return (
        binding_index,
        _valid_sha(variant.get("vertex_byte_sha256")),
        _valid_sha(variant.get("pixel_byte_sha256")),
        _valid_sha(variant.get("pair_byte_sha256")),
        _valid_sha(variant.get("permutation_identity_sha256")),
        variant.get("candidate_file"),
        variant.get("candidate_program_offset"),
        variant.get("candidate_vertex_program_offset"),
    )


def _binding_candidate(
    binding: Mapping[str, Any],
    target: Mapping[str, Any],
    variant: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "binding_index": binding.get("binding_index"),
        "archive": binding.get("archive"),
        "imb_path": binding.get("imb_path"),
        "imb_sha256": _valid_sha(binding.get("imb_sha256")),
        "primitive_index": binding.get("primitive_index"),
        "draw_range": dict(binding.get("draw_range") or {}),
        "material_reference": binding.get("material_reference"),
        "bmt": binding.get("bmt"),
        "bmt_sha256": _valid_sha(binding.get("bmt_sha256")),
        "shader": binding.get("shader"),
        "shader_family": binding.get("shader_family"),
        "vertex_properties": list(binding.get("vertex_properties") or []),
        "property_descriptors": [
            dict(value)
            for value in (binding.get("property_descriptors") or [])
            if isinstance(value, Mapping)
        ],
        "resource_identity_ready": (
            binding.get("resource_identity_ready") is True
        ),
        "draw_range_ready": binding.get("draw_range_ready") is True,
        "same_instance_match_ready": (
            binding.get("same_instance_match_ready") is True
        ),
        "target_strength": target.get("strength"),
        "target_identity_kind": target.get("identity_kind"),
        "variant": {
            "vertex_byte_sha256": _valid_sha(
                variant.get("vertex_byte_sha256")
            ),
            "pixel_byte_sha256": _valid_sha(
                variant.get("pixel_byte_sha256")
            ),
            "pair_byte_sha256": _valid_sha(
                variant.get("pair_byte_sha256")
            ),
            "permutation_identity_sha256": _valid_sha(
                variant.get("permutation_identity_sha256")
            ),
            "candidate_file": variant.get("candidate_file"),
            "candidate_program_offset": variant.get(
                "candidate_program_offset"
            ),
            "candidate_vertex_program_offset": variant.get(
                "candidate_vertex_program_offset"
            ),
            "vertex_pair_selection_status": variant.get(
                "vertex_pair_selection_status"
            ),
            "exact": variant.get("exact") is True,
        },
    }


def _build_pair_index(
    target_set: Mapping[str, Any],
) -> tuple[
    dict[tuple[str, str], list[dict[str, Any]]],
    set[str],
    set[int],
]:
    pair_index: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ] = defaultdict(list)
    pixel_hashes: set[str] = set()
    binding_indices: set[int] = set()

    for binding in target_set.get("binding_targets") or []:
        if not isinstance(binding, Mapping):
            continue
        try:
            binding_index = int(binding.get("binding_index"))
        except (TypeError, ValueError):
            continue
        binding_indices.add(binding_index)
        seen_variants: set[tuple[Any, ...]] = set()

        for target in binding.get("targets") or []:
            if not isinstance(target, Mapping):
                continue

            variants = [
                value
                for value in (target.get("candidate_variants") or [])
                if isinstance(value, Mapping)
            ]
            if not variants:
                variants = [target]

            for variant in variants:
                vertex_sha = _valid_sha(
                    variant.get("vertex_byte_sha256")
                    or target.get("vertex_byte_sha256")
                )
                pixel_sha = _valid_sha(
                    variant.get("pixel_byte_sha256")
                    or target.get("pixel_byte_sha256")
                )
                if pixel_sha:
                    pixel_hashes.add(pixel_sha)
                if not vertex_sha or not pixel_sha:
                    continue

                merged_variant = dict(variant)
                merged_variant.setdefault(
                    "vertex_byte_sha256",
                    vertex_sha,
                )
                merged_variant.setdefault(
                    "pixel_byte_sha256",
                    pixel_sha,
                )
                key = _variant_key(binding_index, merged_variant)
                if key in seen_variants:
                    continue
                seen_variants.add(key)
                pair_index[(vertex_sha, pixel_sha)].append(
                    _binding_candidate(
                        binding,
                        target,
                        merged_variant,
                    )
                )

    for candidates in pair_index.values():
        candidates.sort(
            key=lambda row: (
                int(row.get("binding_index") or -1),
                str(row.get("variant", {}).get("candidate_file") or ""),
                int(
                    row.get("variant", {}).get(
                        "candidate_vertex_program_offset"
                    )
                    or -1
                ),
                int(
                    row.get("variant", {}).get(
                        "candidate_program_offset"
                    )
                    or -1
                ),
            )
        )

    return pair_index, pixel_hashes, binding_indices


def build_runtime_pipeline_candidate_join(
    runtime_catalog: Mapping[str, Any],
    target_set: Mapping[str, Any],
) -> dict[str, Any]:
    if runtime_catalog.get("format") != RUNTIME_FORMAT:
        raise ValueError(
            "runtime catalog must be "
            "SHIFT.D3D9TargetDrawSignatureCatalog/1"
        )
    if target_set.get("format") != TARGET_FORMAT:
        raise ValueError(
            "target set must be SHIFT.IMBRuntimeShaderTargetSet/1"
        )

    pair_index, static_pixel_hashes, static_bindings = (
        _build_pair_index(target_set)
    )
    rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    candidate_binding_count_distribution: Counter[int] = Counter()
    exact_pair_draw_count = 0
    single_binding_draw_count = 0
    exact_pair_pipeline_count = 0
    single_binding_pipeline_count = 0
    candidate_binding_indices: set[int] = set()

    for pipeline in runtime_catalog.get("pipeline_signatures") or []:
        if not isinstance(pipeline, Mapping):
            continue
        signature = pipeline.get("signature")
        if not isinstance(signature, Mapping):
            continue

        vertex_sha = _valid_sha(
            signature.get("vertex_shader_sha256")
        )
        pixel_sha = _valid_sha(
            signature.get("pixel_shader_sha256")
        )
        draw_count = int(pipeline.get("draw_count") or 0)
        candidates = (
            list(pair_index.get((vertex_sha, pixel_sha), []))
            if vertex_sha and pixel_sha
            else []
        )
        binding_ids = sorted({
            int(value["binding_index"])
            for value in candidates
            if isinstance(value.get("binding_index"), int)
        })

        if candidates:
            status = (
                "single-static-binding-candidate"
                if len(binding_ids) == 1
                else "ambiguous-static-binding-candidates"
            )
            exact_pair_pipeline_count += 1
            exact_pair_draw_count += draw_count
            candidate_binding_count_distribution[
                len(binding_ids)
            ] += 1
            candidate_binding_indices.update(binding_ids)
            if len(binding_ids) == 1:
                single_binding_pipeline_count += 1
                single_binding_draw_count += draw_count
        elif pixel_sha and pixel_sha in static_pixel_hashes:
            status = "pixel-only-static-overlap"
        else:
            status = "no-static-pair-candidate"

        status_counts[status] += 1
        runtime_families = sorted({
            str(value)
            for value in (pipeline.get("families") or [])
            if value
        })
        candidate_families = sorted({
            str(value.get("shader_family"))
            for value in candidates
            if value.get("shader_family")
        })

        rows.append({
            "runtime_signature_sha256": pipeline.get(
                "signature_sha256"
            ),
            "draw_count": draw_count,
            "primitive_count_sum": int(
                pipeline.get("primitive_count_sum") or 0
            ),
            "first_frame": pipeline.get("first_frame"),
            "last_frame": pipeline.get("last_frame"),
            "vertex_shader_sha256": vertex_sha,
            "pixel_shader_sha256": pixel_sha,
            "declaration_sha256": _valid_sha(
                signature.get("declaration_sha256")
            ),
            "stream_layout": list(
                signature.get("stream_layout") or []
            ),
            "index_format": signature.get("index_format"),
            "runtime_families": runtime_families,
            "candidate_families": candidate_families,
            "family_consistent": (
                not candidates
                or bool(
                    set(runtime_families)
                    & set(candidate_families)
                )
            ),
            "status": status,
            "candidate_binding_count": len(binding_ids),
            "candidate_variant_count": len(candidates),
            "candidate_binding_indices": binding_ids,
            "candidates": candidates,
        })

    rows.sort(
        key=lambda row: (
            -int(row.get("draw_count") or 0),
            str(row.get("runtime_signature_sha256") or ""),
        )
    )
    runtime_pipeline_count = len(rows)
    runtime_draw_count = sum(
        int(row.get("draw_count") or 0)
        for row in rows
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "observed" if rows else "not-observed",
        "summary": {
            "runtime_pipeline_signature_count": runtime_pipeline_count,
            "runtime_draw_count": runtime_draw_count,
            "static_binding_count": len(static_bindings),
            "static_vs_ps_pair_count": len(pair_index),
            "exact_vs_ps_candidate_pipeline_count": (
                exact_pair_pipeline_count
            ),
            "exact_vs_ps_candidate_draw_count": exact_pair_draw_count,
            "single_static_binding_candidate_pipeline_count": (
                single_binding_pipeline_count
            ),
            "single_static_binding_candidate_draw_count": (
                single_binding_draw_count
            ),
            "distinct_static_candidate_binding_count": len(
                candidate_binding_indices
            ),
            "status_counts": dict(sorted(status_counts.items())),
            "candidate_binding_count_distribution": {
                str(count): pipelines
                for count, pipelines in sorted(
                    candidate_binding_count_distribution.items()
                )
            },
        },
        "pipeline_candidates": rows,
        "boundary": {
            "candidate_only": True,
            "render_admission": False,
            "resource_identity": "not evaluated",
            "primitive_identity": "not evaluated",
            "same_instance_identity": "not evaluated",
            "single_static_binding_candidate": (
                "one static binding shares the exact observed VS+PS "
                "byte hashes; this is not runtime same-instance proof"
            ),
            "required_for_promotion": (
                "exact runtime IMB resource identity + exact primitive "
                "draw range + existing Phase 572 strong match gates"
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime_catalog")
    parser.add_argument("target_set")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    runtime_path = resolve_input_path(args.runtime_catalog)
    target_path = resolve_input_path(args.target_set)
    runtime_catalog = json.loads(
        runtime_path.read_text(encoding="utf-8")
    )
    target_set = json.loads(target_path.read_text(encoding="utf-8"))
    if not isinstance(runtime_catalog, dict):
        raise ValueError("runtime catalog must be a JSON object")
    if not isinstance(target_set, dict):
        raise ValueError("target set must be a JSON object")

    report = build_runtime_pipeline_candidate_join(
        runtime_catalog,
        target_set,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
