import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_silverstone_renderer_source_bootstrap_production as sourceboot


def _write(path: Path, value: dict | str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, dict):
        path.write_text(json.dumps(value), encoding="utf-8")
    else:
        path.write_text(value, encoding="utf-8")
    return path


def _target():
    return {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "capture_ready": True,
        "binding_targets": [{"binding_index": 0, "capture_ready": True}],
    }


def _self_manifest():
    return {
        "format": "SHIFT.SilverstoneRendererSelfBootstrapProductionRun/1",
        "status": "completed",
        "ready": True,
        "summary": {"production_completed": True},
        "production": {
            "status": "completed",
            "renderer_frontier": {
                "status": "continue-offline",
                "capture_blockers": [],
            },
        },
        "blocking_reasons": [],
    }


def test_source_bootstrap_regenerates_targets_and_needs_no_user_bundle(monkeypatch, tmp_path):
    target_path = _write(tmp_path / "generated-targets.json", _target())
    calls = {"target": [], "self": []}

    def target_call(**kwargs):
        calls["target"].append(kwargs)
        return {
            "format": "SHIFT.SilverstoneRendererShaderTargetRegeneration/1",
            "status": "completed",
            "ready": True,
            "summary": {"target_set_capture_ready": True},
            "outputs": {"runtime_shader_targets": str(target_path)},
            "blocking_reasons": [],
        }

    def self_call(**kwargs):
        calls["self"].append(kwargs)
        return _self_manifest()

    monkeypatch.setattr(sourceboot, "regenerate_full_shader_target_set", target_call)
    monkeypatch.setattr(sourceboot, "run_self_bootstrap_production", self_call)

    manifest = sourceboot.run_source_bootstrap_production(
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_image=tmp_path / "SHIFT.exe",
        output_dir=tmp_path / "out",
        corpus=[tmp_path / "Silverstone.zip"],
        bundles=[],
    )

    assert manifest["format"] == sourceboot.FORMAT
    assert manifest["status"] == "completed"
    assert manifest["ready"] is True
    assert manifest["summary"]["shader_target_mode"] == "regenerated-from-corpus"
    assert manifest["summary"]["bundle_crosscheck_supplied"] is False
    assert len(calls["target"]) == 1
    assert calls["target"][0]["corpus"] == [tmp_path / "Silverstone.zip"]
    assert calls["target"][0]["compact_evidence"] == sourceboot.DEFAULT_COMPACT_EVIDENCE
    assert len(calls["self"]) == 1
    self_args = calls["self"][0]
    assert self_args["runtime_shader_targets"] == str(target_path)
    assert self_args["pe_image"] == tmp_path / "SHIFT.exe"
    assert self_args["pe_evidence"] is None
    assert len(self_args["bundles"]) == 1
    empty_bundle = Path(self_args["bundles"][0])
    assert empty_bundle.is_file()
    with zipfile.ZipFile(empty_bundle) as archive:
        assert archive.namelist() == []
    assert manifest["bundle_crosscheck"]["synthetic_empty_bundle"] is True
    assert manifest["bundle_crosscheck"]["synthetic_empty_bundle_contains_evidence"] is False
    assert manifest["boundary"]["manual_full_shader_target_handoff_required"] is False
    assert manifest["boundary"]["manual_renderer_report_bundle_required"] is False
    assert manifest["boundary"]["new_capture_required"] is False


def test_user_bundle_is_forwarded_without_synthetic_bundle(monkeypatch, tmp_path):
    target_path = _write(tmp_path / "target.json", _target())
    bundle = tmp_path / "out.zip"
    calls = []

    monkeypatch.setattr(
        sourceboot,
        "regenerate_full_shader_target_set",
        lambda **kwargs: {
            "format": "SHIFT.SilverstoneRendererShaderTargetRegeneration/1",
            "status": "completed",
            "ready": True,
            "summary": {},
            "outputs": {"runtime_shader_targets": str(target_path)},
            "blocking_reasons": [],
        },
    )

    def self_call(**kwargs):
        calls.append(kwargs)
        return _self_manifest()

    monkeypatch.setattr(sourceboot, "run_self_bootstrap_production", self_call)

    manifest = sourceboot.run_source_bootstrap_production(
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "out",
        corpus=[],
        bundles=[bundle],
        compact_crosscheck=False,
    )

    assert manifest["status"] == "completed"
    assert calls[0]["bundles"] == [bundle]
    assert manifest["bundle_crosscheck"]["user_supplied"] is True
    assert manifest["bundle_crosscheck"]["synthetic_empty_bundle"] is False


def test_explicit_prebuilt_full_target_skips_phase636(monkeypatch, tmp_path):
    target_path = _write(tmp_path / "target.json", _target())
    self_calls = []

    def forbidden_target(*args, **kwargs):
        raise AssertionError("Phase 636 must not run for explicit prebuilt target")

    monkeypatch.setattr(sourceboot, "regenerate_full_shader_target_set", forbidden_target)
    monkeypatch.setattr(
        sourceboot,
        "run_self_bootstrap_production",
        lambda **kwargs: self_calls.append(kwargs) or _self_manifest(),
    )

    manifest = sourceboot.run_source_bootstrap_production(
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "out",
        corpus=[],
        runtime_shader_targets=target_path,
    )

    assert manifest["status"] == "completed"
    assert manifest["summary"]["shader_target_mode"] == "explicit-prebuilt"
    assert manifest["shader_targets"]["path"] == str(target_path)
    assert self_calls[0]["runtime_shader_targets"] == str(target_path)


def test_compact_prebuilt_target_is_rejected_before_self_bootstrap(monkeypatch, tmp_path):
    compact = _write(
        tmp_path / "compact.json",
        {
            "format": "SHIFT.IMBRuntimeShaderTargetSetEvidence/1",
            "result": {},
        },
    )
    self_called = False

    def forbidden_self(*args, **kwargs):
        nonlocal self_called
        self_called = True
        raise AssertionError("self bootstrap must not run")

    monkeypatch.setattr(sourceboot, "run_self_bootstrap_production", forbidden_self)

    manifest = sourceboot.run_source_bootstrap_production(
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "out",
        corpus=[],
        runtime_shader_targets=compact,
    )

    assert manifest["status"] == "blocked"
    assert self_called is False
    assert any("format-mismatch" in reason for reason in manifest["blocking_reasons"])


def test_phase636_failure_blocks_before_phase635(monkeypatch, tmp_path):
    self_called = False

    monkeypatch.setattr(
        sourceboot,
        "regenerate_full_shader_target_set",
        lambda **kwargs: {
            "format": "SHIFT.SilverstoneRendererShaderTargetRegeneration/1",
            "status": "blocked",
            "ready": False,
            "summary": {},
            "outputs": {"runtime_shader_targets": None},
            "blocking_reasons": ["target_set:not-capture-ready"],
        },
    )

    def forbidden_self(*args, **kwargs):
        nonlocal self_called
        self_called = True
        raise AssertionError("Phase 635 must not run")

    monkeypatch.setattr(sourceboot, "run_self_bootstrap_production", forbidden_self)

    manifest = sourceboot.run_source_bootstrap_production(
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_image=tmp_path / "SHIFT.exe",
        output_dir=tmp_path / "out",
        corpus=[tmp_path / "corpus.zip"],
    )

    assert manifest["status"] == "blocked"
    assert self_called is False
    assert "shader_target_regeneration:target_set:not-capture-ready" in manifest["blocking_reasons"]
    assert "shader_target_regeneration:target-set-unavailable" in manifest["blocking_reasons"]


def test_exactly_one_pe_source_is_required(tmp_path):
    with pytest.raises(ValueError, match="exactly one"):
        sourceboot.run_source_bootstrap_production(
            capture_jsonl=tmp_path / "capture.jsonl",
            output_dir=tmp_path / "out-none",
            corpus=[],
        )

    with pytest.raises(ValueError, match="exactly one"):
        sourceboot.run_source_bootstrap_production(
            capture_jsonl=tmp_path / "capture.jsonl",
            pe_image=tmp_path / "SHIFT.exe",
            pe_evidence=tmp_path / "pe.json",
            output_dir=tmp_path / "out-both",
            corpus=[],
        )
