"""Audit renderer proof requirements without turning candidates into proof.

This stage consumes already-produced offline D3D9/scene evidence reports.  It
separates four situations that were previously easy to conflate:

* a capture-local/static proof already exists;
* the needed observation exists but downstream tooling/correlation remains;
* multiple candidates remain and must stay ambiguous;
* the observation is genuinely absent from the historical capture.

A missing event never becomes an automatic request for another capture.  The
caller must explicitly mark that observation as a hard downstream requirement
before the audit emits ``capture_required_now=true``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

FORMAT = "SHIFT.D3D9RendererRequirementAudit/1"

EXPECTED_FORMATS = {
    "shader_use": "SHIFT.D3D9ShaderUseEvidence/1",
    "draw_local": "SHIFT.D3D9TargetDrawLocalEvidence/1",
    "texture_sampler": "SHIFT.D3D9TargetTextureSamplerEvidence/1",
    "ambiguity": "SHIFT.IMBDrawLocalAmbiguityAudit/1",
}

HARD_CAPTURE_REQUIREMENTS = {
    "buffer_payload",
    "sampler_state",
    "portable_texture_identity",
    "texture_snapshot",
}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _rows(report: Mapping[str, Any] | None, key: str = "draws") -> list[Mapping[str, Any]]:
    if not isinstance(report, Mapping):
        return []
    return [row for row in (report.get(key) or []) if isinstance(row, Mapping)]


def _summary(report: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return _mapping(report.get("summary")) if isinstance(report, Mapping) else {}


def _int(value: Any) -> int:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else 0


def _contains_key_fragment(value: Any, fragments: Sequence[str]) -> bool:
    needles = tuple(fragment.lower() for fragment in fragments)
    if isinstance(value, Mapping):
        for key, child in value.items():
            text = str(key).lower()
            if all(fragment in text for fragment in needles):
                return True
            if _contains_key_fragment(child, fragments):
                return True
    elif isinstance(value, list):
        return any(_contains_key_fragment(child, fragments) for child in value)
    return False


def _draw_range_complete(draw: Mapping[str, Any]) -> bool:
    source = _mapping(draw.get("draw_range")) or draw
    return all(
        source.get(key) is not None
        for key in (
            "primitive_type",
            "base_vertex_index",
            "min_vertex_index",
            "num_vertices",
            "start_index",
            "primitive_count",
        )
    )


def _capture_observation(
    texture_sampler: Mapping[str, Any] | None,
    key: str,
) -> Mapping[str, Any]:
    observations = _mapping(texture_sampler.get("capture_observations")) if isinstance(texture_sampler, Mapping) else {}
    return _mapping(observations.get(key))


def _requirement(
    requirement_id: str,
    status: str,
    *,
    evidence: Iterable[str] = (),
    missing_observation: str | None = None,
    existing_next_step: str | None = None,
    confidence: str = "deterministic-report-audit",
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "status": status,
        "confidence": confidence,
        "evidence": sorted({str(item) for item in evidence if item}),
        "missing_observation": missing_observation,
        "existing_next_step": existing_next_step,
    }


def _validate_report(name: str, report: Mapping[str, Any] | None) -> None:
    if report is None:
        return
    expected = EXPECTED_FORMATS[name]
    if report.get("format") != expected:
        raise ValueError(f"{name} report must be {expected}")


def build_renderer_requirement_audit(
    *,
    shader_use: Mapping[str, Any] | None = None,
    draw_local: Mapping[str, Any] | None = None,
    texture_sampler: Mapping[str, Any] | None = None,
    ambiguity: Mapping[str, Any] | None = None,
    hard_requirements: Iterable[str] = (),
) -> dict[str, Any]:
    for name, report in (
        ("shader_use", shader_use),
        ("draw_local", draw_local),
        ("texture_sampler", texture_sampler),
        ("ambiguity", ambiguity),
    ):
        _validate_report(name, report)

    hard = {str(value) for value in hard_requirements}
    unknown_hard = sorted(hard - HARD_CAPTURE_REQUIREMENTS)
    if unknown_hard:
        raise ValueError(f"unknown hard requirements: {', '.join(unknown_hard)}")

    shader_summary = _summary(shader_use)
    shader_draws = _rows(shader_use)
    draw_rows = _rows(draw_local)
    texture_summary = _summary(texture_sampler)
    ambiguity_summary = _summary(ambiguity)

    requirements: list[dict[str, Any]] = []

    shader_creation_count = _int(shader_summary.get("shader_creation_count"))
    requirements.append(_requirement(
        "shader_creation_identity",
        "closed-capture-local" if shader_creation_count else "not-evaluated",
        evidence=[f"observed shader creations={shader_creation_count}"] if shader_creation_count else [],
        existing_next_step=None if shader_creation_count else "run shader-use evidence on the existing capture",
    ))

    exact_shader_draws = _int(shader_summary.get("exact_capture_local_draw_count"))
    requirements.append(_requirement(
        "shader_use_identity",
        "closed-capture-local" if exact_shader_draws else "not-evaluated",
        evidence=[f"draws with exact create+bind provenance={exact_shader_draws}"] if exact_shader_draws else [],
        existing_next_step=None if exact_shader_draws else "run shader-use evidence on the existing capture",
    ))

    exact_pairs = sum(1 for draw in shader_draws if draw.get("shader_pair_sha256"))
    requirements.append(_requirement(
        "vs_ps_pairing",
        "closed-capture-local" if exact_pairs else "not-evaluated",
        evidence=[f"draws with exact VS/PS byte-pair hash={exact_pairs}"] if exact_pairs else [],
        existing_next_step=None if exact_pairs else "derive VS/PS pairing from create/set history",
    ))

    complete_ranges = sum(1 for draw in draw_rows if _draw_range_complete(draw))
    requirements.append(_requirement(
        "draw_indexed_primitive_range",
        "closed-capture-local" if complete_ranges else ("not-evaluated" if not draw_rows else "partial-capture-local"),
        evidence=[f"draws with complete indexed primitive range={complete_ranges}"] if draw_rows else [],
        existing_next_step=None if complete_ranges else "run target draw-local evidence on the existing capture",
    ))

    vb_creation = any(
        _contains_key_fragment(draw, ("vertex", "buffer", "creation", "event"))
        or _contains_key_fragment(draw, ("stream", "creation", "event"))
        for draw in draw_rows
    )
    ib_creation = any(
        _contains_key_fragment(draw, ("index", "buffer", "creation", "event"))
        or _contains_key_fragment(draw, ("indices", "creation", "event"))
        for draw in draw_rows
    )
    requirements.append(_requirement(
        "vb_ib_generation_identity",
        "closed-capture-local" if vb_creation and ib_creation else ("not-evaluated" if not draw_rows else "partial-capture-local"),
        evidence=[
            f"vertex-buffer generation provenance={'observed' if vb_creation else 'unresolved'}",
            f"index-buffer generation provenance={'observed' if ib_creation else 'unresolved'}",
        ] if draw_rows else [],
        existing_next_step=None if vb_creation and ib_creation else "extend draw-local generation extraction before considering recapture",
    ))

    constant_state = any(
        _contains_key_fragment(draw, ("constant", "last", "write"))
        or _contains_key_fragment(draw, ("constant", "snapshot"))
        for draw in draw_rows
    )
    requirements.append(_requirement(
        "ctab_constant_windows",
        "closed-capture-local" if constant_state else ("not-evaluated" if not draw_rows else "present-needs-tooling"),
        evidence=["CTAB-filtered constant/write provenance is present"] if constant_state else [],
        existing_next_step=None if constant_state else "exhaust existing VS/PS constant writes before any recapture request",
    ))

    transform_state = any(
        _contains_key_fragment(draw, ("transform", "signature"))
        or _contains_key_fragment(draw, ("transform", "constant"))
        for draw in draw_rows
    )
    requirements.append(_requirement(
        "world_instance_matrix_semantics",
        "present-needs-tooling" if transform_state else ("not-evaluated" if not draw_rows else "ambiguous"),
        evidence=["transform-like CTAB constants/signatures are present"] if transform_state else [],
        existing_next_step=(
            "prove matrix semantic/order/ownership from CTAB + static scene contracts; name matching remains diagnostic"
            if draw_rows else
            "run draw-local evidence first"
        ),
    ))

    exact_texture_draws = _int(texture_summary.get("exact_capture_local_draw_count"))
    requirements.append(_requirement(
        "texture_creation_binding_identity",
        "closed-capture-local" if exact_texture_draws else "not-evaluated",
        evidence=[f"target draws with exact texture generation+SetTexture provenance={exact_texture_draws}"] if exact_texture_draws else [],
        existing_next_step=None if exact_texture_draws else "run target texture/sampler evidence on the existing capture",
    ))

    sampler_obs = _capture_observation(texture_sampler, "explicit_sampler_state_history")
    sampler_observed = sampler_obs.get("status") == "observed"
    requirements.append(_requirement(
        "sampler_state_snapshots",
        "closed-capture-local" if sampler_observed else ("absent-in-capture" if sampler_obs else "not-evaluated"),
        evidence=[f"explicit SetSamplerState events={_int(sampler_obs.get('observed_count'))}"] if sampler_obs else [],
        missing_observation=None if sampler_observed else (str(sampler_obs.get("minimal_missing_event") or "set_sampler_state") if sampler_obs else None),
        existing_next_step=(
            None if sampler_observed else
            "do not recapture by default: determine whether D3D9 defaults/static material state already proves the required sampler behavior"
        ),
    ))

    portable_obs = _capture_observation(texture_sampler, "portable_resource_path_sha_identity")
    portable_observed = portable_obs.get("status") == "observed"
    requirements.append(_requirement(
        "portable_texture_resource_identity",
        "closed-capture-local" if portable_observed else ("absent-in-capture" if portable_obs else "not-evaluated"),
        evidence=[f"events with path+SHA identity={_int(portable_obs.get('observed_count'))}"] if portable_obs else [],
        missing_observation=None if portable_observed else (str(portable_obs.get("minimal_missing_event") or "resource_path + resource_sha256") if portable_obs else None),
        existing_next_step=(
            None if portable_observed else
            "first use exact BMT/DDS/static dependency evidence; request path+SHA only for survivors that cannot be separated offline"
        ),
    ))

    snapshot_obs = _capture_observation(texture_sampler, "captured_texture_snapshot")
    snapshot_observed = snapshot_obs.get("status") == "observed"
    requirements.append(_requirement(
        "runtime_texture_payload_snapshot",
        "closed-capture-local" if snapshot_observed else ("absent-in-capture" if snapshot_obs else "not-evaluated"),
        evidence=[f"captured texture snapshot events={_int(snapshot_obs.get('observed_count'))}"] if snapshot_obs else [],
        missing_observation=None if snapshot_observed else (str(snapshot_obs.get("minimal_missing_event") or "captured texture snapshot") if snapshot_obs else None),
        existing_next_step=(
            None if snapshot_observed else
            "only require a snapshot when a surviving material ambiguity depends on texture payload equality"
        ),
    ))

    payload_obs = _capture_observation(texture_sampler, "buffer_payload")
    payload_observed = payload_obs.get("status") == "observed"
    requirements.append(_requirement(
        "vb_ib_payload_equality",
        "closed-capture-local" if payload_observed else ("absent-in-capture" if payload_obs else "not-evaluated"),
        evidence=[f"buffer_payload events={_int(payload_obs.get('observed_count'))}"] if payload_obs else [],
        missing_observation=None if payload_observed else (str(payload_obs.get("minimal_missing_event") or "buffer_payload") if payload_obs else None),
        existing_next_step=(
            None if payload_observed else
            "use static scene/instance/LOD references first; capture VB/IB bytes only for geometry identities that remain ambiguous"
        ),
    ))

    class_counts = _mapping(ambiguity_summary.get("ambiguity_class_counts"))
    material_ambiguous = _int(class_counts.get("material-distinct-candidates"))
    shader_ambiguous = _int(class_counts.get("shader-provenance-distinct-candidates"))
    geometry_ambiguous = sum(
        _int(class_counts.get(name))
        for name in (
            "metadata-equivalent-lod-siblings",
            "metadata-equivalent-geometry-alternatives",
        )
    )
    ambiguity_present = bool(class_counts)

    requirements.append(_requirement(
        "material_bmt_correlation",
        "present-needs-tooling" if material_ambiguous else ("no-active-blocker" if ambiguity_present else "not-evaluated"),
        evidence=[f"material-distinct ambiguous draws={material_ambiguous}"] if ambiguity_present else [],
        existing_next_step=(
            "join exact BMT shader parameters and DDS dependencies to draw-local CTAB sampler/constant evidence; keep multiple exact matches ambiguous"
            if material_ambiguous else None
        ),
    ))

    requirements.append(_requirement(
        "fx_fxo_exact_candidate_reduction",
        "present-needs-tooling" if shader_ambiguous else ("no-active-blocker" if ambiguity_present else "not-evaluated"),
        evidence=[f"shader-provenance-distinct ambiguous draws={shader_ambiguous}"] if ambiguity_present else [],
        existing_next_step=(
            "join every surviving candidate to exact embedded FXO VS+PS byte pairs; never select by score/frequency"
            if shader_ambiguous else None
        ),
    ))

    requirements.append(_requirement(
        "scene_resource_exact_draw_attribution",
        "ambiguous" if geometry_ambiguous else ("present-needs-tooling" if ambiguity_present else "not-evaluated"),
        evidence=[f"metadata-equivalent geometry/LOD ambiguous draws={geometry_ambiguous}"] if ambiguity_present else [],
        existing_next_step=(
            "resolve exact static scene-instance/LOD reference before using runtime payload capture"
            if geometry_ambiguous else
            ("continue exact static-candidate correlation; single candidates remain below render-admission proof" if ambiguity_present else None)
        ),
    ))

    absent = [row for row in requirements if row["status"] == "absent-in-capture"]
    tooling = [
        row for row in requirements
        if row["status"] in {"present-needs-tooling", "ambiguous", "partial-capture-local"}
    ]

    hard_to_requirement = {
        "buffer_payload": "vb_ib_payload_equality",
        "sampler_state": "sampler_state_snapshots",
        "portable_texture_identity": "portable_texture_resource_identity",
        "texture_snapshot": "runtime_texture_payload_snapshot",
    }
    rows_by_id = {row["requirement_id"]: row for row in requirements}
    capture_blockers = []
    for hard_id in sorted(hard):
        requirement_id = hard_to_requirement[hard_id]
        row = rows_by_id[requirement_id]
        if row["status"] == "absent-in-capture":
            capture_blockers.append({
                "hard_requirement": hard_id,
                "requirement_id": requirement_id,
                "minimal_missing_observation": row["missing_observation"],
            })

    conditional_capture = [
        {
            "requirement_id": row["requirement_id"],
            "minimal_missing_observation": row["missing_observation"],
            "condition": row["existing_next_step"],
        }
        for row in absent
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "status": "capture-required" if capture_blockers else "continue-offline",
        "summary": {
            "requirement_count": len(requirements),
            "closed_requirement_count": sum(
                1 for row in requirements if row["status"].startswith("closed-")
            ),
            "present_needs_tooling_count": sum(
                1 for row in requirements if row["status"] == "present-needs-tooling"
            ),
            "ambiguous_requirement_count": sum(
                1 for row in requirements if row["status"] == "ambiguous"
            ),
            "absent_in_capture_count": len(absent),
            "capture_required_now": bool(capture_blockers),
            "hard_requirement_count": len(hard),
        },
        "hard_requirements": sorted(hard),
        "requirements": requirements,
        "existing_data_requiring_tooling": [
            {
                "requirement_id": row["requirement_id"],
                "status": row["status"],
                "next_step": row["existing_next_step"],
            }
            for row in tooling
        ],
        "genuinely_absent_capture_observations": [
            {
                "requirement_id": row["requirement_id"],
                "missing_observation": row["missing_observation"],
            }
            for row in absent
        ],
        "capture_blockers": capture_blockers,
        "conditional_minimal_capture": conditional_capture,
        "policy": {
            "ranking_is_proof": False,
            "single_candidate_is_render_admission": False,
            "missing_event_implies_recapture": False,
            "capture_required_only_for_explicit_hard_requirement": True,
            "offline_static_evidence_precedes_recapture": True,
        },
    }


def _load_json(path: str | Path | None) -> Mapping[str, Any] | None:
    if path is None:
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"report is not a JSON object: {path}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output")
    parser.add_argument("--shader-use")
    parser.add_argument("--draw-local")
    parser.add_argument("--texture-sampler")
    parser.add_argument("--ambiguity")
    parser.add_argument(
        "--require",
        action="append",
        default=[],
        choices=sorted(HARD_CAPTURE_REQUIREMENTS),
        help="Mark a capture-only observation as a proven hard downstream requirement.",
    )
    args = parser.parse_args(argv)

    report = build_renderer_requirement_audit(
        shader_use=_load_json(args.shader_use),
        draw_local=_load_json(args.draw_local),
        texture_sampler=_load_json(args.texture_sampler),
        ambiguity=_load_json(args.ambiguity),
        hard_requirements=args.require,
    )
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
