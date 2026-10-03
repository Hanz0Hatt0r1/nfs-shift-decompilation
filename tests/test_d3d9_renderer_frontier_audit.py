import pytest

from d3d9_renderer_frontier_audit import (
    BASE_FORMAT,
    FORMAT,
    FXO_FORMAT,
    MATERIAL_FORMAT,
    MATERIAL_TEXTURE_FORMAT,
    build_renderer_frontier_audit,
)


def _base():
    return {
        "format": BASE_FORMAT,
        "status": "continue-offline",
        "requirements": [
            {
                "requirement_id": "fx_fxo_exact_candidate_reduction",
                "status": "present-needs-tooling",
                "confidence": "deterministic-report-audit",
                "evidence": ["shader ambiguity"],
                "missing_observation": None,
                "existing_next_step": "old FXO step",
            },
            {
                "requirement_id": "material_bmt_correlation",
                "status": "present-needs-tooling",
                "confidence": "deterministic-report-audit",
                "evidence": ["material ambiguity"],
                "missing_observation": None,
                "existing_next_step": "old material step",
            },
            {
                "requirement_id": "vb_ib_payload_equality",
                "status": "absent-in-capture",
                "confidence": "deterministic-report-audit",
                "evidence": [],
                "missing_observation": "buffer_payload",
                "existing_next_step": "use static scene identity first",
            },
        ],
        "capture_blockers": [],
        "conditional_minimal_capture": [
            {
                "requirement_id": "vb_ib_payload_equality",
                "minimal_missing_observation": "buffer_payload",
                "condition": "use static scene identity first",
            }
        ],
        "policy": {
            "ranking_is_proof": False,
            "missing_event_implies_recapture": False,
        },
    }


def _fxo(*, ready=True, required=2, verified=2, missing=0):
    return {
        "format": FXO_FORMAT,
        "ready": ready,
        "ambiguity_filter": {"required_pair_count": required},
        "summary": {
            "verified_pair_count": verified,
            "missing_required_pair_count": missing,
        },
    }


def _material(*, total=4, resolved=4, remaining=0):
    return {
        "format": MATERIAL_FORMAT,
        "summary": {
            "material_distinct_draw_count": total,
            "single_candidate_draw_count": resolved,
            "remaining_ambiguous_draw_count": remaining,
        },
    }


def _textures(*, total=6, resolved=6, remaining=0, descriptor_survivors=0):
    counts = {}
    if descriptor_survivors:
        counts["single-survivor-by-texture-contradiction-unproven"] = descriptor_survivors
    return {
        "format": MATERIAL_TEXTURE_FORMAT,
        "summary": {
            "input_unresolved_draw_count": total,
            "single_candidate_draw_count": resolved,
            "remaining_unresolved_draw_count": remaining,
            "resolution_status_counts": counts,
        },
    }


def _by_id(report):
    return {row["requirement_id"]: row for row in report["requirements"]}


def test_later_exact_reports_close_fxo_and_material_frontiers():
    report = build_renderer_frontier_audit(
        _base(),
        fxo_provenance=_fxo(),
        material_constants=_material(),
    )
    assert report["format"] == FORMAT
    rows = _by_id(report)
    assert rows["fx_fxo_exact_candidate_reduction"]["status"] == "closed-offline-exact"
    assert rows["material_bmt_correlation"]["status"] == "closed-offline-exact"
    assert report["summary"]["closed_requirement_count"] == 2
    assert report["summary"]["capture_required_now"] is False
    assert rows["vb_ib_payload_equality"]["status"] == "absent-in-capture"


def test_partial_material_resolution_keeps_offline_tooling_frontier():
    report = build_renderer_frontier_audit(
        _base(),
        fxo_provenance=_fxo(),
        material_constants=_material(total=10, resolved=4, remaining=6),
    )
    row = _by_id(report)["material_bmt_correlation"]
    assert row["status"] == "present-needs-tooling"
    assert "remaining material ambiguity=6" in row["evidence"]
    assert "DDS" in row["existing_next_step"]
    assert any(
        item["requirement_id"] == "material_bmt_correlation"
        for item in report["existing_data_requiring_tooling"]
    )


def test_phase622_exact_texture_identity_closes_remaining_material_frontier():
    report = build_renderer_frontier_audit(
        _base(),
        material_constants=_material(total=10, resolved=4, remaining=6),
        material_textures=_textures(total=6, resolved=6, remaining=0),
    )
    row = _by_id(report)["material_bmt_correlation"]
    assert row["status"] == "closed-offline-exact"
    assert row["confidence"] == "exact-dds-runtime-path-sha-evidence"
    assert "resolved by exact material texture identity=6" in row["evidence"]
    assert report["summary"]["phase622_applied"] is True


def test_phase622_descriptor_only_survivor_stays_offline_unproven():
    report = build_renderer_frontier_audit(
        _base(),
        material_constants=_material(total=10, resolved=4, remaining=6),
        material_textures=_textures(total=6, resolved=2, remaining=4, descriptor_survivors=3),
    )
    row = _by_id(report)["material_bmt_correlation"]
    assert row["status"] == "present-needs-tooling"
    assert "descriptor-only single survivors still unproven=3" in row["evidence"]
    assert "portable texture path+SHA" in row["existing_next_step"]
    assert report["policy"]["descriptor_compatibility_is_not_resource_identity"] is True


def test_empty_phase622_does_not_overwrite_phase620_exact_closure():
    report = build_renderer_frontier_audit(
        _base(),
        material_constants=_material(total=4, resolved=4, remaining=0),
        material_textures=_textures(total=0, resolved=0, remaining=0),
    )
    row = _by_id(report)["material_bmt_correlation"]
    assert row["status"] == "closed-offline-exact"
    assert row["confidence"] == "exact-f32-ctab-register-evidence"


def test_partial_fxo_provenance_is_not_closed():
    report = build_renderer_frontier_audit(
        _base(),
        fxo_provenance=_fxo(ready=False, required=3, verified=2, missing=1),
    )
    row = _by_id(report)["fx_fxo_exact_candidate_reduction"]
    assert row["status"] == "present-needs-tooling"
    assert "missing required pairs=1" in row["evidence"]
    assert report["summary"]["phase619_applied"] is True


def test_no_material_distinct_rows_removes_active_material_blocker():
    report = build_renderer_frontier_audit(
        _base(),
        material_constants=_material(total=0, resolved=0, remaining=0),
    )
    row = _by_id(report)["material_bmt_correlation"]
    assert row["status"] == "no-active-blocker"
    assert row["existing_next_step"] is None


def test_absent_capture_observation_stays_conditional_not_required():
    report = build_renderer_frontier_audit(
        _base(),
        fxo_provenance=_fxo(),
        material_constants=_material(),
        material_textures=_textures(total=0, resolved=0, remaining=0),
    )
    assert report["status"] == "continue-offline"
    assert report["capture_blockers"] == []
    assert report["genuinely_absent_capture_observations"] == [
        {
            "requirement_id": "vb_ib_payload_equality",
            "missing_observation": "buffer_payload",
        }
    ]


def test_existing_capture_blocker_is_preserved_not_reinterpreted():
    base = _base()
    base["capture_blockers"] = [
        {
            "hard_requirement": "buffer_payload",
            "requirement_id": "vb_ib_payload_equality",
            "minimal_missing_observation": "buffer_payload",
        }
    ]
    report = build_renderer_frontier_audit(base, fxo_provenance=_fxo())
    assert report["status"] == "capture-required"
    assert report["summary"]["capture_required_now"] is True
    assert report["capture_blockers"] == base["capture_blockers"]


def test_formats_fail_closed():
    with pytest.raises(ValueError, match="base audit"):
        build_renderer_frontier_audit({"format": "wrong"})
    with pytest.raises(ValueError, match="FXO provenance"):
        build_renderer_frontier_audit(_base(), fxo_provenance={"format": "wrong"})
    with pytest.raises(ValueError, match="material constants"):
        build_renderer_frontier_audit(_base(), material_constants={"format": "wrong"})
    with pytest.raises(ValueError, match="material textures"):
        build_renderer_frontier_audit(_base(), material_textures={"format": "wrong"})
