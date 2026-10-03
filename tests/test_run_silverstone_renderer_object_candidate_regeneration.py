import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_silverstone_renderer_object_candidate_regeneration as regen


def _write(path: Path, value) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _capture(tmp_path: Path, *, ready=True):
    return _write(
        tmp_path / "capture.json",
        {
            "format": "SHIFT.IMBRuntimeCapturePipeline/1",
            "pipeline_ready": ready,
            "resource_results": [],
            "blocking_reasons": [] if ready else ["fixture-capture-blocker"],
        },
    )


def _scene_ir_report(ready=True):
    return {
        "format": "SHIFT.OfflineSceneIRMaterialization/1",
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": [] if ready else ["fixture-ir-blocker"],
        "archive_count": 1,
        "manifest_resource_count": 1,
        "manifest_error_count": 0 if ready else 1,
    }


def _occ(sha: str, *, path="tracks/test/scene.sgb", archive="track.bff"):
    return {
        "status": "extracted",
        "archive_ordinal": 0,
        "archive": archive,
        "source": "corpus.zip",
        "source_member": archive,
        "entry_index": 7,
        "path": path,
        "error": None,
        "payload": b"fixture-sgb",
        "sha256": sha,
    }


def _runtime():
    return {"format": "SHIFT.SGBRuntime/1", "ready": True, "chunks": []}


def _placement_join():
    return {
        "format": "SHIFT.SGBPlacementJoin/1",
        "ready": True,
        "blocking_reasons": [],
    }


def _placement():
    return {
        "format": "SHIFT.SGBScenePlacement/1",
        "ready": True,
        "placements": [],
    }


def _handoffs(*, ready=False, enriched=False):
    return {
        "format": "SHIFT.SGBObjectRenderHandoffSet/1",
        "ready": ready,
        "blocking_reasons": [] if ready else ["fixture-matrix-context-missing"],
        "objects": [],
        "enriched": enriched,
    }


def _join(tag="initial", *, ready=True, identity_complete=False):
    return {
        "format": "SHIFT.SGBRuntimeObjectCandidateJoin/1",
        "status": "unique-candidates" if identity_complete else "ambiguous",
        "ready": ready,
        "identity_complete": identity_complete,
        "blocking_reasons": [] if ready else ["fixture-join-blocker"],
        "runtime_resource_count": 2,
        "matched_runtime_resource_count": 2 if ready else 0,
        "unique_candidate_resource_count": 2 if identity_complete else 0,
        "resources": [],
        "tag": tag,
    }


def _root(*, ready=False):
    return {
        "format": "SHIFT.SGBMultiMatrixRootConsensus/1",
        "status": "ready" if ready else "not-found",
        "ready": ready,
        "blocking_reasons": [],
        "consensus": [],
    }


def _prepare(monkeypatch, tmp_path: Path, occurrences, *, root_ready=False):
    calls = {"handoffs": [], "join": [], "root": []}

    def build_ir(inputs, output_dir):
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        (root / "manifest.json").write_text(
            json.dumps([
                {
                    "archive": "track.bff",
                    "path": "tracks/test/a.imb",
                    "sha256": "a" * 64,
                }
            ]),
            encoding="utf-8",
        )
        return _scene_ir_report(True)

    monkeypatch.setattr(regen, "build_scene_ir", build_ir)
    monkeypatch.setattr(regen, "_discover_sgb_occurrences", lambda inputs: occurrences)
    monkeypatch.setattr(regen, "parse_sgb_runtime", lambda payload, strict=False: _runtime())
    monkeypatch.setattr(regen, "build_sgb_placement_join", lambda runtime: _placement_join())
    monkeypatch.setattr(regen, "build_sgb_scene_placement", lambda join: _placement())

    def handoff(runtime, *, root_consensus=None):
        calls["handoffs"].append(root_consensus)
        return _handoffs(ready=root_consensus is not None, enriched=root_consensus is not None)

    def object_join(scene, handoffs, capture, manifest):
        calls["join"].append(handoffs)
        return _join(
            "enriched" if handoffs.get("enriched") else "initial",
            ready=True,
            identity_complete=handoffs.get("enriched") is True,
        )

    def root(runtime, join, capture):
        calls["root"].append(join)
        return _root(ready=root_ready)

    monkeypatch.setattr(regen, "build_sgb_object_render_handoff_set", handoff)
    monkeypatch.setattr(regen, "build_runtime_object_candidate_join", object_join)
    monkeypatch.setattr(regen, "build_multimatrix_root_consensus", root)
    return calls


def test_unique_ready_sgb_is_selected_without_requiring_root_consensus(monkeypatch, tmp_path):
    capture = _capture(tmp_path)
    occurrence = _occ("1" * 64)
    calls = _prepare(monkeypatch, tmp_path, [occurrence], root_ready=False)

    report = regen.regenerate_runtime_object_candidates(
        corpus=[tmp_path / "corpus.zip"],
        capture_pipeline=capture,
        output_dir=tmp_path / "out",
    )

    assert report["format"] == regen.FORMAT
    assert report["status"] == "completed"
    assert report["ready"] is True
    assert report["summary"]["ready_distinct_sgb_identity_count"] == 1
    assert report["selected_scene"]["sgb_sha256"] == "1" * 64
    assert report["selected_scene"]["root_consensus_ready"] is False
    assert report["selected_scene"]["transform_enriched"] is False
    assert report["selected_scene"]["identity_complete"] is False
    assert len(calls["handoffs"]) == 1
    assert len(calls["join"]) == 1
    assert len(calls["root"]) == 1
    selected = json.loads(
        Path(report["outputs"]["object_candidate_join"]).read_text(encoding="utf-8")
    )
    assert selected["tag"] == "initial"
    assert report["boundary"]["root_consensus_is_required_for_initial_object_join"] is False
    assert report["boundary"]["new_capture_required"] is False


def test_ready_root_consensus_rebuilds_handoffs_and_enriches_final_join(monkeypatch, tmp_path):
    capture = _capture(tmp_path)
    occurrence = _occ("2" * 64)
    calls = _prepare(monkeypatch, tmp_path, [occurrence], root_ready=True)

    report = regen.regenerate_runtime_object_candidates(
        corpus=[tmp_path / "corpus.zip"],
        capture_pipeline=capture,
        output_dir=tmp_path / "out",
    )

    assert report["status"] == "completed"
    assert report["selected_scene"]["root_consensus_ready"] is True
    assert report["selected_scene"]["transform_enriched"] is True
    assert report["selected_scene"]["identity_complete"] is True
    assert len(calls["handoffs"]) == 2
    assert len(calls["join"]) == 2
    selected = json.loads(
        Path(report["outputs"]["object_candidate_join"]).read_text(encoding="utf-8")
    )
    assert selected["tag"] == "enriched"
    assert Path(report["outputs"]["root_consensus"]).is_file()


def test_exact_duplicate_sgb_occurrences_collapse_by_payload_and_join_identity(monkeypatch, tmp_path):
    capture = _capture(tmp_path)
    occurrences = [
        _occ("3" * 64, archive="a.bff"),
        _occ("3" * 64, archive="copy.bff"),
    ]
    _prepare(monkeypatch, tmp_path, occurrences, root_ready=False)

    report = regen.regenerate_runtime_object_candidates(
        corpus=[tmp_path / "corpus.zip"],
        capture_pipeline=capture,
        output_dir=tmp_path / "out",
    )

    assert report["status"] == "completed"
    assert report["summary"]["ready_sgb_occurrence_count"] == 2
    assert report["summary"]["ready_distinct_sgb_identity_count"] == 1
    assert report["selected_scene"]["duplicate_occurrence_count"] == 2
    assert len(report["selected_scene"]["occurrences"]) == 2
    assert report["boundary"]["exact_duplicate_sgb_occurrences_may_collapse"] is True


def test_different_ready_sgb_payloads_remain_ambiguous_even_if_join_payload_matches(monkeypatch, tmp_path):
    capture = _capture(tmp_path)
    occurrences = [
        _occ("4" * 64, path="tracks/test/a.sgb"),
        _occ("5" * 64, path="tracks/test/b.sgb"),
    ]
    _prepare(monkeypatch, tmp_path, occurrences, root_ready=False)

    report = regen.regenerate_runtime_object_candidates(
        corpus=[tmp_path / "corpus.zip"],
        capture_pipeline=capture,
        output_dir=tmp_path / "out",
    )

    assert report["status"] == "blocked"
    assert report["ready"] is False
    assert report["summary"]["ready_distinct_sgb_identity_count"] == 2
    assert report["selected_scene"] is None
    assert "scene_selection:multiple-ready-distinct-sgb-identities:2" in report["blocking_reasons"]
    assert report["boundary"]["different_sgb_payloads_with_same_logical_paths_may_collapse"] is False


def test_capture_pipeline_must_be_ready_before_scene_ir_or_sgb_scan(monkeypatch, tmp_path):
    capture = _capture(tmp_path, ready=False)
    ir_called = False
    scan_called = False

    def forbidden_ir(*args, **kwargs):
        nonlocal ir_called
        ir_called = True
        raise AssertionError("scene IR must not run")

    def forbidden_scan(*args, **kwargs):
        nonlocal scan_called
        scan_called = True
        raise AssertionError("SGB scan must not run")

    monkeypatch.setattr(regen, "build_scene_ir", forbidden_ir)
    monkeypatch.setattr(regen, "_discover_sgb_occurrences", forbidden_scan)

    report = regen.regenerate_runtime_object_candidates(
        corpus=[],
        capture_pipeline=capture,
        output_dir=tmp_path / "out",
    )

    assert report["status"] == "blocked"
    assert ir_called is False
    assert scan_called is False
    assert "capture_pipeline:not-ready" in report["blocking_reasons"]


def test_blocked_scene_ir_stops_before_sgb_selection(monkeypatch, tmp_path):
    capture = _capture(tmp_path)
    scan_called = False

    monkeypatch.setattr(regen, "build_scene_ir", lambda inputs, output_dir: _scene_ir_report(False))

    def forbidden_scan(*args, **kwargs):
        nonlocal scan_called
        scan_called = True
        raise AssertionError("SGB scan must not run when IR is blocked")

    monkeypatch.setattr(regen, "_discover_sgb_occurrences", forbidden_scan)

    report = regen.regenerate_runtime_object_candidates(
        corpus=[tmp_path / "corpus.zip"],
        capture_pipeline=capture,
        output_dir=tmp_path / "out",
    )

    assert report["status"] == "blocked"
    assert scan_called is False
    assert "scene_ir:fixture-ir-blocker" in report["blocking_reasons"]
