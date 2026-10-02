"""Narrow static IMB candidates through capture-local runtime geometry identity.

Phase 615 consumes the Phase 613 pointer-observation catalogue and the Phase 611
material-descriptor candidate join. A Phase 611 single-content row may seed the
static geometry fingerprint observed behind one Phase 613 geometry pointer
identity. The same capture-local geometry allocation may then narrow an
ambiguous static candidate set even when texture objects differ between draws.

The seed is deliberately geometry-only: exact IMB payload SHA, primitive index,
source draw range and static vertex stride. Texture-pointer equality is not used
to infer BMT identity. Pointer equality remains session-local candidate evidence
and never proves portable resource identity or render admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.IMBRuntimeGeometryPointerCandidateJoin/1"
POINTER_FORMAT = "SHIFT.D3D9TargetPointerObservations/1"
MATERIAL_FORMAT = "SHIFT.IMBRuntimeMaterialDescriptorCandidateJoin/1"


def _valid_sha(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _canonical_hash(value: Mapping[str, Any]) -> str:
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


def _geometry_fingerprint_payload(group: Mapping[str, Any]) -> dict[str, Any] | None:
    imb_sha = _valid_sha(group.get("imb_sha256"))
    primitive_index = group.get("primitive_index")
    stride = group.get("static_vertex_stride")
    draw = group.get("draw_range")
    if (
        not imb_sha
        or not isinstance(primitive_index, int)
        or not isinstance(stride, int)
        or not isinstance(draw, Mapping)
    ):
        return None
    try:
        first_index = int(draw.get("first_index"))
        index_count = int(draw.get("index_count"))
        primitive_count = int(draw.get("primitive_count"))
    except (TypeError, ValueError):
        return None
    return {
        "imb_sha256": imb_sha,
        "primitive_index": primitive_index,
        "draw_range": {
            "first_index": first_index,
            "index_count": index_count,
            "primitive_count": primitive_count,
        },
        "static_vertex_stride": stride,
    }


def _compact_group(group: Mapping[str, Any]) -> dict[str, Any]:
    result = {
        "content_group_sha256": _valid_sha(group.get("content_group_sha256")),
        "imb_sha256": _valid_sha(group.get("imb_sha256")),
        "imb_paths": sorted({str(v) for v in (group.get("imb_paths") or []) if v}),
        "archives": sorted({str(v) for v in (group.get("archives") or []) if v}),
        "bmt_sha256": _valid_sha(group.get("bmt_sha256")),
        "shader_family": group.get("shader_family"),
        "primitive_index": group.get("primitive_index"),
        "draw_range": dict(group.get("draw_range") or {}),
        "static_vertex_stride": group.get("static_vertex_stride"),
        "matched_vertex_shader_sha256": _valid_sha(group.get("matched_vertex_shader_sha256")),
        "matched_pixel_shader_sha256": _valid_sha(group.get("matched_pixel_shader_sha256")),
        "pipeline_recovery_evidence_kind": group.get("pipeline_recovery_evidence_kind"),
        "pipeline_recovery_static_vertex_shader_mismatch": group.get(
            "pipeline_recovery_static_vertex_shader_mismatch"
        ),
    }
    geometry = _geometry_fingerprint_payload(result)
    result["geometry_fingerprint"] = geometry
    result["geometry_fingerprint_sha256"] = (
        _canonical_hash(geometry) if geometry is not None else None
    )
    return result


def _material_index(material_join: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in material_join.get("resource_shapes") or []:
        if not isinstance(row, Mapping):
            continue
        resource_sha = _valid_sha(row.get("resource_shape_sha256"))
        if not resource_sha:
            continue
        groups = [
            _compact_group(group)
            for group in (row.get("candidate_content_groups") or [])
            if isinstance(group, Mapping)
            and _valid_sha(group.get("content_group_sha256"))
        ]
        result[resource_sha] = {
            "resource_shape_sha256": resource_sha,
            "candidate_content_status": row.get("candidate_content_status"),
            "candidate_content_groups": groups,
            "draw_count": int(row.get("draw_count") or 0),
            "families": list(row.get("families") or []),
            "geometry_shape_sha256": row.get("geometry_shape_sha256"),
            "pipeline_signature_sha256": row.get("pipeline_signature_sha256"),
        }
    return result


def _pointer_index(pointer_report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for row in pointer_report.get("resource_shapes") or []:
        if not isinstance(row, Mapping):
            continue
        resource_sha = _valid_sha(row.get("resource_shape_sha256"))
        if resource_sha:
            result[resource_sha] = row
    return result


def _build_geometry_seed_index(
    material_by_resource: Mapping[str, Mapping[str, Any]],
    pointer_by_resource: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    raw: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "geometry_fingerprint_sha256s": set(),
            "content_group_sha256s": set(),
            "resource_shape_sha256s": set(),
            "draw_count": 0,
            "fingerprints": {},
        }
    )
    for resource_sha, material in material_by_resource.items():
        groups = list(material.get("candidate_content_groups") or [])
        if material.get("candidate_content_status") != "single-content-candidate" or len(groups) != 1:
            continue
        group = groups[0]
        fingerprint_sha = _valid_sha(group.get("geometry_fingerprint_sha256"))
        content_sha = _valid_sha(group.get("content_group_sha256"))
        fingerprint = group.get("geometry_fingerprint")
        if not fingerprint_sha or not content_sha or not isinstance(fingerprint, Mapping):
            continue
        pointer = pointer_by_resource.get(resource_sha)
        if not isinstance(pointer, Mapping):
            continue
        for observation in pointer.get("geometry_pointer_observations") or []:
            if not isinstance(observation, Mapping):
                continue
            identity_sha = _valid_sha(observation.get("identity_sha256"))
            identity = observation.get("identity")
            if not identity_sha or not isinstance(identity, Mapping):
                continue
            if not bool(identity.get("creation_identity_complete")):
                continue
            seed = raw[identity_sha]
            seed["geometry_fingerprint_sha256s"].add(fingerprint_sha)
            seed["content_group_sha256s"].add(content_sha)
            seed["resource_shape_sha256s"].add(resource_sha)
            seed["draw_count"] += int(observation.get("draw_count_in_resource_shape") or 0)
            seed["fingerprints"][fingerprint_sha] = dict(fingerprint)

    result: dict[str, dict[str, Any]] = {}
    for identity_sha, source in raw.items():
        fingerprints = sorted(source["geometry_fingerprint_sha256s"])
        result[identity_sha] = {
            "geometry_pointer_identity_sha256": identity_sha,
            "status": (
                "unique-geometry-seed"
                if len(fingerprints) == 1
                else "conflicting-geometry-seeds"
            ),
            "geometry_fingerprint_sha256s": fingerprints,
            "geometry_fingerprints": [
                source["fingerprints"][digest] for digest in fingerprints
            ],
            "content_group_sha256s": sorted(source["content_group_sha256s"]),
            "resource_shape_sha256s": sorted(source["resource_shape_sha256s"]),
            "seed_draw_count": int(source["draw_count"]),
        }
    return result


def build_runtime_geometry_pointer_candidate_join(
    pointer_report: Mapping[str, Any],
    material_join: Mapping[str, Any],
) -> dict[str, Any]:
    if pointer_report.get("format") != POINTER_FORMAT:
        raise ValueError("pointer report must be SHIFT.D3D9TargetPointerObservations/1")
    if material_join.get("format") != MATERIAL_FORMAT:
        raise ValueError(
            "material join must be SHIFT.IMBRuntimeMaterialDescriptorCandidateJoin/1"
        )
    alignment = pointer_report.get("catalog_alignment")
    if not isinstance(alignment, Mapping) or alignment.get("status") != "exact":
        raise ValueError("pointer report requires exact Phase 605 catalog alignment")

    material_by_resource = _material_index(material_join)
    pointer_by_resource = _pointer_index(pointer_report)
    material_shapes = set(material_by_resource)
    pointer_shapes = set(pointer_by_resource)
    if material_shapes != pointer_shapes:
        raise ValueError(
            "resource-shape set mismatch between pointer/material reports: "
            f"missing-pointer={len(material_shapes - pointer_shapes)}, "
            f"missing-material={len(pointer_shapes - material_shapes)}"
        )

    seeds = _build_geometry_seed_index(material_by_resource, pointer_by_resource)
    seed_status_counts = Counter(row["status"] for row in seeds.values())
    gate_counts: Counter[str] = Counter()
    source_status_counts: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    total_identity_draws = 0
    single_identity_count = 0
    single_identity_draws = 0
    newly_resolved_count = 0
    newly_resolved_draws = 0
    seeded_count = 0
    seeded_draws = 0
    conflict_count = 0
    conflict_draws = 0

    for resource_sha in sorted(material_shapes):
        material = material_by_resource[resource_sha]
        pointer = pointer_by_resource[resource_sha]
        base_groups = list(material.get("candidate_content_groups") or [])
        base_hashes = [
            str(group["content_group_sha256"])
            for group in base_groups
            if group.get("content_group_sha256")
        ]
        source_status = str(material.get("candidate_content_status") or "unknown")
        source_status_counts[source_status] += 1
        identity_rows: list[dict[str, Any]] = []
        resolved_contents: set[str] = set()
        observation_draw_sum = 0
        all_single = True

        for observation in pointer.get("geometry_pointer_observations") or []:
            if not isinstance(observation, Mapping):
                continue
            identity_sha = _valid_sha(observation.get("identity_sha256"))
            if not identity_sha:
                continue
            draw_count = int(observation.get("draw_count_in_resource_shape") or 0)
            observation_draw_sum += draw_count
            total_identity_draws += draw_count
            seed = seeds.get(identity_sha)
            selected = list(base_groups)
            gate_status = "no-seed"
            seed_fingerprint_sha = None

            if not base_groups:
                gate_status = "no-base-candidates"
            elif len(base_groups) == 1:
                gate_status = "already-single"
            elif isinstance(seed, Mapping):
                if seed.get("status") == "unique-geometry-seed":
                    seeded_count += 1
                    seeded_draws += draw_count
                    values = list(seed.get("geometry_fingerprint_sha256s") or [])
                    seed_fingerprint_sha = _valid_sha(values[0]) if len(values) == 1 else None
                    matching = [
                        group
                        for group in base_groups
                        if group.get("geometry_fingerprint_sha256") == seed_fingerprint_sha
                    ]
                    if matching and len(matching) < len(base_groups):
                        selected = matching
                        gate_status = "reduced-by-same-geometry-seed"
                    elif matching:
                        gate_status = "geometry-seed-matched-all"
                    else:
                        gate_status = "geometry-seed-outside-static-candidate-set"
                        conflict_count += 1
                        conflict_draws += draw_count
                else:
                    gate_status = "conflicting-geometry-seeds"
                    conflict_count += 1
                    conflict_draws += draw_count

            gate_counts[gate_status] += 1
            selected_hashes = sorted({
                str(group.get("content_group_sha256"))
                for group in selected
                if group.get("content_group_sha256")
            })
            if len(selected_hashes) == 1:
                candidate_status = "single-content-candidate"
                single_identity_count += 1
                single_identity_draws += draw_count
                resolved_contents.add(selected_hashes[0])
                if len(set(base_hashes)) > 1:
                    newly_resolved_count += 1
                    newly_resolved_draws += draw_count
            elif selected_hashes:
                candidate_status = "ambiguous-content-candidates"
                all_single = False
            else:
                candidate_status = "no-content-candidates"
                all_single = False

            identity_rows.append({
                "geometry_pointer_identity_sha256": identity_sha,
                "draw_count": draw_count,
                "first_frame": observation.get("first_frame"),
                "last_frame": observation.get("last_frame"),
                "geometry_pointer_identity": dict(observation.get("identity") or {}),
                "source_candidate_content_status": source_status,
                "source_candidate_content_group_count": len(set(base_hashes)),
                "geometry_seed_status": (
                    seed.get("status") if isinstance(seed, Mapping) else "unseeded"
                ),
                "geometry_seed_fingerprint_sha256": seed_fingerprint_sha,
                "geometry_seed_resource_shape_sha256s": (
                    list(seed.get("resource_shape_sha256s") or [])
                    if isinstance(seed, Mapping)
                    else []
                ),
                "geometry_candidate_gate_status": gate_status,
                "candidate_content_status": candidate_status,
                "candidate_content_group_count": len(selected_hashes),
                "candidate_content_group_sha256s": selected_hashes,
                "candidate_content_groups": selected,
            })

        if not identity_rows:
            resource_status = "no-geometry-pointer-observations"
        elif all_single:
            resource_status = (
                "single-content-across-geometry-identities"
                if len(resolved_contents) == 1
                else "multiple-single-contents-by-geometry-identity"
            )
        else:
            resource_status = "geometry-identities-still-ambiguous"

        rows.append({
            "resource_shape_sha256": resource_sha,
            "geometry_shape_sha256": material.get("geometry_shape_sha256"),
            "pipeline_signature_sha256": material.get("pipeline_signature_sha256"),
            "families": list(material.get("families") or []),
            "resource_shape_draw_count": int(material.get("draw_count") or 0),
            "geometry_pointer_observation_draw_count": observation_draw_sum,
            "source_candidate_content_status": source_status,
            "source_candidate_content_group_count": len(set(base_hashes)),
            "geometry_pointer_identity_count": len(identity_rows),
            "geometry_resource_status": resource_status,
            "resolved_content_group_sha256s": sorted(resolved_contents),
            "geometry_pointer_identities": identity_rows,
        })

    rows.sort(
        key=lambda row: (
            -int(row.get("resource_shape_draw_count") or 0),
            str(row.get("resource_shape_sha256") or ""),
        )
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "observed" if rows else "not-observed",
        "summary": {
            "runtime_resource_shape_count": len(rows),
            "runtime_resource_shape_draw_count": sum(
                int(row.get("resource_shape_draw_count") or 0) for row in rows
            ),
            "geometry_pointer_identity_observation_count": sum(
                int(row.get("geometry_pointer_identity_count") or 0) for row in rows
            ),
            "geometry_pointer_identity_draw_count": total_identity_draws,
            "geometry_seed_identity_count": len(seeds),
            "geometry_seed_status_counts": dict(sorted(seed_status_counts.items())),
            "seeded_geometry_identity_observation_count": seeded_count,
            "seeded_geometry_identity_draw_count": seeded_draws,
            "single_content_geometry_identity_count": single_identity_count,
            "single_content_geometry_identity_draw_count": single_identity_draws,
            "newly_resolved_geometry_identity_count": newly_resolved_count,
            "newly_resolved_geometry_identity_draw_count": newly_resolved_draws,
            "geometry_seed_conflict_identity_count": conflict_count,
            "geometry_seed_conflict_draw_count": conflict_draws,
            "geometry_candidate_gate_status_counts": dict(sorted(gate_counts.items())),
            "source_candidate_status_counts": dict(sorted(source_status_counts.items())),
        },
        "geometry_seeds": sorted(
            seeds.values(),
            key=lambda row: str(row.get("geometry_pointer_identity_sha256") or ""),
        ),
        "resource_shapes": rows,
        "boundary": {
            "candidate_only": True,
            "capture_local_only": True,
            "geometry_pointer_equality": (
                "same capture device + stream-0 VB generation + IB generation + exact draw range; session-local only"
            ),
            "geometry_seed_projection": (
                "single-content rows seed exact IMB SHA + primitive index + source draw range + static vertex stride"
            ),
            "material_pointer_policy": (
                "not used for BMT narrowing because equal texture-object sets do not prove equal material constants or BMT identity"
            ),
            "render_admission": False,
            "required_for_promotion": (
                "exact runtime resource path/SHA or payload equality plus existing Phase 572 strong same-instance gates"
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pointer_report")
    parser.add_argument("material_join")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    pointer_report = json.loads(
        resolve_input_path(args.pointer_report).read_text(encoding="utf-8")
    )
    material_join = json.loads(
        resolve_input_path(args.material_join).read_text(encoding="utf-8")
    )
    if not isinstance(pointer_report, dict) or not isinstance(material_join, dict):
        raise ValueError("inputs must be JSON objects")
    report = build_runtime_geometry_pointer_candidate_join(pointer_report, material_join)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
