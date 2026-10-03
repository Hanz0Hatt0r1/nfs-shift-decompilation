from __future__ import annotations

import offline_bootstrap_corpus_validation as corpus


def _catalog():
    return {
        "format": "SHIFT.OfflineResourceCatalog/1",
        "archives": [
            {"id": "a-track", "archive_name": "Silverstone.bff"},
            {"id": "a-track-physics", "archive_name": "Silverstone_Physics.bff"},
            {"id": "a-orphan-physics", "archive_name": "Orphan_Physics.bff"},
            {"id": "a-car", "archive_name": "BMW_M3_E36.bff"},
            {"id": "a-not-car", "archive_name": "Misc.bff"},
        ],
        "resources": [
            {"archive_id": "a-car", "extension": ".cdf"},
            {"archive_id": "a-car", "extension": ".edf"},
            {"archive_id": "a-not-car", "extension": ".cdf"},
        ],
    }


def _graph():
    return {"format": "SHIFT.OfflineResourceDependencyGraph/1"}


def test_candidate_discovery_is_exact_and_narrow():
    catalog = _catalog()
    assert corpus.discover_track_candidates(catalog) == ["Silverstone"]
    assert corpus.discover_vehicle_candidates(catalog) == ["BMW_M3_E36"]


def test_validation_runs_existing_loaders_and_aggregates_blockers(monkeypatch):
    observed = []

    def fake_track(catalog, graph, *, track):
        observed.append(("track", track))
        return {
            "status": "ready",
            "ready": True,
            "blocking_reasons": [],
            "blocked_required_roots": [],
            "unresolved_dependencies": [],
            "selected_archives": {},
            "roots": {},
        }

    def fake_vehicle(catalog, graph, *, vehicle):
        observed.append(("vehicle", vehicle))
        return {
            "status": "blocked",
            "ready": False,
            "blocking_reasons": ["vehicle.vhf-missing", "dependency-missing:x->y"],
            "blocked_required_roots": [],
            "unresolved_dependencies": [{"ref": "y"}],
            "selected_archives": {},
            "roots": {},
        }

    monkeypatch.setattr(corpus, "load_track", fake_track)
    monkeypatch.setattr(corpus, "load_vehicle", fake_vehicle)

    report = corpus.build_bootstrap_corpus_validation(_catalog(), _graph())

    assert observed == [("track", "Silverstone"), ("vehicle", "BMW_M3_E36")]
    assert report["ready"] is False
    assert report["summary"]["targets"] == 2
    assert report["summary"]["ready"] == 1
    assert report["summary"]["blocked"] == 1
    assert report["summary"]["track"] == {"candidates": 1, "ready": 1, "blocked": 0}
    assert report["summary"]["vehicle"] == {"candidates": 1, "ready": 0, "blocked": 1}
    assert report["summary"]["blocking_reason_counts"] == {
        "dependency-missing:x->y": 1,
        "vehicle.vhf-missing": 1,
    }
    assert report["blocking_reasons"] == ["target-blocked:vehicle:BMW_M3_E36"]
    assert report["boundary"]["fuzzy_name_matching"] is False
    assert report["boundary"]["candidate_discovery_implies_readiness"] is False


def test_invalid_contracts_fail_before_target_discovery(monkeypatch):
    called = False

    def should_not_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("loaders must not run for invalid catalog/graph formats")

    monkeypatch.setattr(corpus, "load_track", should_not_run)
    monkeypatch.setattr(corpus, "load_vehicle", should_not_run)

    report = corpus.build_bootstrap_corpus_validation(
        {"format": "wrong", "archives": [], "resources": []},
        {"format": "wrong"},
    )

    assert called is False
    assert report["ready"] is False
    assert report["summary"]["targets"] == 0
    assert report["blocking_reasons"] == [
        "catalog:invalid-format",
        "dependency-graph:invalid-format",
    ]
