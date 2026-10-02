"""Join observed D3D9 target pipelines to static IMB shader candidates.

This is a pre-admission narrowing layer.  Exact VS+PS matches are preferred.
When a static target is only pixel-hash observable, the fallback also requires
the source-backed IMB runtime vertex stride to match stream 0.  Neither path
proves runtime resource, primitive, or same-instance identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
_SOURCE_PATHS = [REPOSITORY_ROOT, SOURCE_ROOT]
if SOURCE_ROOT.is_dir():
    _SOURCE_PATHS.extend(
        sorted(
            (path for path in SOURCE_ROOT.rglob("*") if path.is_dir()),
            key=lambda path: (len(path.parts), str(path)),
        )
    )
for _source_path in reversed(_SOURCE_PATHS):
    _source_value = str(_source_path)
    if _source_value not in sys.path:
        sys.path.insert(0, _source_value)

from imb_neutral_geometry import (
    runtime_interleaved_stride_for_properties,
)

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


def _runtime_stream0_stride(signature: Mapping[str, Any]) -> int | None:
    for row in signature.get("stream_layout") or []:
        if not isinstance(row, Mapping):
            continue
        try:
            stream = int(row.get("stream"))
            stride = int(row.get("stride"))
        except (TypeError, ValueError):
            continue
        if stream == 0 and stride > 0:
            return stride
    return None


def _complete_runtime_draw_ranges(
    pipeline: Mapping[str, Any],
) -> tuple[set[tuple[int, int]] | None, str]:
    full = pipeline.get("observed_draw_ranges")
    if isinstance(full, list) and full:
        values: set[tuple[int, int]] = set()
        for row in full:
            if not isinstance(row, Mapping):
                continue
            try:
                start_index = int(row.get("start_index"))
                primitive_count = int(row.get("primitive_count"))
            except (TypeError, ValueError):
                continue
            if start_index >= 0 and primitive_count >= 0:
                values.add((start_index, primitive_count))
        if values:
            return values, "observed_draw_ranges"

    top = pipeline.get("top_draw_ranges")
    distinct = pipeline.get("distinct_draw_range_count")
    if (
        isinstance(top, list)
        and top
        and isinstance(distinct, int)
        and distinct == len(top)
    ):
        values = set()
        for row in top:
            if not isinstance(row, Mapping):
                continue
            try:
                start_index = int(row.get("start_index"))
                primitive_count = int(row.get("primitive_count"))
            except (TypeError, ValueError):
                continue
            if start_index >= 0 and primitive_count >= 0:
                values.add((start_index, primitive_count))
        if values:
            return values, "complete-top-draw-ranges"

    return None, "unavailable-or-truncated"


def _filter_candidates_by_draw_range(
    candidates: list[dict[str, Any]],
    observed: set[tuple[int, int]] | None,
) -> list[dict[str, Any]]:
    if not candidates or observed is None:
        return list(candidates)

    filtered = []
    for candidate in candidates:
        draw_range = candidate.get("draw_range")
        if not isinstance(draw_range, Mapping):
            continue
        try:
            first_index = int(draw_range.get("first_index"))
            primitive_count = int(draw_range.get("primitive_count"))
        except (TypeError, ValueError):
            continue
        if (first_index, primitive_count) in observed:
            filtered.append(candidate)
    return filtered


def _binding_summary(binding: Mapping[str, Any]) -> dict[str, Any]:
    properties = [
        str(value)
        for value in (binding.get("vertex_properties") or [])
    ]
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
        "vertex_properties": properties,
        "static_vertex_stride": (
            runtime_interleaved_stride_for_properties(properties)
        ),
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
    }


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


def _target_pixel_sha(
    target: Mapping[str, Any],
    variant: Mapping[str, Any] | None = None,
) -> str | None:
    variant = variant or {}
    return _valid_sha(
        variant.get("pixel_byte_sha256")
        or target.get("pixel_byte_sha256")
        or (
            target.get("identity_value")
            if target.get("identity_kind") == "pixel"
            else None
        )
    )


def _compact_match(
    binding: Mapping[str, Any],
    target: Mapping[str, Any],
    *,
    evidence_kind: str,
    matched_variant_count: int,
    vertex_sha: str | None,
    pixel_sha: str | None,
    pair_sha: str | None = None,
    permutation_sha: str | None = None,
) -> dict[str, Any]:
    return {
        **_binding_summary(binding),
        "evidence_kind": evidence_kind,
        "target_strength": target.get("strength"),
        "target_identity_kind": target.get("identity_kind"),
        "target_identity_value": target.get("identity_value"),
        "matched_variant_count": int(matched_variant_count),
        "matched_vertex_shader_sha256": vertex_sha,
        "matched_pixel_shader_sha256": pixel_sha,
        "matched_pair_byte_sha256": pair_sha,
        "matched_permutation_identity_sha256": permutation_sha,
    }


def _finalize_index(
    raw: Mapping[Any, Mapping[int, dict[str, Any]]],
) -> dict[Any, list[dict[str, Any]]]:
    out: dict[Any, list[dict[str, Any]]] = {}
    for key, by_binding in raw.items():
        rows = []
        for candidate in by_binding.values():
            row = dict(candidate)
            variant_keys = row.pop("_variant_keys", set())
            row["matched_variant_count"] = len(variant_keys)
            rows.append(row)
        rows.sort(
            key=lambda row: int(row.get("binding_index") or -1)
        )
        out[key] = rows
    return out


def _build_static_indices(
    target_set: Mapping[str, Any],
) -> tuple[
    dict[tuple[str, str], list[dict[str, Any]]],
    dict[tuple[str, int], list[dict[str, Any]]],
    set[str],
    set[int],
]:
    pair_raw: dict[
        tuple[str, str],
        dict[int, dict[str, Any]],
    ] = defaultdict(dict)
    pixel_stride_raw: dict[
        tuple[str, int],
        dict[int, dict[str, Any]],
    ] = defaultdict(dict)
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
        summary = _binding_summary(binding)
        static_stride = summary.get("static_vertex_stride")

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

            target_pixel = _target_pixel_sha(target)
            if target_pixel:
                pixel_hashes.add(target_pixel)

            # Strong path: every concrete variant with exact VS+PS bytes.
            for variant in variants:
                vertex_sha = _valid_sha(
                    variant.get("vertex_byte_sha256")
                    or target.get("vertex_byte_sha256")
                )
                pixel_sha = _target_pixel_sha(target, variant)
                if pixel_sha:
                    pixel_hashes.add(pixel_sha)
                if not vertex_sha or not pixel_sha:
                    continue

                key = (vertex_sha, pixel_sha)
                candidate = pair_raw[key].get(binding_index)
                variant_key = _variant_key(binding_index, variant)
                if candidate is None:
                    candidate = _compact_match(
                        binding,
                        target,
                        evidence_kind="exact-vs+ps",
                        matched_variant_count=0,
                        vertex_sha=vertex_sha,
                        pixel_sha=pixel_sha,
                        pair_sha=_valid_sha(
                            variant.get("pair_byte_sha256")
                            or target.get("pair_byte_sha256")
                        ),
                        permutation_sha=_valid_sha(
                            variant.get("permutation_identity_sha256")
                            or target.get(
                                "permutation_identity_sha256"
                            )
                        ),
                    )
                    candidate["_variant_keys"] = set()
                    pair_raw[key][binding_index] = candidate
                candidate["_variant_keys"].add(variant_key)

            # Weak but source-constrained path: only targets whose static
            # contract itself is prefilter-only may fall back to PS+stride.
            if (
                target.get("strength") == "prefilter-only"
                and target_pixel
                and isinstance(static_stride, int)
                and static_stride > 0
            ):
                key = (target_pixel, static_stride)
                candidate = pixel_stride_raw[key].get(binding_index)
                if candidate is None:
                    candidate = _compact_match(
                        binding,
                        target,
                        evidence_kind="pixel+static-vertex-stride",
                        matched_variant_count=0,
                        vertex_sha=None,
                        pixel_sha=target_pixel,
                    )
                    candidate["_variant_keys"] = set()
                    pixel_stride_raw[key][binding_index] = candidate
                for variant in variants:
                    candidate["_variant_keys"].add(
                        _variant_key(binding_index, variant)
                    )

    return (
        _finalize_index(pair_raw),
        _finalize_index(pixel_stride_raw),
        pixel_hashes,
        binding_indices,
    )


def _binding_ids(candidates: list[Mapping[str, Any]]) -> list[int]:
    return sorted({
        int(value["binding_index"])
        for value in candidates
        if isinstance(value.get("binding_index"), int)
    })


def _candidate_content_key(
    candidate: Mapping[str, Any],
) -> tuple[Any, ...]:
    imb_sha = _valid_sha(candidate.get("imb_sha256"))
    bmt_sha = _valid_sha(candidate.get("bmt_sha256"))
    draw_range = candidate.get("draw_range")
    if not isinstance(draw_range, Mapping):
        draw_range = {}
    try:
        first_index = int(draw_range.get("first_index"))
    except (TypeError, ValueError):
        first_index = None
    try:
        index_count = int(draw_range.get("index_count"))
    except (TypeError, ValueError):
        index_count = None
    try:
        primitive_count = int(draw_range.get("primitive_count"))
    except (TypeError, ValueError):
        primitive_count = None

    # A missing payload SHA must never collapse unrelated bindings.
    fallback_binding = (
        None
        if imb_sha is not None
        else candidate.get("binding_index")
    )
    return (
        imb_sha,
        fallback_binding,
        candidate.get("primitive_index"),
        first_index,
        index_count,
        primitive_count,
        bmt_sha,
        candidate.get("shader_family"),
        candidate.get("static_vertex_stride"),
        tuple(candidate.get("vertex_properties") or []),
        _valid_sha(candidate.get("matched_vertex_shader_sha256")),
        _valid_sha(candidate.get("matched_pixel_shader_sha256")),
    )


def _content_group_sha(key: tuple[Any, ...]) -> str:
    payload = json.dumps(
        key,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _candidate_content_groups(
    candidates: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    for candidate in candidates:
        key = _candidate_content_key(candidate)
        group = groups.setdefault(key, {
            "content_group_sha256": _content_group_sha(key),
            "imb_sha256": _valid_sha(candidate.get("imb_sha256")),
            "primitive_index": candidate.get("primitive_index"),
            "draw_range": dict(candidate.get("draw_range") or {}),
            "bmt_sha256": _valid_sha(candidate.get("bmt_sha256")),
            "shader_family": candidate.get("shader_family"),
            "static_vertex_stride": candidate.get("static_vertex_stride"),
            "matched_vertex_shader_sha256": _valid_sha(
                candidate.get("matched_vertex_shader_sha256")
            ),
            "matched_pixel_shader_sha256": _valid_sha(
                candidate.get("matched_pixel_shader_sha256")
            ),
            "binding_indices": [],
            "archives": [],
            "imb_paths": [],
        })
        binding_index = candidate.get("binding_index")
        if (
            isinstance(binding_index, int)
            and binding_index not in group["binding_indices"]
        ):
            group["binding_indices"].append(binding_index)
        archive = candidate.get("archive")
        if archive and archive not in group["archives"]:
            group["archives"].append(archive)
        imb_path = candidate.get("imb_path")
        if imb_path and imb_path not in group["imb_paths"]:
            group["imb_paths"].append(imb_path)

    result = list(groups.values())
    for group in result:
        group["binding_indices"].sort()
        group["archives"].sort()
        group["imb_paths"].sort()
        group["static_binding_count"] = len(group["binding_indices"])
    result.sort(
        key=lambda row: (
            -int(row.get("static_binding_count") or 0),
            str(row.get("content_group_sha256") or ""),
        )
    )
    return result


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

    (
        pair_index,
        pixel_stride_index,
        static_pixel_hashes,
        static_bindings,
    ) = _build_static_indices(target_set)

    rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    candidate_binding_count_distribution: Counter[int] = Counter()
    exact_pair_draw_count = 0
    exact_pair_pipeline_count = 0
    layout_pixel_draw_count = 0
    layout_pixel_pipeline_count = 0
    single_binding_draw_count = 0
    single_binding_pipeline_count = 0
    single_content_group_draw_count = 0
    single_content_group_pipeline_count = 0
    candidate_content_group_count_distribution: Counter[int] = Counter()
    distinct_content_group_sha256s: set[str] = set()
    draw_range_gate_pipeline_count = 0
    draw_range_gate_reduced_pipeline_count = 0
    draw_range_gate_rejected_pipeline_count = 0
    final_candidate_pipeline_count = 0
    final_candidate_draw_count = 0
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
        runtime_stride = _runtime_stream0_stride(signature)
        draw_count = int(pipeline.get("draw_count") or 0)

        exact_candidates = (
            list(pair_index.get((vertex_sha, pixel_sha), []))
            if vertex_sha and pixel_sha
            else []
        )
        layout_candidates = (
            list(
                pixel_stride_index.get(
                    (pixel_sha, runtime_stride),
                    [],
                )
            )
            if pixel_sha and isinstance(runtime_stride, int)
            else []
        )

        evidence_kind = "none"
        if exact_candidates:
            base_candidates = exact_candidates
            evidence_kind = "exact-vs+ps"
            exact_pair_pipeline_count += 1
            exact_pair_draw_count += draw_count
        elif layout_candidates:
            base_candidates = layout_candidates
            evidence_kind = "pixel+static-vertex-stride"
            layout_pixel_pipeline_count += 1
            layout_pixel_draw_count += draw_count
        else:
            base_candidates = []

        runtime_draw_ranges, draw_range_source = (
            _complete_runtime_draw_ranges(pipeline)
        )
        pre_draw_range_binding_ids = _binding_ids(base_candidates)
        candidates = _filter_candidates_by_draw_range(
            base_candidates,
            runtime_draw_ranges,
        )
        draw_range_gate_status = "not-applied"
        if base_candidates and runtime_draw_ranges is not None:
            draw_range_gate_pipeline_count += 1
            if len(candidates) < len(base_candidates):
                draw_range_gate_reduced_pipeline_count += 1
                draw_range_gate_status = "reduced"
            else:
                draw_range_gate_status = "matched-all"
            if not candidates:
                draw_range_gate_rejected_pipeline_count += 1
                draw_range_gate_status = "rejected-all"
            evidence_kind = f"{evidence_kind}+draw-range"

        binding_ids = _binding_ids(candidates)
        content_groups = _candidate_content_groups(candidates)
        content_group_count = len(content_groups)
        content_status = "none"
        if candidates:
            candidate_content_group_count_distribution[
                content_group_count
            ] += 1
            distinct_content_group_sha256s.update(
                str(group["content_group_sha256"])
                for group in content_groups
            )
            if content_group_count == 1:
                content_status = "single-content-candidate"
                single_content_group_pipeline_count += 1
                single_content_group_draw_count += draw_count
            else:
                content_status = "ambiguous-content-candidates"
            final_candidate_pipeline_count += 1
            final_candidate_draw_count += draw_count
            if evidence_kind.startswith("exact-vs+ps"):
                status = (
                    "single-static-binding-candidate"
                    if len(binding_ids) == 1
                    else "ambiguous-static-binding-candidates"
                )
            else:
                status = (
                    "single-layout-pixel-static-binding-candidate"
                    if len(binding_ids) == 1
                    else "layout-pixel-static-binding-candidates"
                )
            candidate_binding_count_distribution[
                len(binding_ids)
            ] += 1
            candidate_binding_indices.update(binding_ids)
            if len(binding_ids) == 1:
                single_binding_pipeline_count += 1
                single_binding_draw_count += draw_count
        elif base_candidates:
            status = "draw-range-rejected-static-overlap"
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
            "runtime_vertex_stride": runtime_stride,
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
            "candidate_evidence_kind": evidence_kind,
            "draw_range_gate_status": draw_range_gate_status,
            "runtime_draw_range_source": draw_range_source,
            "runtime_draw_ranges": (
                [
                    {
                        "start_index": start_index,
                        "primitive_count": primitive_count,
                    }
                    for start_index, primitive_count in sorted(
                        runtime_draw_ranges
                    )
                ]
                if runtime_draw_ranges is not None
                else []
            ),
            "pre_draw_range_candidate_binding_count": len(
                pre_draw_range_binding_ids
            ),
            "status": status,
            "candidate_binding_count": len(binding_ids),
            "candidate_content_group_count": content_group_count,
            "candidate_content_status": content_status,
            "candidate_content_groups": content_groups,
            "candidate_variant_count": sum(
                int(value.get("matched_variant_count") or 0)
                for value in candidates
            ),
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
    candidate_pipeline_count = final_candidate_pipeline_count
    candidate_draw_count = final_candidate_draw_count

    return {
        "format": FORMAT,
        "version": 1,
        "status": "observed" if rows else "not-observed",
        "summary": {
            "runtime_pipeline_signature_count": runtime_pipeline_count,
            "runtime_draw_count": runtime_draw_count,
            "static_binding_count": len(static_bindings),
            "static_vs_ps_pair_count": len(pair_index),
            "static_pixel_stride_key_count": len(pixel_stride_index),
            "exact_vs_ps_candidate_pipeline_count": (
                exact_pair_pipeline_count
            ),
            "exact_vs_ps_candidate_draw_count": exact_pair_draw_count,
            "layout_pixel_candidate_pipeline_count": (
                layout_pixel_pipeline_count
            ),
            "layout_pixel_candidate_draw_count": (
                layout_pixel_draw_count
            ),
            "candidate_pipeline_count": candidate_pipeline_count,
            "candidate_draw_count": candidate_draw_count,
            "candidate_draw_coverage": (
                candidate_draw_count / runtime_draw_count
                if runtime_draw_count
                else 0.0
            ),
            "draw_range_gate_pipeline_count": (
                draw_range_gate_pipeline_count
            ),
            "draw_range_gate_reduced_pipeline_count": (
                draw_range_gate_reduced_pipeline_count
            ),
            "draw_range_gate_rejected_pipeline_count": (
                draw_range_gate_rejected_pipeline_count
            ),
            "single_static_binding_candidate_pipeline_count": (
                single_binding_pipeline_count
            ),
            "single_static_binding_candidate_draw_count": (
                single_binding_draw_count
            ),
            "single_content_candidate_pipeline_count": (
                single_content_group_pipeline_count
            ),
            "single_content_candidate_draw_count": (
                single_content_group_draw_count
            ),
            "distinct_static_candidate_binding_count": len(
                candidate_binding_indices
            ),
            "distinct_candidate_content_group_count": len(
                distinct_content_group_sha256s
            ),
            "candidate_content_group_count_distribution": {
                str(count): pipelines
                for count, pipelines in sorted(
                    candidate_content_group_count_distribution.items()
                )
            },
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
            "exact_vs_ps_candidate": (
                "static candidate contains the exact observed VS+PS "
                "byte hashes"
            ),
            "layout_pixel_candidate": (
                "static prefilter-only target shares the exact observed "
                "PS hash and its source-backed IMB vertex properties "
                "derive the same stream-0 byte stride; VS identity is "
                "not claimed"
            ),
            "draw_range_candidate_gate": (
                "when the runtime catalogue exposes a complete draw-range "
                "set, static candidates must match observed start_index + "
                "primitive_count; truncated legacy top ranges do not filter"
            ),
            "single_static_binding_candidate": (
                "one static binding survives the applicable candidate "
                "gate; this is not runtime same-instance proof"
            ),
            "candidate_compaction": (
                "candidate rows are grouped by static binding; repeated "
                "FXO offsets are represented by matched_variant_count "
                "instead of duplicating the binding payload"
            ),
            "content_candidate_group": (
                "archive-invariant diagnostic grouping by exact IMB payload "
                "SHA + primitive/draw range + BMT SHA + shader/layout "
                "contract; this does not identify a runtime archive instance"
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
