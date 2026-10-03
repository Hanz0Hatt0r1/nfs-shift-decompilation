import pytest

from d3d9_renderer_requirement_audit import (
    FORMAT,
    build_renderer_requirement_audit,
)


def _shader_use():
    return {
        "format": "SHIFT.D3D9ShaderUseEvidence/1",
        "summary": {
            "shader_creation_count": 4,
            "exact_capture_local_draw_count": 2,
        },
        "draws": [
            {"shader_pair_sha256": "a" * 64},
            {"shader_pair_sha256": "b" * 64},
        ],
    }


def _draw_local():
    return {
        "format": "SHIFT.D3D9TargetDrawLocalEvidence/1",
        "draws": [{
            "draw_range": {
                "primitive_type": 4,
                "base_vertex_index": 0,
                "min_vertex_index": 0,
                "num_vertices": 24,
                "start_index": 12,
                "primitive_count": 8,
            },
            "streams": [{
                "vertex_buffer_creation_event_index": 10,
            }],
            "indices": {
                "index_buffer_creation_event_index": 11,
            },
            "vertex_constant_snapshot": [{
                "register": 0,
                "last_write_event_index": 20,
            }],
            "transform_like_constant_signature_sha256": "c" * 64,
        }],
    }


def _texture_sampler(*, sampler=False, portable=False, snapshot=False, payload=False):
    def observation(observed, missing):
        return {
            "status": "observed" if observed else "not-observed-in-capture",
            "observed_count": 1 if observed else 0,
            "minimal_missing_event": None if observed else missing,
        }

    return {
        "format": "SHIFT.D3D9TargetTextureSamplerEvidence/1",
        "summary": {
            "exact_capture_local_draw_count": 2,
        },
        "capture_observations": {
            "explicit_sampler_state_history": observation(sampler, "set_sampler_state"),
            "portable_resource_path_sha_identity": observation(
                portable, "resource_path + resource_sha256 on one resource event"
            ),
            "captured_texture_snapshot": observation(
                snapshot, "snapshot_status=captured + snapshot_paths"
            ),
            "buffer_payload": observation(payload, "buffer_payload"),
        },
    }


def _ambiguity():
    return {
        "format": "SHIFT.IMBDrawLocalAmbiguityAudit/1",
        "summary": {
            "ambiguity_class_counts": {
                "material-distinct-candidates": 17,
                "shader-provenance-distinct-candidates": 5,
                "metadata-equivalent-lod-siblings": 9,
            }
        },
    }


def _by_id(report):
    return {row["requirement_id"]: row for row in report["requirements"]}


def test_audit_prefers_existing_tooling_and_does_not_request_capture_by_default():
    report = build_renderer_requirement_audit(
        shader_use=_shader_use(),
        draw_local=_draw_local(),
        texture_sampler=_texture_sampler(),
        ambiguity=_ambiguity(),
    )

    assert report["format"] == FORMAT
    assert report["status"] == "continue-offline"
    assert report["summary"]["capture_required_now"] is False
    rows = _by_id(report)
    assert rows["shader_creation_identity"]["status"] == "closed-capture-local"
    assert rows["shader_use_identity"]["status"] == "closed-capture-local"
    assert rows["vs_ps_pairing"]["status"] == "closed-capture-local"
    assert rows["draw_indexed_primitive_range"]["status"] == "closed-capture-local"
    assert rows["vb_ib_generation_identity"]["status"] == "closed-capture-local"
    assert rows["ctab_constant_windows"]["status"] == "closed-capture-local"
    assert rows["world_instance_matrix_semantics"]["status"] == "present-needs-tooling"
    assert rows["texture_creation_binding_identity"]["status"] == "closed-capture-local"
    assert rows["sampler_state_snapshots"]["status"] == "absent-in-capture"
    assert rows["vb_ib_payload_equality"]["status"] == "absent-in-capture"
    assert rows["material_bmt_correlation"]["status"] == "present-needs-tooling"
    assert rows["fx_fxo_exact_candidate_reduction"]["status"] == "present-needs-tooling"
    assert rows["scene_resource_exact_draw_attribution"]["status"] == "ambiguous"
    assert report["capture_blockers"] == []
    assert report["policy"]["missing_event_implies_recapture"] is False
    assert report["policy"]["ranking_is_proof"] is False


def test_capture_is_requested_only_when_absent_observation_is_explicit_hard_requirement():
    report = build_renderer_requirement_audit(
        texture_sampler=_texture_sampler(),
        hard_requirements=["buffer_payload"],
    )

    assert report["status"] == "capture-required"
    assert report["summary"]["capture_required_now"] is True
    assert report["capture_blockers"] == [{
        "hard_requirement": "buffer_payload",
        "requirement_id": "vb_ib_payload_equality",
        "minimal_missing_observation": "buffer_payload",
    }]


def test_observed_capture_fields_close_only_their_own_requirements():
    report = build_renderer_requirement_audit(
        texture_sampler=_texture_sampler(
            sampler=True,
            portable=True,
            snapshot=True,
            payload=True,
        ),
        hard_requirements=[
            "buffer_payload",
            "sampler_state",
            "portable_texture_identity",
            "texture_snapshot",
        ],
    )

    rows = _by_id(report)
    assert rows["sampler_state_snapshots"]["status"] == "closed-capture-local"
    assert rows["portable_texture_resource_identity"]["status"] == "closed-capture-local"
    assert rows["runtime_texture_payload_snapshot"]["status"] == "closed-capture-local"
    assert rows["vb_ib_payload_equality"]["status"] == "closed-capture-local"
    assert report["capture_blockers"] == []
    assert report["summary"]["capture_required_now"] is False


def test_material_and_shader_ambiguity_stays_explicit_without_ranking():
    report = build_renderer_requirement_audit(ambiguity=_ambiguity())
    rows = _by_id(report)

    material = rows["material_bmt_correlation"]
    shader = rows["fx_fxo_exact_candidate_reduction"]
    assert material["status"] == "present-needs-tooling"
    assert material["evidence"] == ["material-distinct ambiguous draws=17"]
    assert shader["status"] == "present-needs-tooling"
    assert shader["evidence"] == ["shader-provenance-distinct ambiguous draws=5"]
    assert report["policy"]["ranking_is_proof"] is False


def test_invalid_report_format_fails_closed():
    with pytest.raises(ValueError, match="shader_use report must be"):
        build_renderer_requirement_audit(
            shader_use={"format": "wrong"},
        )


def test_unknown_hard_requirement_fails_closed():
    with pytest.raises(ValueError, match="unknown hard requirements"):
        build_renderer_requirement_audit(
            hard_requirements=["invented-observation"],
        )
