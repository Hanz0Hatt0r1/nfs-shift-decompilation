import imb_runtime_capture_pipeline as pipeline


def _binding(index, *, first_index):
    return {
        "binding_index": index,
        "imb_path": f"tracks/silverstone/object_{index}.imb",
        "imb_sha256": str(index + 1) * 64,
        "draw_range": {
            "first_index": first_index,
            "index_count": 6,
            "primitive_count": 2,
        },
    }


def _target_set():
    return {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "capture_ready": True,
        "same_instance_match_ready": True,
        "binding_target_count": 2,
        "binding_targets": [
            _binding(0, first_index=0),
            _binding(1, first_index=12),
        ],
        "unique_targets": [],
    }


def test_route_prefilter_candidates_requires_exact_draw_range():
    report = pipeline.route_prefilter_candidate_bindings(
        _target_set(),
        {
            "candidate_draws": [
                {
                    "line": 10,
                    "frame": 2,
                    "event_index": 7,
                    "draw_ordinal": 3,
                    "start_index": 0,
                    "primitive_count": 2,
                    "candidate_binding_indices": [0, 1],
                },
                {
                    "line": 11,
                    "frame": 2,
                    "event_index": 8,
                    "draw_ordinal": 4,
                    "start_index": 99,
                    "primitive_count": 2,
                    "candidate_binding_indices": [0, 1],
                },
            ]
        },
    )

    assert report["routed_binding_indices"] == [0]
    assert report["routed_binding_count"] == 1
    assert report["draw_routes"][0]["routed_binding_indices"] == [0]
    assert report["draw_routes"][1]["routed_binding_indices"] == []
    assert report["boundary"]["resource_identity_proven"] is False


def test_pipeline_runs_runtime_evidence_only_for_routed_resources(monkeypatch):
    target_set = _target_set()

    monkeypatch.setattr(
        pipeline,
        "prefilter_imb_raw_capture",
        lambda targets, events: {
            "format": "SHIFT.IMBRawCaptureShaderPrefilter/1",
            "prefilter_ready": True,
            "blocking_reasons": [],
            "summary": {"candidate_draw_count": 1},
            "candidate_draws": [{
                "line": 1,
                "frame": 1,
                "event_index": 1,
                "draw_ordinal": 1,
                "start_index": 0,
                "primitive_count": 2,
                "candidate_binding_indices": [0, 1],
            }],
        },
    )
    monkeypatch.setattr(
        pipeline,
        "build_imb_runtime_resource_evidence_set",
        lambda targets: {
            "format": "SHIFT.IMBRuntimeResourceEvidenceSet/1",
            "ready": True,
            "blocking_reasons": [],
            "resource_count": 2,
            "binding_target_count": 2,
            "resources": [
                {
                    "resource_index": 0,
                    "archive": "A.bff",
                    "resource_path": "tracks/silverstone/object_0.imb",
                    "resource_sha256": "1" * 64,
                    "binding_indices": [0],
                    "runtime_binding_input": {"resource": "object_0.imb"},
                },
                {
                    "resource_index": 1,
                    "archive": "A.bff",
                    "resource_path": "tracks/silverstone/object_1.imb",
                    "resource_sha256": "2" * 64,
                    "binding_indices": [1],
                    "runtime_binding_input": {"resource": "object_1.imb"},
                },
            ],
        },
    )

    runtime_calls = []

    def fake_runtime(events, *, meb_resource, usage_ordinal_map):
        runtime_calls.append(meb_resource["resource"])
        return {
            "format": "SHIFT.D3D9RuntimeBindingEvidence/1",
            "status": "ready",
            "trace": {"event_count": len(events)},
            "blocking_reasons": [],
            "same_instance_gate": {
                "status": "ready",
                "ready": True,
                "candidate_frames": [{"frame": 1, "draw_index": 0}],
                "blocking_reasons": [],
            },
        }

    monkeypatch.setattr(
        pipeline,
        "build_runtime_binding_evidence",
        fake_runtime,
    )
    monkeypatch.setattr(
        pipeline,
        "match_imb_runtime_shader_variants",
        lambda targets, runtime: {
            "format": "SHIFT.IMBRuntimeShaderVariantMatch/1",
            "status": "ready",
            "ready": True,
            "blocking_reasons": [],
            "summary": {
                "resource_binding_count": 1,
                "attributed_binding_count": 1,
            },
            "binding_results": [{
                "binding_index": 0,
                "observed": True,
                "attributed": True,
            }],
        },
    )

    report = pipeline.build_imb_runtime_capture_pipeline(
        target_set,
        [{"event": "noop"}],
        usage_ordinal_map={0: 0},
    )

    assert runtime_calls == ["object_0.imb"]
    assert report["pipeline_ready"] is True
    assert report["attribution_complete"] is True
    assert report["status"] == "ready"
    assert report["summary"]["routed_binding_count"] == 1
    assert report["summary"]["candidate_resource_count"] == 1
    assert report["summary"]["runtime_report_count"] == 1
    assert report["summary"]["attributed_candidate_binding_count"] == 1


def test_missing_usage_map_keeps_orchestration_fail_closed(monkeypatch):
    target_set = _target_set()

    monkeypatch.setattr(
        pipeline,
        "prefilter_imb_raw_capture",
        lambda targets, events: {
            "prefilter_ready": True,
            "blocking_reasons": [],
            "summary": {"candidate_draw_count": 0},
            "candidate_draws": [],
        },
    )
    monkeypatch.setattr(
        pipeline,
        "build_imb_runtime_resource_evidence_set",
        lambda targets: {
            "format": "SHIFT.IMBRuntimeResourceEvidenceSet/1",
            "ready": True,
            "blocking_reasons": [],
            "resource_count": 2,
            "binding_target_count": 2,
            "resources": [],
        },
    )

    report = pipeline.build_imb_runtime_capture_pipeline(
        target_set,
        [],
        usage_ordinal_map=None,
    )

    assert report["pipeline_ready"] is False
    assert report["attribution_complete"] is False
    assert report["status"] == "blocked"
    assert "usage-ordinal-map:not-supplied" in report["blocking_reasons"]


def test_prefilter_draw_without_range_match_does_not_spawn_runtime_reports(
    monkeypatch,
):
    target_set = _target_set()
    monkeypatch.setattr(
        pipeline,
        "prefilter_imb_raw_capture",
        lambda targets, events: {
            "prefilter_ready": True,
            "blocking_reasons": [],
            "summary": {"candidate_draw_count": 1},
            "candidate_draws": [{
                "start_index": 99,
                "primitive_count": 2,
                "candidate_binding_indices": [0, 1],
            }],
        },
    )
    monkeypatch.setattr(
        pipeline,
        "build_imb_runtime_resource_evidence_set",
        lambda targets: {
            "format": "SHIFT.IMBRuntimeResourceEvidenceSet/1",
            "ready": True,
            "blocking_reasons": [],
            "resource_count": 2,
            "binding_target_count": 2,
            "resources": [{
                "resource_index": 0,
                "binding_indices": [0],
                "runtime_binding_input": {"resource": "unused.imb"},
            }],
        },
    )

    def unexpected(*args, **kwargs):
        raise AssertionError("runtime evidence should not be built")

    monkeypatch.setattr(
        pipeline,
        "build_runtime_binding_evidence",
        unexpected,
    )

    report = pipeline.build_imb_runtime_capture_pipeline(
        target_set,
        [],
        usage_ordinal_map={0: 0},
    )

    assert report["pipeline_ready"] is True
    assert report["status"] == "not-found"
    assert report["summary"]["routed_binding_count"] == 0
    assert report["summary"]["runtime_report_count"] == 0
