import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_silverstone_renderer_shader_target_regeneration as regen


def _write(path: Path, value: dict | str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, dict):
        path.write_text(json.dumps(value), encoding="utf-8")
    else:
        path.write_text(value, encoding="utf-8")
    return path


def _ranking():
    return {
        "format": "SHIFT.IMBMaterialShaderRanking/1",
        "status": "runtime-gated",
        "ready": False,
        "primitive_binding_count": 2,
        "runtime_target_count": 2,
        "unique_rank_context_count": 2,
        "selection_status_counts": {"ambiguous": 2},
        "rows": [
            {
                "archive": "track.bff",
                "imb_path": "track/a.imb",
                "imb_sha256": "a" * 64,
                "draw_range": {
                    "first_index": 0,
                    "index_count": 3,
                    "primitive_count": 1,
                },
                "primitive_index": 0,
                "selection_status": "ambiguous",
                "top_rank_candidate_count": 1,
                "top_rank_candidates": [],
            },
            {
                "archive": "track.bff",
                "imb_path": "track/b.imb",
                "imb_sha256": "b" * 64,
                "draw_range": {
                    "first_index": 3,
                    "index_count": 3,
                    "primitive_count": 1,
                },
                "primitive_index": 0,
                "selection_status": "ambiguous",
                "top_rank_candidate_count": 1,
                "top_rank_candidates": [],
            },
        ],
    }


def _target_set(*, capture_ready=True):
    pixel_a = "1" * 64
    pixel_b = "2" * 64
    bindings = [
        {
            "binding_index": 0,
            "capture_ready": capture_ready,
            "attribution_ready": False,
            "hash_target_count": 1,
        },
        {
            "binding_index": 1,
            "capture_ready": capture_ready,
            "attribution_ready": False,
            "hash_target_count": 1,
        },
    ]
    return {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "status": "capture-ready" if capture_ready else "blocked",
        "capture_ready": capture_ready,
        "attribution_ready": False,
        "binding_target_count": 2,
        "unique_hash_target_count": 2,
        "strong_hash_target_count": 0,
        "prefilter_only_target_count": 2,
        "binding_targets": bindings,
        "unique_targets": [
            {
                "identity_kind": "pixel",
                "identity_value": pixel_a,
                "strength": "prefilter-only",
                "pixel_byte_sha256": pixel_a,
                "shader_families": ["familya"],
            },
            {
                "identity_kind": "pixel",
                "identity_value": pixel_b,
                "strength": "prefilter-only",
                "pixel_byte_sha256": pixel_b,
                "shader_families": ["familyb"],
            },
        ],
        "blocking_reasons": [] if capture_ready else ["fixture-blocker"],
    }


def _compact_from_projection(projection: dict):
    return {
        "format": "SHIFT.IMBRuntimeShaderTargetSetEvidence/1",
        "verification_scope": "fixture",
        "source_ranking": projection["source_ranking"],
        "result": projection["result"],
        "families": projection["families"],
        "boundary": projection["boundary"],
    }


def _install(monkeypatch, *, ranking=None, target=None):
    ranking = _ranking() if ranking is None else ranking
    target = _target_set() if target is None else target
    calls = {"ranking": [], "target": []}

    def ranking_call(inputs, *, max_imb_per_archive=0):
        calls["ranking"].append((list(inputs), max_imb_per_archive))
        return ranking

    def target_call(value):
        calls["target"].append(value)
        return target

    monkeypatch.setattr(regen, "audit_imb_material_shader_ranking", ranking_call)
    monkeypatch.setattr(regen, "build_imb_runtime_shader_target_set", target_call)
    return calls, ranking, target


def test_regenerates_full_target_set_without_requiring_unique_static_selection(
    monkeypatch,
    tmp_path,
):
    corpus = _write(tmp_path / "corpus.zip", "fixture")
    calls, ranking, target = _install(monkeypatch)

    manifest = regen.regenerate_full_shader_target_set(
        corpus=[corpus],
        output_dir=tmp_path / "out",
    )

    assert manifest["format"] == regen.FORMAT
    assert manifest["status"] == "completed"
    assert manifest["ready"] is True
    assert manifest["summary"]["target_set_capture_ready"] is True
    assert manifest["summary"]["binding_target_count"] == 2
    assert len(calls["ranking"]) == 1
    assert calls["target"] == [ranking]
    assert json.loads(
        Path(manifest["outputs"]["runtime_shader_targets"]).read_text(encoding="utf-8")
    ) == target
    projection = json.loads(
        Path(manifest["outputs"]["compact_projection"]).read_text(encoding="utf-8")
    )
    assert projection["source_ranking"]["selection_status_counts"] == {"ambiguous": 2}
    assert projection["result"]["target_kind_counts"] == {"pixel": 2}
    assert projection["families"] == [
        {
            "family": "familya",
            "pixel_shader_sha256": ["1" * 64],
            "pixel_target_count": 1,
        },
        {
            "family": "familyb",
            "pixel_shader_sha256": ["2" * 64],
            "pixel_target_count": 1,
        },
    ]
    assert manifest["boundary"]["ranking_preserves_tied_top_candidates"] is True
    assert manifest["boundary"]["compact_phase568_evidence_is_reconstruction_source"] is False
    assert manifest["boundary"]["new_capture_required"] is False


def test_exact_compact_projection_match_is_crosscheck_only(monkeypatch, tmp_path):
    corpus = _write(tmp_path / "corpus.zip", "fixture")
    _calls, ranking, target = _install(monkeypatch)
    projection = regen._compact_projection_from_full(ranking, target)
    compact = _write(
        tmp_path / "compact.json",
        _compact_from_projection(projection),
    )

    manifest = regen.regenerate_full_shader_target_set(
        corpus=[corpus],
        compact_evidence=compact,
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "completed"
    assert manifest["summary"]["compact_crosscheck_requested"] is True
    assert manifest["summary"]["compact_crosscheck_match"] is True
    record = manifest["inputs"]["compact_evidence"]
    assert record["projection_status"] == "exact-semantic-projection-match"
    assert record["expected_projection_sha256"] == record["regenerated_projection_sha256"]


def test_compact_projection_mismatch_blocks_but_does_not_replace_full_target(
    monkeypatch,
    tmp_path,
):
    corpus = _write(tmp_path / "corpus.zip", "fixture")
    _calls, ranking, target = _install(monkeypatch)
    projection = regen._compact_projection_from_full(ranking, target)
    compact_value = _compact_from_projection(projection)
    compact_value["result"] = dict(compact_value["result"])
    compact_value["result"]["unique_hash_target_count"] = 999
    compact = _write(tmp_path / "compact.json", compact_value)

    manifest = regen.regenerate_full_shader_target_set(
        corpus=[corpus],
        compact_evidence=compact,
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "blocked"
    assert manifest["ready"] is False
    assert "compact_evidence:semantic-projection-mismatch" in manifest["blocking_reasons"]
    assert Path(manifest["outputs"]["runtime_shader_targets"]).is_file()
    assert json.loads(
        Path(manifest["outputs"]["runtime_shader_targets"]).read_text(encoding="utf-8")
    ) == target
    assert manifest["inputs"]["compact_evidence"]["projection_status"] == "semantic-projection-mismatch"


def test_non_capture_ready_target_set_blocks(monkeypatch, tmp_path):
    corpus = _write(tmp_path / "corpus.zip", "fixture")
    _install(monkeypatch, target=_target_set(capture_ready=False))

    manifest = regen.regenerate_full_shader_target_set(
        corpus=[corpus],
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "blocked"
    assert manifest["summary"]["target_set_available"] is True
    assert manifest["summary"]["target_set_capture_ready"] is False
    assert "target_set:not-capture-ready" in manifest["blocking_reasons"]


def test_missing_corpus_blocks_before_ranking(monkeypatch, tmp_path):
    called = False

    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("ranking must not run")

    monkeypatch.setattr(regen, "audit_imb_material_shader_ranking", forbidden)

    manifest = regen.regenerate_full_shader_target_set(
        corpus=[tmp_path / "missing.zip"],
        output_dir=tmp_path / "out",
    )

    assert called is False
    assert manifest["status"] == "blocked"
    assert any("file-not-found" in reason for reason in manifest["blocking_reasons"])
    assert manifest["outputs"]["runtime_shader_targets"] is None


def test_wrong_compact_format_fails_closed(monkeypatch, tmp_path):
    corpus = _write(tmp_path / "corpus.zip", "fixture")
    _install(monkeypatch)
    compact = _write(tmp_path / "compact.json", {"format": "wrong"})

    manifest = regen.regenerate_full_shader_target_set(
        corpus=[corpus],
        compact_evidence=compact,
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "blocked"
    assert any(
        reason.startswith("compact_evidence:failed:ValueError:")
        for reason in manifest["blocking_reasons"]
    )
    assert manifest["inputs"]["compact_evidence"]["projection_status"] == "unreadable-or-invalid"
