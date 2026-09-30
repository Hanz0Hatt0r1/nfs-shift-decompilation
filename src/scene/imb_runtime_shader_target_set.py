"""Build capture-oriented shader targets from IMB material ranking evidence.

This contract never chooses a retail shader permutation. It converts every
complete top-rank candidate set into byte-hash targets suitable for D3D9
capture prefiltering and later same-instance attribution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"
RANKING_FORMAT = "SHIFT.IMBMaterialShaderRanking/1"


def _valid_sha(value: Any) -> str | None:
    text = str(value or "").lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _candidate_target(
    candidate: Mapping[str, Any],
) -> dict[str, Any] | None:
    permutation_sha = _valid_sha(
        candidate.get("permutation_identity_sha256")
    )
    pair_sha = _valid_sha(candidate.get("pair_sha256"))
    vertex_sha = _valid_sha(candidate.get("vertex_sha256"))
    pixel_sha = _valid_sha(candidate.get("pixel_sha256"))
    pair_unique = (
        candidate.get("vertex_pair_selection_status") == "unique"
    )

    if pair_unique and permutation_sha:
        identity_kind = "permutation"
        identity_value = permutation_sha
        strength = "exact-pair"
    elif pair_unique and pair_sha:
        identity_kind = "pair"
        identity_value = pair_sha
        strength = "exact-pair"
    elif pixel_sha:
        identity_kind = "pixel"
        identity_value = pixel_sha
        strength = "prefilter-only"
    elif vertex_sha:
        identity_kind = "vertex"
        identity_value = vertex_sha
        strength = "prefilter-only"
    else:
        return None

    return {
        "identity_kind": identity_kind,
        "identity_value": identity_value,
        "strength": strength,
        "permutation_identity_sha256": permutation_sha,
        "pair_byte_sha256": pair_sha,
        "vertex_byte_sha256": vertex_sha,
        "pixel_byte_sha256": pixel_sha,
        "candidate_file": candidate.get("file"),
        "candidate_program_offset": candidate.get("program_offset"),
        "vertex_pair_selection_status": candidate.get(
            "vertex_pair_selection_status"
        ),
        "exact": candidate.get("exact") is True,
    }


def _binding_identity(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "archive": row.get("archive"),
        "imb_path": row.get("imb_path"),
        "imb_entry_index": row.get("imb_entry_index"),
        "imb_sha256": row.get("imb_sha256"),
        "primitive_index": row.get("primitive_index"),
        "draw_range": dict(row.get("draw_range") or {}),
        "property_descriptors": [
            dict(value)
            for value in (row.get("property_descriptors") or [])
            if isinstance(value, Mapping)
        ],
        "material_reference": row.get("material_reference"),
        "bmt": row.get("bmt"),
        "bmt_sha256": row.get("bmt_sha256"),
        "shader": row.get("shader"),
        "shader_family": row.get("shader_family"),
        "vertex_properties": list(row.get("vertex_properties") or []),
    }


def build_imb_runtime_shader_target_set(
    ranking: Mapping[str, Any],
) -> dict[str, Any]:
    if ranking.get("format") != RANKING_FORMAT:
        raise ValueError(
            "input must be SHIFT.IMBMaterialShaderRanking/1"
        )

    blockers: list[str] = []
    binding_targets: list[dict[str, Any]] = []
    global_targets: dict[tuple[str, str], dict[str, Any]] = {}

    rows = [
        row
        for row in (ranking.get("rows") or [])
        if isinstance(row, Mapping)
    ]

    for ordinal, row in enumerate(rows):
        identity = _binding_identity(row)
        declared_count = row.get("top_rank_candidate_count")
        candidates = [
            candidate
            for candidate in (row.get("top_rank_candidates") or [])
            if isinstance(candidate, Mapping)
        ]

        row_blockers: list[str] = []
        if declared_count is None:
            row_blockers.append("top-rank-candidate-count-missing")
        else:
            try:
                declared_count = int(declared_count)
            except (TypeError, ValueError):
                row_blockers.append("top-rank-candidate-count-invalid")
                declared_count = -1
            if declared_count < 0:
                row_blockers.append("top-rank-candidate-count-invalid")
            elif declared_count != len(candidates):
                row_blockers.append(
                    "top-rank-candidate-list-incomplete"
                )

        targets: list[dict[str, Any]] = []
        dropped = 0
        for candidate in candidates:
            target = _candidate_target(candidate)
            if target is None:
                dropped += 1
                continue
            targets.append(target)

        dedup: dict[tuple[str, str], dict[str, Any]] = {}
        for target in targets:
            key = (
                str(target["identity_kind"]),
                str(target["identity_value"]),
            )
            if key not in dedup:
                dedup[key] = {
                    "identity_kind": target["identity_kind"],
                    "identity_value": target["identity_value"],
                    "strength": target["strength"],
                    "candidate_locations": [],
                    "candidate_variants": [],
                }
            variant = {
                "permutation_identity_sha256": target.get(
                    "permutation_identity_sha256"
                ),
                "pair_byte_sha256": target.get("pair_byte_sha256"),
                "vertex_byte_sha256": target.get("vertex_byte_sha256"),
                "pixel_byte_sha256": target.get("pixel_byte_sha256"),
                "candidate_file": target.get("candidate_file"),
                "candidate_program_offset": target.get(
                    "candidate_program_offset"
                ),
                "vertex_pair_selection_status": target.get(
                    "vertex_pair_selection_status"
                ),
                "exact": target.get("exact") is True,
            }
            dedup[key]["candidate_variants"].append(variant)
            dedup[key]["candidate_locations"].append({
                "file": target.get("candidate_file"),
                "program_offset": target.get(
                    "candidate_program_offset"
                ),
            })

        targets = list(dedup.values())
        for target in targets:
            variants = target["candidate_variants"]
            for field in (
                "permutation_identity_sha256",
                "pair_byte_sha256",
                "vertex_byte_sha256",
                "pixel_byte_sha256",
            ):
                values = {
                    variant.get(field)
                    for variant in variants
                    if variant.get(field)
                }
                target[field] = next(iter(values)) if len(values) == 1 else None
            target["candidate_variant_count"] = len(variants)

        if not targets:
            row_blockers.append("no-hash-targets")
        if dropped:
            row_blockers.append(
                f"unhashed-top-candidates:{dropped}"
            )

        capture_ready = (
            bool(targets)
            and not any(
                reason in {
                    "top-rank-candidate-count-missing",
                    "top-rank-candidate-count-invalid",
                    "top-rank-candidate-list-incomplete",
                    "no-hash-targets",
                }
                or reason.startswith("unhashed-top-candidates:")
                for reason in row_blockers
            )
        )
        attribution_ready = (
            capture_ready
            and all(
                target.get("strength") == "exact-pair"
                and target.get("candidate_variants")
                and all(
                    variant.get("exact") is True
                    for variant in target["candidate_variants"]
                )
                for target in targets
            )
        )

        binding_targets.append({
            "binding_index": ordinal,
            **identity,
            "selection_status": row.get("selection_status"),
            "top_rank_candidate_count": (
                declared_count if declared_count is not None else None
            ),
            "hash_target_count": len(targets),
            "dropped_unhashed_top_candidates": dropped,
            "capture_ready": capture_ready,
            "attribution_ready": attribution_ready,
            "blocking_reasons": row_blockers,
            "targets": targets,
        })

        for reason in row_blockers:
            blockers.append(
                f"binding-{ordinal}:{reason}"
            )

        for target in targets:
            key = (
                str(target["identity_kind"]),
                str(target["identity_value"]),
            )
            aggregate = global_targets.setdefault(key, {
                "identity_kind": target["identity_kind"],
                "identity_value": target["identity_value"],
                "strength": target["strength"],
                "permutation_identity_sha256": target.get(
                    "permutation_identity_sha256"
                ),
                "pair_byte_sha256": target.get(
                    "pair_byte_sha256"
                ),
                "vertex_byte_sha256": target.get(
                    "vertex_byte_sha256"
                ),
                "pixel_byte_sha256": target.get(
                    "pixel_byte_sha256"
                ),
                "candidate_variant_count": 0,
                "binding_indices": [],
                "shader_families": [],
                "imb_paths": [],
            })
            aggregate["candidate_variant_count"] += int(
                target.get("candidate_variant_count") or 0
            )
            if ordinal not in aggregate["binding_indices"]:
                aggregate["binding_indices"].append(ordinal)
            family = row.get("shader_family")
            if (
                family
                and family not in aggregate["shader_families"]
            ):
                aggregate["shader_families"].append(family)
            imb_path = row.get("imb_path")
            if (
                imb_path
                and imb_path not in aggregate["imb_paths"]
            ):
                aggregate["imb_paths"].append(imb_path)

    capture_ready = (
        bool(binding_targets)
        and all(
            row.get("capture_ready")
            for row in binding_targets
        )
    )
    attribution_ready = (
        capture_ready
        and all(
            row.get("attribution_ready")
            for row in binding_targets
        )
    )

    unique_targets = sorted(
        global_targets.values(),
        key=lambda row: (
            str(row["identity_kind"]),
            str(row["identity_value"]),
        ),
    )
    for row in unique_targets:
        row["binding_indices"].sort()
        row["shader_families"].sort()
        row["imb_paths"].sort()

    return {
        "format": FORMAT,
        "version": 1,
        "status": (
            "capture-ready" if capture_ready else "blocked"
        ),
        "capture_ready": capture_ready,
        "attribution_ready": attribution_ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "source_ranking": {
            "format": ranking.get("format"),
            "primitive_binding_count": ranking.get(
                "primitive_binding_count"
            ),
            "runtime_target_count": ranking.get(
                "runtime_target_count"
            ),
            "unique_rank_context_count": ranking.get(
                "unique_rank_context_count"
            ),
        },
        "binding_target_count": len(binding_targets),
        "unique_hash_target_count": len(unique_targets),
        "strong_hash_target_count": sum(
            row.get("strength") == "exact-pair"
            for row in unique_targets
        ),
        "prefilter_only_target_count": sum(
            row.get("strength") == "prefilter-only"
            for row in unique_targets
        ),
        "binding_targets": binding_targets,
        "unique_targets": unique_targets,
        "boundary": {
            "render_admission": False,
            "selects_permutation": False,
            "requires_complete_top_rank_set": True,
            "preserves_candidate_variants": True,
            "resource_identity_fields": [
                "archive", "imb_path", "imb_sha256"
            ],
            "draw_identity_fields": [
                "primitive_index", "draw_range", "property_descriptors"
            ],
            "purpose": (
                "prefilter runtime D3D9 shader objects and constrain "
                "same-instance IMB primitive attribution"
            ),
        },
    }


def validate_file(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("ranking input must be a JSON object")
    return build_imb_runtime_shader_target_set(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build capture-oriented IMB shader targets from "
            "material-ranking evidence"
        )
    )
    parser.add_argument("ranking")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_file(args.ranking)
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
        "capture_ready": report["capture_ready"],
        "attribution_ready": report[
            "attribution_ready"
        ],
        "binding_target_count": report[
            "binding_target_count"
        ],
        "unique_hash_target_count": report[
            "unique_hash_target_count"
        ],
        "strong_hash_target_count": report[
            "strong_hash_target_count"
        ],
        "prefilter_only_target_count": report[
            "prefilter_only_target_count"
        ],
        "blocking_reasons": report[
            "blocking_reasons"
        ],
    }, ensure_ascii=False, indent=2))
    return 0 if report["capture_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
