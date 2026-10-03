"""Classify unresolved Phase 617 static-candidate ambiguity without ranking.

The input is ``SHIFT.IMBDrawLocalStaticCandidateJoin/1``.  Phase 618 does not
select a winner.  It groups surviving candidates by the evidence dimension that
still differs so later offline work can target the right proof source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.IMBDrawLocalAmbiguityAudit/1"
INPUT_FORMAT = "SHIFT.IMBDrawLocalStaticCandidateJoin/1"
_LOD_RE = re.compile(r"_lod[a-z0-9]+(?=\.imb$)", re.IGNORECASE)


def _valid_sha(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def resolve_input_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate
    repo_root = Path(__file__).resolve().parents[2]
    repo_candidate = repo_root / candidate
    if repo_candidate.exists():
        return repo_candidate
    raise FileNotFoundError(
        f"input file not found: {candidate} (also tried {repo_candidate})"
    )


def _candidate_paths(candidate: Mapping[str, Any]) -> list[str]:
    return sorted({
        str(value).replace("\\", "/")
        for value in (candidate.get("imb_paths") or [])
        if value
    })


def _candidate_contract(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Return proof-relevant metadata while excluding portable IMB identity.

    Content/IMB hashes and paths are deliberately excluded.  Equal contracts do
    not mean equal meshes; they mean Phase 617 has no remaining candidate field
    other than geometry identity with which to distinguish them.
    """
    return {
        "bmt_sha256": _valid_sha(candidate.get("bmt_sha256")),
        "shader_family": candidate.get("shader_family"),
        "primitive_index": candidate.get("primitive_index"),
        "draw_range": dict(candidate.get("draw_range") or {}),
        "static_vertex_stride": candidate.get("static_vertex_stride"),
        "matched_vertex_shader_sha256": _valid_sha(
            candidate.get("matched_vertex_shader_sha256")
        ),
        "matched_pixel_shader_sha256": _valid_sha(
            candidate.get("matched_pixel_shader_sha256")
        ),
        "pipeline_recovery_evidence_kind": candidate.get(
            "pipeline_recovery_evidence_kind"
        ),
        "pipeline_recovery_static_vertex_shader_mismatch": (
            candidate.get("pipeline_recovery_static_vertex_shader_mismatch")
            is True
        ),
    }


def _candidate_summary(candidate: Mapping[str, Any]) -> dict[str, Any]:
    contract = _candidate_contract(candidate)
    return {
        "content_group_sha256": _valid_sha(candidate.get("content_group_sha256")),
        "imb_sha256": _valid_sha(candidate.get("imb_sha256")),
        "imb_paths": _candidate_paths(candidate),
        "archives": sorted({
            str(value) for value in (candidate.get("archives") or []) if value
        }),
        **contract,
        "shader_gate_status": candidate.get("shader_gate_status"),
        "candidate_contract_sha256": _canonical_hash(contract),
    }


def _single_path(candidate: Mapping[str, Any]) -> str | None:
    paths = _candidate_paths(candidate)
    return paths[0] if len(paths) == 1 else None


def _lod_sibling_diagnostic(candidates: list[Mapping[str, Any]]) -> dict[str, Any]:
    paths = [_single_path(candidate) for candidate in candidates]
    if len(candidates) < 2 or any(path is None for path in paths):
        return {"status": "not-proven", "normalized_path": None}
    path_values = [str(path) for path in paths]
    normalized = [_LOD_RE.sub("_lod?", path.lower()) for path in path_values]
    changed = [norm != path.lower() for norm, path in zip(normalized, path_values)]
    if len(set(path_values)) > 1 and all(changed) and len(set(normalized)) == 1:
        return {
            "status": "path-name-lod-siblings",
            "normalized_path": normalized[0],
        }
    return {"status": "not-proven", "normalized_path": None}


def _set_count(candidates: list[Mapping[str, Any]], key: str) -> int:
    return len({_canonical_hash(candidate.get(key)) for candidate in candidates})


def _candidate_pair(candidate: Mapping[str, Any]) -> tuple[str | None, str | None]:
    return (
        _valid_sha(candidate.get("matched_vertex_shader_sha256")),
        _valid_sha(candidate.get("matched_pixel_shader_sha256")),
    )


def _classify(candidates: list[Mapping[str, Any]]) -> dict[str, Any]:
    contracts = [_candidate_contract(candidate) for candidate in candidates]
    contract_hashes = {_canonical_hash(contract) for contract in contracts}
    bmt_values = {_valid_sha(candidate.get("bmt_sha256")) for candidate in candidates}
    shader_pairs = {_candidate_pair(candidate) for candidate in candidates}
    families = {str(candidate.get("shader_family") or "") for candidate in candidates}
    draw_ranges = {_canonical_hash(candidate.get("draw_range") or {}) for candidate in candidates}
    strides = {candidate.get("static_vertex_stride") for candidate in candidates}
    primitive_indices = {candidate.get("primitive_index") for candidate in candidates}
    cross_vs = [
        candidate.get("pipeline_recovery_static_vertex_shader_mismatch") is True
        for candidate in candidates
    ]
    lod = _lod_sibling_diagnostic(candidates)

    metadata_equivalent = len(contract_hashes) == 1
    if metadata_equivalent and lod["status"] == "path-name-lod-siblings":
        ambiguity_class = "metadata-equivalent-lod-siblings"
        next_gate = "static-scene-reference-or-portable-geometry-identity"
    elif metadata_equivalent:
        ambiguity_class = "metadata-equivalent-geometry-alternatives"
        next_gate = "static-scene-reference-or-portable-geometry-identity"
    elif len(bmt_values) > 1:
        ambiguity_class = "material-distinct-candidates"
        next_gate = "offline-exact-material-content-correlation"
    elif len(shader_pairs) > 1:
        ambiguity_class = "shader-provenance-distinct-candidates"
        next_gate = "offline-exact-fxo-pair-provenance"
    else:
        ambiguity_class = "mixed-static-metadata-candidates"
        next_gate = "offline-static-candidate-evidence-split"

    return {
        "ambiguity_class": ambiguity_class,
        "next_gate": next_gate,
        "candidate_contract_count": len(contract_hashes),
        "distinct_bmt_sha256_count": len(bmt_values),
        "distinct_static_shader_pair_count": len(shader_pairs),
        "distinct_shader_family_count": len(families),
        "distinct_draw_range_count": len(draw_ranges),
        "distinct_static_vertex_stride_count": len(strides),
        "distinct_primitive_index_count": len(primitive_indices),
        "metadata_equivalent_except_imb_identity": metadata_equivalent,
        "all_cross_vs_donor_evidence": bool(cross_vs) and all(cross_vs),
        "any_cross_vs_donor_evidence": any(cross_vs),
        "lod_path_diagnostic": lod,
    }


def _minimal_evidence_for_class(ambiguity_class: str) -> dict[str, Any]:
    if ambiguity_class in {
        "metadata-equivalent-lod-siblings",
        "metadata-equivalent-geometry-alternatives",
    }:
        return {
            "offline_first": [
                "exact static scene/instance resource reference to one surviving IMB",
                "source-backed LOD selection metadata tied to the same scene instance",
            ],
            "capture_only_if_offline_fails": [
                "stream-0 VB payload once for the relevant buffer generation",
                "current IB payload once for the relevant buffer generation",
                "or portable runtime resource path plus SHA-256",
            ],
        }
    if ambiguity_class == "material-distinct-candidates":
        return {
            "offline_first": [
                "exact BMT shader-parameter and DDS-content correlation",
                "draw-local sampler/constant evidence joined by exact register contract",
            ],
            "capture_only_if_offline_fails": [
                "portable texture content identity for only the differing material samplers",
            ],
        }
    if ambiguity_class == "shader-provenance-distinct-candidates":
        return {
            "offline_first": [
                "exact FXO embedded VS+PS byte-pair provenance for every surviving candidate",
            ],
            "capture_only_if_offline_fails": [],
        }
    return {
        "offline_first": [
            "split candidates by every differing static field and apply only exact source-backed joins",
        ],
        "capture_only_if_offline_fails": [
            "capture only the specific identity dimension still absent after offline joins",
        ],
    }


def build_draw_local_ambiguity_audit(report: Mapping[str, Any]) -> dict[str, Any]:
    if report.get("format") != INPUT_FORMAT:
        raise ValueError(
            "input report must be SHIFT.IMBDrawLocalStaticCandidateJoin/1"
        )

    class_counts: Counter[str] = Counter()
    class_draws: Counter[str] = Counter()
    next_gate_counts: Counter[str] = Counter()
    candidate_count_distribution: Counter[int] = Counter()
    contract_count_distribution: Counter[int] = Counter()
    ambiguous_rows: list[dict[str, Any]] = []
    single_draw_count = 0

    for draw in report.get("draws") or []:
        if not isinstance(draw, Mapping):
            continue
        status = str(draw.get("candidate_resolution_status") or "")
        if status == "single-static-candidate":
            single_draw_count += 1
            continue
        if status != "ambiguous-static-candidates":
            continue

        candidates = [
            dict(candidate)
            for candidate in (draw.get("surviving_candidate_variants") or [])
            if isinstance(candidate, Mapping)
        ]
        summarized = [_candidate_summary(candidate) for candidate in candidates]
        classification = _classify(candidates)
        content_shas = sorted({
            str(candidate.get("content_group_sha256"))
            for candidate in candidates
            if candidate.get("content_group_sha256")
        })
        candidate_set_sha = _canonical_hash({"content_group_sha256s": content_shas})
        class_name = str(classification["ambiguity_class"])
        next_gate = str(classification["next_gate"])
        class_counts[class_name] += 1
        class_draws[class_name] += 1
        next_gate_counts[next_gate] += 1
        candidate_count_distribution[len(content_shas)] += 1
        contract_count_distribution[int(classification["candidate_contract_count"])] += 1

        ambiguous_rows.append({
            "event_index": draw.get("event_index"),
            "frame": draw.get("frame"),
            "draw_evidence_sha256": _valid_sha(draw.get("draw_evidence_sha256")),
            "resource_shape_sha256": _valid_sha(draw.get("resource_shape_sha256")),
            "geometry_pointer_identity_sha256": _valid_sha(
                draw.get("geometry_pointer_identity_sha256")
            ),
            "shader_pair": dict(draw.get("shader_pair") or {}),
            "candidate_set_sha256": candidate_set_sha,
            "surviving_content_group_count": len(content_shas),
            "surviving_content_group_sha256s": content_shas,
            **classification,
            "minimal_evidence": _minimal_evidence_for_class(class_name),
            "candidates": summarized,
        })

    ambiguous_rows.sort(
        key=lambda row: (
            int(row.get("event_index"))
            if isinstance(row.get("event_index"), int)
            else 2**63 - 1,
            str(row.get("draw_evidence_sha256") or ""),
        )
    )

    set_groups: dict[str, dict[str, Any]] = {}
    geometry_groups: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "draw_count": 0,
            "classes": Counter(),
            "candidate_sets": set(),
            "next_gates": Counter(),
        }
    )
    for row in ambiguous_rows:
        candidate_set_sha = str(row["candidate_set_sha256"])
        group = set_groups.get(candidate_set_sha)
        if group is None:
            group = {
                "candidate_set_sha256": candidate_set_sha,
                "surviving_content_group_sha256s": list(
                    row["surviving_content_group_sha256s"]
                ),
                "ambiguity_class": row["ambiguity_class"],
                "next_gate": row["next_gate"],
                "draw_count": 0,
                "geometry_pointer_identity_sha256s": set(),
                "resource_shape_sha256s": set(),
                "sample_event_indices": [],
            }
            set_groups[candidate_set_sha] = group
        group["draw_count"] += 1
        if row.get("geometry_pointer_identity_sha256"):
            group["geometry_pointer_identity_sha256s"].add(
                row["geometry_pointer_identity_sha256"]
            )
        if row.get("resource_shape_sha256"):
            group["resource_shape_sha256s"].add(row["resource_shape_sha256"])
        if len(group["sample_event_indices"]) < 8:
            group["sample_event_indices"].append(row.get("event_index"))

        geometry_sha = row.get("geometry_pointer_identity_sha256")
        if geometry_sha:
            geometry = geometry_groups[str(geometry_sha)]
            geometry["draw_count"] += 1
            geometry["classes"][str(row["ambiguity_class"])] += 1
            geometry["candidate_sets"].add(candidate_set_sha)
            geometry["next_gates"][str(row["next_gate"])] += 1

    candidate_sets = []
    for group in set_groups.values():
        candidate_sets.append({
            **{
                key: value
                for key, value in group.items()
                if key not in {
                    "geometry_pointer_identity_sha256s",
                    "resource_shape_sha256s",
                }
            },
            "geometry_pointer_identity_sha256s": sorted(
                group["geometry_pointer_identity_sha256s"]
            ),
            "resource_shape_sha256s": sorted(group["resource_shape_sha256s"]),
        })
    candidate_sets.sort(
        key=lambda row: (-int(row["draw_count"]), str(row["candidate_set_sha256"]))
    )

    geometry_rows = []
    for geometry_sha, group in geometry_groups.items():
        geometry_rows.append({
            "geometry_pointer_identity_sha256": geometry_sha,
            "ambiguous_draw_count": int(group["draw_count"]),
            "ambiguity_class_counts": dict(sorted(group["classes"].items())),
            "candidate_set_count": len(group["candidate_sets"]),
            "candidate_set_sha256s": sorted(group["candidate_sets"]),
            "next_gate_counts": dict(sorted(group["next_gates"].items())),
        })
    geometry_rows.sort(
        key=lambda row: (
            -int(row["ambiguous_draw_count"]),
            str(row["geometry_pointer_identity_sha256"]),
        )
    )

    metadata_equivalent_draw_count = sum(
        1
        for row in ambiguous_rows
        if row["metadata_equivalent_except_imb_identity"]
    )
    lod_diagnostic_draw_count = sum(
        1
        for row in ambiguous_rows
        if row["lod_path_diagnostic"]["status"] == "path-name-lod-siblings"
    )
    all_cross_vs_draw_count = sum(
        1 for row in ambiguous_rows if row["all_cross_vs_donor_evidence"]
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "observed" if ambiguous_rows else "not-observed",
        "summary": {
            "source_draw_count": len([
                row for row in (report.get("draws") or []) if isinstance(row, Mapping)
            ]),
            "single_static_candidate_draw_count": single_draw_count,
            "ambiguous_static_candidate_draw_count": len(ambiguous_rows),
            "unique_ambiguous_candidate_set_count": len(candidate_sets),
            "ambiguous_geometry_pointer_identity_count": len(geometry_rows),
            "metadata_equivalent_except_imb_identity_draw_count": (
                metadata_equivalent_draw_count
            ),
            "lod_path_diagnostic_draw_count": lod_diagnostic_draw_count,
            "all_cross_vs_donor_ambiguous_draw_count": all_cross_vs_draw_count,
            "ambiguity_class_counts": dict(sorted(class_counts.items())),
            "next_gate_counts": dict(sorted(next_gate_counts.items())),
            "surviving_content_group_count_distribution": {
                str(key): value
                for key, value in sorted(candidate_count_distribution.items())
            },
            "candidate_contract_count_distribution": {
                str(key): value
                for key, value in sorted(contract_count_distribution.items())
            },
        },
        "ambiguous_draws": ambiguous_rows,
        "candidate_sets": candidate_sets,
        "geometry_groups": geometry_rows,
        "recommended_order": [
            "Resolve material-distinct candidates with exact offline BMT/DDS/constant evidence.",
            "Resolve shader-provenance-distinct candidates only with exact embedded FXO VS+PS pair provenance.",
            "Resolve metadata-equivalent geometry alternatives from source-backed scene/instance/LOD references if available.",
            "Only after those offline joins fail, request targeted stream-0 VB + IB payload identity for the remaining geometry generations.",
        ],
        "boundary": {
            "audit_only": True,
            "candidate_ranking": False,
            "lod_path_is_identity_proof": False,
            "single_candidate_is_retail_identity": False,
            "portable_resource_identity_claimed": False,
            "new_capture_policy": (
                "defer capture until exact offline material/shader/scene-reference joins are exhausted per ambiguity class"
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase617_report")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = json.loads(
        resolve_input_path(args.phase617_report).read_text(encoding="utf-8")
    )
    if not isinstance(report, dict):
        raise ValueError("input must be a JSON object")
    result = build_draw_local_ambiguity_audit(report)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
