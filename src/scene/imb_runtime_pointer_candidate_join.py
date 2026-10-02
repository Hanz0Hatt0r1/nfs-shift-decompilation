"""Propagate static IMB content candidates through capture-local D3D9 object identity.

Phase 614 consumes the Phase 613 pointer-observation catalogue and the Phase
611 material-descriptor candidate join.  Single-content resource shapes become
candidate-only seeds for identical runtime VB/IB/texture object generations.
The join operates per combined pointer identity rather than per descriptor
shape so one descriptor-equivalent shape may legitimately contain several
static contents.

Pointer equality is session-local evidence only.  It never proves archive path,
payload SHA-256, portable identity, or render admission.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.IMBRuntimePointerCandidateJoin/1"
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


def _compact_group(group: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "content_group_sha256": _valid_sha(
            group.get("content_group_sha256")
        ),
        "imb_sha256": _valid_sha(group.get("imb_sha256")),
        "imb_paths": sorted({
            str(value)
            for value in (group.get("imb_paths") or [])
            if value
        }),
        "archives": sorted({
            str(value)
            for value in (group.get("archives") or [])
            if value
        }),
        "bmt_sha256": _valid_sha(group.get("bmt_sha256")),
        "shader_family": group.get("shader_family"),
        "primitive_index": group.get("primitive_index"),
        "draw_range": dict(group.get("draw_range") or {}),
        "static_vertex_stride": group.get("static_vertex_stride"),
        "matched_vertex_shader_sha256": _valid_sha(
            group.get("matched_vertex_shader_sha256")
        ),
        "matched_pixel_shader_sha256": _valid_sha(
            group.get("matched_pixel_shader_sha256")
        ),
        "pipeline_recovery_evidence_kind": group.get(
            "pipeline_recovery_evidence_kind"
        ),
        "pipeline_recovery_static_vertex_shader_mismatch": group.get(
            "pipeline_recovery_static_vertex_shader_mismatch"
        ),
    }


def _material_index(
    material_join: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
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
            "candidate_content_status": row.get(
                "candidate_content_status"
            ),
            "candidate_content_group_count": len(groups),
            "candidate_content_groups": groups,
            "candidate_content_group_sha256s": sorted({
                str(group["content_group_sha256"])
                for group in groups
                if group.get("content_group_sha256")
            }),
            "families": list(row.get("families") or []),
            "draw_count": int(row.get("draw_count") or 0),
            "geometry_shape_sha256": row.get("geometry_shape_sha256"),
            "pipeline_signature_sha256": row.get(
                "pipeline_signature_sha256"
            ),
            "material_descriptor_gate_status": row.get(
                "material_descriptor_gate_status"
            ),
        }
    return result


def _pointer_index(
    pointer_report: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for row in pointer_report.get("resource_shapes") or []:
        if not isinstance(row, Mapping):
            continue
        resource_sha = _valid_sha(row.get("resource_shape_sha256"))
        if resource_sha:
            result[resource_sha] = row
    return result


def _build_seed_index(
    material_by_resource: Mapping[str, Mapping[str, Any]],
    pointer_by_resource: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    raw: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "content_group_sha256s": set(),
            "resource_shape_sha256s": set(),
            "draw_count": 0,
        }
    )
    for resource_sha, material in material_by_resource.items():
        candidate_hashes = list(
            material.get("candidate_content_group_sha256s") or []
        )
        if (
            material.get("candidate_content_status")
            != "single-content-candidate"
            or len(candidate_hashes) != 1
        ):
            continue
        pointer = pointer_by_resource.get(resource_sha)
        if not isinstance(pointer, Mapping):
            continue
        content_sha = _valid_sha(candidate_hashes[0])
        if not content_sha:
            continue
        for observation in pointer.get(
            "combined_pointer_observations"
        ) or []:
            if not isinstance(observation, Mapping):
                continue
            identity_sha = _valid_sha(
                observation.get("identity_sha256")
            )
            if not identity_sha:
                continue
            seed = raw[identity_sha]
            seed["content_group_sha256s"].add(content_sha)
            seed["resource_shape_sha256s"].add(resource_sha)
            seed["draw_count"] += int(
                observation.get("draw_count_in_resource_shape") or 0
            )

    result: dict[str, dict[str, Any]] = {}
    for identity_sha, source in raw.items():
        contents = sorted(source["content_group_sha256s"])
        result[identity_sha] = {
            "identity_sha256": identity_sha,
            "status": (
                "unique-content-seed"
                if len(contents) == 1
                else "conflicting-content-seeds"
            ),
            "content_group_sha256s": contents,
            "resource_shape_sha256s": sorted(
                source["resource_shape_sha256s"]
            ),
            "seed_draw_count": int(source["draw_count"]),
        }
    return result


def build_runtime_pointer_candidate_join(
    pointer_report: Mapping[str, Any],
    material_join: Mapping[str, Any],
) -> dict[str, Any]:
    if pointer_report.get("format") != POINTER_FORMAT:
        raise ValueError(
            "pointer report must be SHIFT.D3D9TargetPointerObservations/1"
        )
    if material_join.get("format") != MATERIAL_FORMAT:
        raise ValueError(
            "material join must be "
            "SHIFT.IMBRuntimeMaterialDescriptorCandidateJoin/1"
        )

    alignment = pointer_report.get("catalog_alignment")
    if (
        not isinstance(alignment, Mapping)
        or alignment.get("status") != "exact"
    ):
        raise ValueError(
            "pointer report requires exact Phase 605 catalog alignment"
        )

    material_by_resource = _material_index(material_join)
    pointer_by_resource = _pointer_index(pointer_report)
    material_shapes = set(material_by_resource)
    pointer_shapes = set(pointer_by_resource)
    if material_shapes != pointer_shapes:
        missing_pointer = sorted(material_shapes - pointer_shapes)
        missing_material = sorted(pointer_shapes - material_shapes)
        raise ValueError(
            "resource-shape set mismatch between pointer/material reports: "
            f"missing-pointer={len(missing_pointer)}, "
            f"missing-material={len(missing_material)}"
        )

    seeds = _build_seed_index(
        material_by_resource,
        pointer_by_resource,
    )
    seed_status_counts = Counter(
        row["status"] for row in seeds.values()
    )

    rows: list[dict[str, Any]] = []
    gate_status_counts: Counter[str] = Counter()
    source_status_counts: Counter[str] = Counter()
    total_identity_draws = 0
    single_identity_count = 0
    single_identity_draws = 0
    newly_resolved_identity_count = 0
    newly_resolved_identity_draws = 0
    seeded_identity_count = 0
    seeded_identity_draws = 0
    conflict_identity_count = 0
    conflict_identity_draws = 0

    for resource_sha in sorted(material_shapes):
        material = material_by_resource[resource_sha]
        pointer = pointer_by_resource[resource_sha]
        base_groups = list(material["candidate_content_groups"])
        base_by_sha = {
            str(group["content_group_sha256"]): group
            for group in base_groups
            if group.get("content_group_sha256")
        }
        base_hashes = sorted(base_by_sha)
        source_status = str(
            material.get("candidate_content_status") or "unknown"
        )
        source_status_counts[source_status] += 1

        pointer_rows = []
        resource_resolved_contents: set[str] = set()
        all_identity_rows_single = True
        observation_draw_sum = 0

        for observation in pointer.get(
            "combined_pointer_observations"
        ) or []:
            if not isinstance(observation, Mapping):
                continue
            identity_sha = _valid_sha(
                observation.get("identity_sha256")
            )
            if not identity_sha:
                continue
            draw_count = int(
                observation.get("draw_count_in_resource_shape") or 0
            )
            observation_draw_sum += draw_count
            total_identity_draws += draw_count
            seed = seeds.get(identity_sha)
            candidate_hashes = list(base_hashes)
            gate_status = "no-seed"
            seed_content_sha = None

            if not base_hashes:
                gate_status = "no-base-candidates"
            elif len(base_hashes) == 1:
                gate_status = "already-single"
            elif isinstance(seed, Mapping):
                seed_status = seed.get("status")
                if seed_status == "unique-content-seed":
                    seeded_identity_count += 1
                    seeded_identity_draws += draw_count
                    seed_values = list(
                        seed.get("content_group_sha256s") or []
                    )
                    seed_content_sha = (
                        _valid_sha(seed_values[0])
                        if len(seed_values) == 1
                        else None
                    )
                    if seed_content_sha in base_by_sha:
                        candidate_hashes = [seed_content_sha]
                        gate_status = "reduced-by-same-object-seed"
                    else:
                        gate_status = "seed-outside-static-candidate-set"
                        conflict_identity_count += 1
                        conflict_identity_draws += draw_count
                else:
                    gate_status = "conflicting-pointer-seeds"
                    conflict_identity_count += 1
                    conflict_identity_draws += draw_count

            gate_status_counts[gate_status] += 1
            selected_groups = [
                base_by_sha[digest]
                for digest in candidate_hashes
                if digest in base_by_sha
            ]
            if len(candidate_hashes) == 1:
                identity_status = "single-content-candidate"
                single_identity_count += 1
                single_identity_draws += draw_count
                resource_resolved_contents.add(candidate_hashes[0])
                if len(base_hashes) > 1:
                    newly_resolved_identity_count += 1
                    newly_resolved_identity_draws += draw_count
            elif candidate_hashes:
                identity_status = "ambiguous-content-candidates"
                all_identity_rows_single = False
            else:
                identity_status = "no-content-candidates"
                all_identity_rows_single = False

            pointer_rows.append({
                "combined_pointer_identity_sha256": identity_sha,
                "draw_count": draw_count,
                "first_frame": observation.get("first_frame"),
                "last_frame": observation.get("last_frame"),
                "pointer_identity": dict(
                    observation.get("identity") or {}
                ),
                "source_candidate_content_status": source_status,
                "source_candidate_content_group_count": len(base_hashes),
                "pointer_seed_status": (
                    seed.get("status")
                    if isinstance(seed, Mapping)
                    else "unseeded"
                ),
                "pointer_seed_content_group_sha256": seed_content_sha,
                "pointer_seed_resource_shape_sha256s": (
                    list(seed.get("resource_shape_sha256s") or [])
                    if isinstance(seed, Mapping)
                    else []
                ),
                "pointer_candidate_gate_status": gate_status,
                "candidate_content_status": identity_status,
                "candidate_content_group_count": len(candidate_hashes),
                "candidate_content_group_sha256s": candidate_hashes,
                "candidate_content_groups": selected_groups,
            })

        if not pointer_rows:
            resource_status = "no-pointer-observations"
        elif all_identity_rows_single:
            if len(resource_resolved_contents) == 1:
                resource_status = "single-content-across-pointer-identities"
            else:
                resource_status = "multiple-single-contents-by-pointer-identity"
        else:
            resource_status = "pointer-identities-still-ambiguous"

        rows.append({
            "resource_shape_sha256": resource_sha,
            "geometry_shape_sha256": material.get(
                "geometry_shape_sha256"
            ),
            "pipeline_signature_sha256": material.get(
                "pipeline_signature_sha256"
            ),
            "families": list(material.get("families") or []),
            "resource_shape_draw_count": int(
                material.get("draw_count") or 0
            ),
            "pointer_observation_draw_count": observation_draw_sum,
            "source_candidate_content_status": source_status,
            "source_candidate_content_group_count": len(base_hashes),
            "source_candidate_content_group_sha256s": base_hashes,
            "pointer_identity_count": len(pointer_rows),
            "pointer_resource_status": resource_status,
            "resolved_content_group_sha256s": sorted(
                resource_resolved_contents
            ),
            "pointer_identities": pointer_rows,
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
                int(row.get("resource_shape_draw_count") or 0)
                for row in rows
            ),
            "combined_pointer_identity_observation_count": sum(
                int(row.get("pointer_identity_count") or 0)
                for row in rows
            ),
            "combined_pointer_identity_draw_count": total_identity_draws,
            "pointer_seed_identity_count": len(seeds),
            "pointer_seed_status_counts": dict(
                sorted(seed_status_counts.items())
            ),
            "seeded_pointer_identity_observation_count": (
                seeded_identity_count
            ),
            "seeded_pointer_identity_draw_count": seeded_identity_draws,
            "single_content_pointer_identity_count": single_identity_count,
            "single_content_pointer_identity_draw_count": (
                single_identity_draws
            ),
            "newly_resolved_pointer_identity_count": (
                newly_resolved_identity_count
            ),
            "newly_resolved_pointer_identity_draw_count": (
                newly_resolved_identity_draws
            ),
            "pointer_seed_conflict_identity_count": (
                conflict_identity_count
            ),
            "pointer_seed_conflict_draw_count": conflict_identity_draws,
            "pointer_candidate_gate_status_counts": dict(
                sorted(gate_status_counts.items())
            ),
            "source_candidate_status_counts": dict(
                sorted(source_status_counts.items())
            ),
        },
        "pointer_seeds": sorted(
            seeds.values(),
            key=lambda row: str(row["identity_sha256"]),
        ),
        "resource_shapes": rows,
        "boundary": {
            "candidate_only": True,
            "render_admission": False,
            "capture_local_only": True,
            "seed_rule": (
                "only Phase 611 single-content resource shapes seed a combined "
                "Phase 613 VB/IB/texture pointer identity; conflicting seeds "
                "never narrow candidates"
            ),
            "per_pointer_identity": (
                "narrowing occurs per combined runtime object generation, not "
                "for an entire descriptor-equivalent resource shape"
            ),
            "same_object_meaning": (
                "same capture device + stream-0 VB generation + IB generation "
                "+ exact draw range + CTAB-filtered texture generations"
            ),
            "pointer_equality": (
                "session-local object continuity only; it is not archive path, "
                "payload hash, or portable resource identity"
            ),
            "required_for_promotion": (
                "exact runtime resource path/SHA or payload equality plus "
                "existing Phase 572 strong same-instance gates"
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pointer_report")
    parser.add_argument("material_join")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    pointer = json.loads(
        resolve_input_path(args.pointer_report).read_text(encoding="utf-8")
    )
    material = json.loads(
        resolve_input_path(args.material_join).read_text(encoding="utf-8")
    )
    if not isinstance(pointer, dict) or not isinstance(material, dict):
        raise ValueError("pointer/material inputs must be JSON objects")

    report = build_runtime_pointer_candidate_join(pointer, material)
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
