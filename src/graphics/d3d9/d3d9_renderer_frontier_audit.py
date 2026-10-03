"""Fold later exact offline evidence back into the renderer requirement frontier."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.D3D9RendererFrontierAudit/1"
BASE_FORMAT = "SHIFT.D3D9RendererRequirementAudit/1"
FXO_FORMAT = "SHIFT.IMBFXOPairProvenance/1"
MATERIAL_FORMAT = "SHIFT.IMBMaterialConstantCandidateJoin/1"
MATERIAL_TEXTURE_FORMAT = "SHIFT.IMBMaterialTextureCandidateJoin/1"
SCENE_GEOMETRY_FORMAT = "SHIFT.IMBStaticSceneReferenceCandidateJoin/1"
RUNTIME_RESOURCE_DRAW_FORMAT = "SHIFT.IMBRuntimeResourceDrawCandidateJoin/1"
REPEATED_INSTANCE_TRANSFORM_FORMAT = "SHIFT.IMBRepeatedSceneInstanceTransformJoin/1"


def _summary(report: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return report.get("summary") if isinstance(report, Mapping) and isinstance(report.get("summary"), Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def build_renderer_frontier_audit(
    base: Mapping[str, Any],
    *,
    fxo_provenance: Mapping[str, Any] | None = None,
    material_constants: Mapping[str, Any] | None = None,
    material_textures: Mapping[str, Any] | None = None,
    scene_geometry: Mapping[str, Any] | None = None,
    runtime_resource_draw: Mapping[str, Any] | None = None,
    repeated_instance_transforms: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if base.get("format") != BASE_FORMAT:
        raise ValueError(f"base audit must be {BASE_FORMAT}")
    if fxo_provenance is not None and fxo_provenance.get("format") != FXO_FORMAT:
        raise ValueError(f"FXO provenance must be {FXO_FORMAT}")
    if material_constants is not None and material_constants.get("format") != MATERIAL_FORMAT:
        raise ValueError(f"material constants must be {MATERIAL_FORMAT}")
    if material_textures is not None and material_textures.get("format") != MATERIAL_TEXTURE_FORMAT:
        raise ValueError(f"material textures must be {MATERIAL_TEXTURE_FORMAT}")
    if scene_geometry is not None and scene_geometry.get("format") != SCENE_GEOMETRY_FORMAT:
        raise ValueError(f"scene geometry must be {SCENE_GEOMETRY_FORMAT}")
    if runtime_resource_draw is not None and runtime_resource_draw.get("format") != RUNTIME_RESOURCE_DRAW_FORMAT:
        raise ValueError(f"runtime resource draw must be {RUNTIME_RESOURCE_DRAW_FORMAT}")
    if repeated_instance_transforms is not None and repeated_instance_transforms.get("format") != REPEATED_INSTANCE_TRANSFORM_FORMAT:
        raise ValueError(f"repeated instance transforms must be {REPEATED_INSTANCE_TRANSFORM_FORMAT}")

    requirements = [dict(row) for row in (base.get("requirements") or []) if isinstance(row, Mapping)]
    by_id = {str(row.get("requirement_id")): row for row in requirements}

    fxo_row = by_id.get("fx_fxo_exact_candidate_reduction")
    if fxo_row is not None and fxo_provenance is not None:
        summary = _summary(fxo_provenance)
        missing = _int(summary.get("missing_required_pair_count"))
        verified = _int(summary.get("verified_pair_count"))
        required = _int((fxo_provenance.get("ambiguity_filter") or {}).get("required_pair_count"))
        if fxo_provenance.get("ready") is True and missing == 0:
            fxo_row.update({
                "status": "closed-offline-exact",
                "confidence": "exact-byte-equality",
                "evidence": [
                    f"Phase 619 verified exact FXO VS/PS pairs={verified}",
                    f"required shader-provenance pairs={required}",
                ],
                "missing_observation": None,
                "existing_next_step": None,
            })
        else:
            fxo_row.update({
                "status": "present-needs-tooling",
                "confidence": "deterministic-report-audit",
                "evidence": [
                    f"Phase 619 verified exact FXO VS/PS pairs={verified}",
                    f"missing required pairs={missing}",
                ],
                "existing_next_step": "resolve the listed Phase 619 missing exact FXO pair provenance from the existing corpus before recapture",
            })

    material_row = by_id.get("material_bmt_correlation")
    if material_row is not None and material_constants is not None:
        summary = _summary(material_constants)
        total = _int(summary.get("material_distinct_draw_count"))
        resolved = _int(summary.get("single_candidate_draw_count"))
        remaining = _int(summary.get("remaining_ambiguous_draw_count"))
        if total == 0:
            material_row.update({
                "status": "no-active-blocker",
                "confidence": "deterministic-report-audit",
                "evidence": ["Phase 620 material-distinct draws=0"],
                "missing_observation": None,
                "existing_next_step": None,
            })
        elif remaining == 0 and resolved == total:
            material_row.update({
                "status": "closed-offline-exact",
                "confidence": "exact-f32-ctab-register-evidence",
                "evidence": [
                    f"Phase 620 material-distinct draws={total}",
                    f"resolved by exact material constants={resolved}",
                ],
                "missing_observation": None,
                "existing_next_step": None,
            })
        else:
            material_row.update({
                "status": "present-needs-tooling",
                "confidence": "deterministic-report-audit",
                "evidence": [
                    f"Phase 620 material-distinct draws={total}",
                    f"resolved by exact material constants={resolved}",
                    f"remaining material ambiguity={remaining}",
                ],
                "missing_observation": None,
                "existing_next_step": (
                    "apply exact BMT/DDS sampler descriptor/content evidence only to the remaining Phase 620 ambiguous rows; "
                    "do not request texture snapshots unless payload identity becomes a proven discriminator"
                ),
            })

    if material_row is not None and material_textures is not None:
        summary = _summary(material_textures)
        total = _int(summary.get("input_unresolved_draw_count"))
        resolved = _int(summary.get("single_candidate_draw_count"))
        remaining = _int(summary.get("remaining_unresolved_draw_count"))
        resolution_counts = summary.get("resolution_status_counts")
        resolution_counts = resolution_counts if isinstance(resolution_counts, Mapping) else {}
        descriptor_survivors = _int(
            resolution_counts.get("single-survivor-by-texture-contradiction-unproven")
        )
        if total == 0:
            if material_row.get("status") != "closed-offline-exact":
                material_row.update({
                    "status": "no-active-blocker",
                    "confidence": "deterministic-report-audit",
                    "evidence": ["Phase 622 unresolved material draws=0"],
                    "missing_observation": None,
                    "existing_next_step": None,
                })
        elif remaining == 0 and resolved == total:
            material_row.update({
                "status": "closed-offline-exact",
                "confidence": "exact-dds-runtime-path-sha-evidence",
                "evidence": [
                    f"Phase 622 unresolved material draws={total}",
                    f"resolved by exact material texture identity={resolved}",
                ],
                "missing_observation": None,
                "existing_next_step": None,
            })
        else:
            evidence = [
                f"Phase 622 unresolved material draws={total}",
                f"resolved by exact material texture identity={resolved}",
                f"remaining material ambiguity={remaining}",
            ]
            if descriptor_survivors:
                evidence.append(
                    f"descriptor-only single survivors still unproven={descriptor_survivors}"
                )
            material_row.update({
                "status": "present-needs-tooling",
                "confidence": "deterministic-report-audit",
                "evidence": evidence,
                "missing_observation": None,
                "existing_next_step": (
                    "continue exact offline scene/instance and candidate correlation for the Phase 622 survivors; "
                    "descriptor compatibility is not texture identity, and portable texture path+SHA should become a hard capture requirement only if those survivors remain a proven renderer blocker"
                ),
            })

    scene_row = by_id.get("scene_resource_exact_draw_attribution")
    if scene_row is not None and scene_geometry is not None:
        summary = _summary(scene_geometry)
        total = _int(summary.get("geometry_ambiguous_draw_count"))
        resolved = _int(summary.get("draw_attribution_resolved_count"))
        remaining = _int(summary.get("remaining_geometry_ambiguous_draw_count"))
        single_static = _int(summary.get("single_scene_referenced_candidate_draw_count"))
        lod_families = _int(summary.get("source_backed_lod_family_draw_count"))
        ready_sgbs = _int(summary.get("ready_sgb_count"))
        blocked_sgbs = _int(summary.get("blocked_sgb_count"))

        if total == 0:
            scene_row.update({
                "status": "no-active-blocker",
                "confidence": "deterministic-report-audit",
                "evidence": ["Phase 623 geometry-ambiguous draws=0"],
                "missing_observation": None,
                "existing_next_step": None,
            })
        elif remaining == 0 and resolved == total:
            scene_row.update({
                "status": "closed-offline-exact",
                "confidence": "exact-static-scene-plus-instance-selection-evidence",
                "evidence": [
                    f"Phase 623 geometry-ambiguous draws={total}",
                    f"exact draw attributions resolved={resolved}",
                ],
                "missing_observation": None,
                "existing_next_step": None,
            })
        else:
            evidence = [
                f"Phase 623 geometry-ambiguous draws={total}",
                f"single static scene resource candidates={single_static}",
                f"source-backed LOD families={lod_families}",
                f"remaining exact draw attribution ambiguity={remaining}",
                f"ready source-backed SGB decodes={ready_sgbs}",
            ]
            if blocked_sgbs:
                evidence.append(f"blocked source-backed SGB decodes={blocked_sgbs}")
            if blocked_sgbs:
                next_step = (
                    "complete source-backed SGB coverage for the listed blocked scene files, then attach exact transform/spatial or instance/LOD selection evidence; "
                    "do not request buffer payload while a static scene gate remains incomplete"
                )
            elif lod_families:
                next_step = (
                    "join the recovered source-backed LOD slots/thresholds to exact transform/spatial instance/LOD selection evidence from the existing capture; "
                    "only consider buffer payload if that exact instance/LOD selection still cannot distinguish the draw"
                )
            elif single_static:
                next_step = (
                    "attach an exact transform/spatial scene-instance witness to the single static resource candidate; "
                    "do not promote static reference alone to draw attribution"
                )
            else:
                next_step = (
                    "continue exact static scene/root/resource correlation for the unresolved geometry candidates before considering runtime buffer payload"
                )
            scene_row.update({
                "status": "ambiguous",
                "confidence": "deterministic-report-audit",
                "evidence": evidence,
                "missing_observation": None,
                "existing_next_step": next_step,
            })

    # Phase 624 is stronger than Phase 623 resource-only static evidence because
    # it joins one strong, same-instance-gated runtime resource attribution to
    # the exact raw draw event index. Repeated SGB placements of the same exact
    # resource remain an instance-selection problem rather than a geometry one.
    if scene_row is not None and runtime_resource_draw is not None:
        summary = _summary(runtime_resource_draw)
        total = _int(summary.get("input_geometry_draw_count"))
        exact_resource = _int(summary.get("exact_resource_draw_count"))
        exact_scene = _int(summary.get("exact_scene_resource_draw_count"))
        repeated = _int(summary.get("repeated_scene_instance_draw_count"))
        conflicts = _int(summary.get("conflict_draw_count"))
        remaining = _int(summary.get("remaining_scene_draw_ambiguity_count"))

        if total == 0:
            if scene_row.get("status") != "closed-offline-exact":
                scene_row.update({
                    "status": "no-active-blocker",
                    "confidence": "deterministic-report-audit",
                    "evidence": ["Phase 624 geometry draw set=0"],
                    "missing_observation": None,
                    "existing_next_step": None,
                })
        elif remaining == 0 and exact_scene == total:
            scene_row.update({
                "status": "closed-offline-exact",
                "confidence": "exact-same-event-runtime-resource-plus-static-scene-evidence",
                "evidence": [
                    f"Phase 624 geometry draws={total}",
                    f"exact same-event runtime resource draws={exact_resource}",
                    f"exact unique scene resource draws={exact_scene}",
                ],
                "missing_observation": None,
                "existing_next_step": None,
            })
        else:
            evidence = [
                f"Phase 624 geometry draws={total}",
                f"exact same-event runtime resource draws={exact_resource}",
                f"exact unique scene resource draws={exact_scene}",
                f"repeated scene instances after resource proof={repeated}",
                f"runtime/static conflicts={conflicts}",
                f"remaining scene draw ambiguity={remaining}",
            ]
            if conflicts:
                next_step = (
                    "inspect the listed exact same-event runtime/static conflicts and existing candidate provenance; "
                    "do not rank a conflicting candidate set and do not request buffer payload while the contradiction is unresolved"
                )
            elif repeated:
                next_step = (
                    "join exact draw-local world-matrix/transform or source-backed spatial evidence to the repeated SGB references of the already-proven resource; "
                    "VB/IB payload is irrelevant to repeated-instance selection"
                )
            elif exact_resource:
                next_step = (
                    "complete exact static scene reference/instance correlation for the resources already proven at the same draw event; "
                    "do not recapture geometry payload"
                )
            else:
                next_step = (
                    "exhaust existing IMBRuntimeCapturePipeline same-event strong attribution rows for the Phase 623 candidate set before considering any buffer payload observation"
                )
            scene_row.update({
                "status": "ambiguous",
                "confidence": "deterministic-report-audit",
                "evidence": evidence,
                "missing_observation": None,
                "existing_next_step": next_step,
            })

    # Phase 625 resolves only repeated scene placements after Phase 624 has
    # already proven the exact IMB/LOD resource at the same captured draw.
    # Exact float32 transform observations can select one placement, but missing
    # or equal world matrices remain ambiguity rather than negative evidence.
    if scene_row is not None and repeated_instance_transforms is not None:
        summary = _summary(repeated_instance_transforms)
        total = _int(summary.get("input_geometry_draw_count"))
        already_exact = _int(summary.get("already_exact_scene_resource_draw_count"))
        repeated = _int(summary.get("repeated_instance_input_draw_count"))
        resolved = _int(summary.get("resolved_repeated_instance_draw_count"))
        unresolved = _int(summary.get("unresolved_repeated_instance_draw_count"))
        upstream = _int(summary.get("upstream_non_instance_ambiguity_count"))
        remaining = _int(summary.get("remaining_scene_draw_ambiguity_count"))
        resolution_counts = summary.get("resolution_status_counts")
        resolution_counts = resolution_counts if isinstance(resolution_counts, Mapping) else {}
        incomplete = _int(resolution_counts.get("blocked-incomplete-scene-world-matrices"))
        missing_transform = _int(resolution_counts.get("draw-local-transform-observation-missing"))
        equal_matrices = _int(resolution_counts.get("ambiguous-equal-or-multiple-world-matrix-matches"))

        if total == 0:
            if scene_row.get("status") != "closed-offline-exact":
                scene_row.update({
                    "status": "no-active-blocker",
                    "confidence": "deterministic-report-audit",
                    "evidence": ["Phase 625 geometry draw set=0"],
                    "missing_observation": None,
                    "existing_next_step": None,
                })
        elif repeated_instance_transforms.get("ready") is True and remaining == 0:
            scene_row.update({
                "status": "closed-offline-exact",
                "confidence": "exact-same-draw-f32-world-matrix-instance-evidence",
                "evidence": [
                    f"Phase 625 geometry draws={total}",
                    f"already exact unique scene resource draws={already_exact}",
                    f"repeated instance draws={repeated}",
                    f"repeated instances resolved by exact float32 world matrices={resolved}",
                ],
                "missing_observation": None,
                "existing_next_step": None,
            })
        else:
            evidence = [
                f"Phase 625 geometry draws={total}",
                f"already exact unique scene resource draws={already_exact}",
                f"repeated instance draws={repeated}",
                f"repeated instances resolved by exact float32 world matrices={resolved}",
                f"unresolved repeated instances={unresolved}",
                f"upstream non-instance ambiguity={upstream}",
                f"remaining scene draw ambiguity={remaining}",
            ]
            if incomplete:
                evidence.append(f"incomplete scene world-matrix candidate sets={incomplete}")
            if missing_transform:
                evidence.append(f"same-draw transform observations missing from pipeline={missing_transform}")
            if equal_matrices:
                evidence.append(f"equal/multiple exact world-matrix matches={equal_matrices}")

            if upstream:
                next_step = (
                    "resolve the Phase 624 non-instance blockers first; Phase 625 intentionally touches only repeated placements of already-proven resources"
                )
            elif incomplete:
                next_step = (
                    "complete source-backed world-matrix materialization/root consensus for every surviving repeated scene candidate, then rerun exact float32 transform matching; "
                    "a missing candidate matrix is not a contradiction and VB/IB payload cannot repair it"
                )
            elif equal_matrices:
                next_step = (
                    "join source-backed placement spatial/partition/visibility evidence for the equal-transform candidates; "
                    "VB/IB payload cannot distinguish placements of the same exact mesh and equal world matrix"
                )
            elif missing_transform:
                next_step = (
                    "exhaust the existing raw/draw-local D3D9 constant state for the exact Phase 624 event before treating transform state as absent; "
                    "do not request geometry buffer payload"
                )
            else:
                next_step = (
                    "continue exact source-backed scene placement/spatial correlation for the unresolved repeated instances; do not rank and do not request VB/IB payload"
                )
            scene_row.update({
                "status": "ambiguous",
                "confidence": "deterministic-report-audit",
                "evidence": evidence,
                "missing_observation": None,
                "existing_next_step": next_step,
            })

    absent = [row for row in requirements if row.get("status") == "absent-in-capture"]
    tooling = [
        row for row in requirements
        if row.get("status") in {"present-needs-tooling", "ambiguous", "partial-capture-local"}
    ]
    capture_blockers = list(base.get("capture_blockers") or [])
    result = {
        "format": FORMAT,
        "version": 1,
        "status": "capture-required" if capture_blockers else "continue-offline",
        "summary": {
            "requirement_count": len(requirements),
            "closed_requirement_count": sum(
                str(row.get("status") or "").startswith("closed-") for row in requirements
            ),
            "present_needs_tooling_count": sum(
                row.get("status") == "present-needs-tooling" for row in requirements
            ),
            "ambiguous_requirement_count": sum(
                row.get("status") == "ambiguous" for row in requirements
            ),
            "absent_in_capture_count": len(absent),
            "capture_required_now": bool(capture_blockers),
            "phase619_applied": fxo_provenance is not None,
            "phase620_applied": material_constants is not None,
            "phase622_applied": material_textures is not None,
            "phase623_applied": scene_geometry is not None,
            "phase624_applied": runtime_resource_draw is not None,
            "phase625_applied": repeated_instance_transforms is not None,
        },
        "requirements": requirements,
        "existing_data_requiring_tooling": [
            {
                "requirement_id": row.get("requirement_id"),
                "status": row.get("status"),
                "next_step": row.get("existing_next_step"),
            }
            for row in tooling
        ],
        "genuinely_absent_capture_observations": [
            {
                "requirement_id": row.get("requirement_id"),
                "missing_observation": row.get("missing_observation"),
            }
            for row in absent
        ],
        "capture_blockers": capture_blockers,
        "conditional_minimal_capture": list(base.get("conditional_minimal_capture") or []),
        "source_reports": {
            "base": BASE_FORMAT,
            "fxo_provenance": fxo_provenance.get("format") if fxo_provenance else None,
            "material_constants": material_constants.get("format") if material_constants else None,
            "material_textures": material_textures.get("format") if material_textures else None,
            "scene_geometry": scene_geometry.get("format") if scene_geometry else None,
            "runtime_resource_draw": runtime_resource_draw.get("format") if runtime_resource_draw else None,
            "repeated_instance_transforms": repeated_instance_transforms.get("format") if repeated_instance_transforms else None,
        },
        "policy": {
            **dict(base.get("policy") or {}),
            "later_exact_offline_evidence_updates_frontier": True,
            "ambiguity_is_not_proof": True,
            "descriptor_compatibility_is_not_resource_identity": True,
            "static_scene_reference_is_draw_attribution": False,
            "source_backed_lod_family_is_selected_lod": False,
            "same_event_runtime_path_sha_is_resource_draw_identity": True,
            "resource_draw_identity_is_repeated_instance_identity": False,
            "exact_f32_world_matrix_is_instance_witness": True,
            "incomplete_world_matrix_is_contradiction": False,
            "equal_world_matrices_select_instance": False,
            "buffer_payload_relevant_to_repeated_instance": False,
        },
    }
    return result


def _load(path: str | None) -> Mapping[str, Any] | None:
    if not path:
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"report is not a JSON object: {path}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_audit")
    parser.add_argument("output")
    parser.add_argument("--fxo-provenance")
    parser.add_argument("--material-constants")
    parser.add_argument("--material-textures")
    parser.add_argument("--scene-geometry")
    parser.add_argument("--runtime-resource-draw")
    parser.add_argument("--repeated-instance-transforms")
    args = parser.parse_args(argv)
    base = _load(args.base_audit)
    assert base is not None
    report = build_renderer_frontier_audit(
        base,
        fxo_provenance=_load(args.fxo_provenance),
        material_constants=_load(args.material_constants),
        material_textures=_load(args.material_textures),
        scene_geometry=_load(args.scene_geometry),
        runtime_resource_draw=_load(args.runtime_resource_draw),
        repeated_instance_transforms=_load(args.repeated_instance_transforms),
    )
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
