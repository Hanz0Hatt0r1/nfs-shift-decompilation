from tools.audit_imb_material_shader_ranking import (
    FORMAT,
    _candidate_identity,
    _compact_candidate,
    summarize_ranking_rows,
)


def test_ranking_summary_counts_only_unique_rows_as_ready():
    report = summarize_ranking_rows([
        {
            "shader_family": "basicinstanced",
            "selection_status": "unique",
            "blocking_reasons": [],
        },
        {
            "shader_family": "basicinstanced",
            "selection_status": "ambiguous",
            "blocking_reasons": ["shader-selection:ambiguous"],
        },
        {
            "shader_family": "foliageinstanced",
            "selection_status": "heuristic",
            "blocking_reasons": ["shader-selection:heuristic"],
        },
        {
            "shader_family": "skintestinstanced",
            "selection_status": "none",
            "blocking_reasons": ["shader-selection:none"],
        },
    ])

    assert report["format"] == FORMAT
    assert report["status"] == "runtime-gated"
    assert report["ready"] is False
    assert report["primitive_binding_count"] == 4
    assert report["unique_selection_count"] == 1
    assert report["ambiguous_selection_count"] == 1
    assert report["heuristic_selection_count"] == 1
    assert report["no_selection_count"] == 1
    assert report["runtime_target_count"] == 3
    assert report["selection_status_counts"] == {
        "ambiguous": 1,
        "heuristic": 1,
        "none": 1,
        "unique": 1,
    }
    assert report["shader_family_use_counts"] == {
        "basicinstanced": 2,
        "foliageinstanced": 1,
        "skintestinstanced": 1,
    }


def test_all_unique_contexts_are_selection_ready():
    report = summarize_ranking_rows([
        {
            "shader_family": "crowdgeninstanced",
            "selection_status": "unique",
            "blocking_reasons": [],
        },
        {
            "shader_family": "crowdgeninstancedbillboard",
            "selection_status": "unique",
            "blocking_reasons": [],
        },
    ])

    assert report["status"] == "selection-ready"
    assert report["ready"] is True
    assert report["runtime_target_count"] == 0


def test_blocker_prevents_ready_even_for_unique_selection():
    report = summarize_ranking_rows([
        {
            "shader_family": "basicinstanced",
            "selection_status": "unique",
            "blocking_reasons": ["material-texture-binding:unresolved"],
        },
    ])

    assert report["ready"] is False
    assert report["status"] == "runtime-gated"
    assert report["unique_selection_count"] == 1
    assert report["runtime_target_count"] == 0
    assert report["blocking_reason_counts"] == {
        "material-texture-binding:unresolved": 1,
    }


def test_candidate_identity_prefers_permutation_then_pair_then_pixel():
    assert _candidate_identity({
        "permutation_identity": {"identity_sha256": "perm"},
        "pair_sha256": "pair",
        "pixel_sha256": "pixel",
    }) == "perm"
    assert _candidate_identity({
        "pair_sha256": "pair",
        "pixel_sha256": "pixel",
    }) == "pair"
    assert _candidate_identity({"pixel_sha256": "pixel"}) == "pixel"
    assert _candidate_identity({}) is None


def test_compact_candidate_retains_only_ranking_provenance():
    row = _compact_candidate({
        "file": "cache/foo.fxo",
        "program_offset": 128,
        "payload_sha256": "payload",
        "pixel_sha256": "pixel",
        "vertex_sha256": "vertex",
        "pair_sha256": "pair",
        "permutation_identity": {"identity_sha256": "perm", "extra": "drop"},
        "exact": True,
        "score": 2,
        "expected_count": 2,
        "vertex_pair_valid": True,
        "vertex_pair_score": 3.0,
        "vertex_pair_selection_status": "unique",
        "uniform_coverage": 1.0,
        "specialization_score": 4.0,
        "specialization_contradicted": [],
        "specialization_unexpected": ["X"],
        "samplers": [{"name": "drop-me"}],
    })

    assert row["file"] == "cache/foo.fxo"
    assert row["permutation_identity_sha256"] == "perm"
    assert row["pair_sha256"] == "pair"
    assert row["exact"] is True
    assert row["specialization_unexpected"] == ["X"]
    assert "samplers" not in row
