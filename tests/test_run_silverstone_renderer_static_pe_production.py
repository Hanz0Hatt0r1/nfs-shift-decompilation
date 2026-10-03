import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_silverstone_renderer_static_pe_production as static_pe


def _pe_report(*, usage_status="decoded", file_backed=True):
    return {
        "format": "SHIFT.PEImageEvidence/1",
        "image": {
            "bytes": 1234,
            "image_base": "0x00400000",
            "machine": "0x014c",
            "optional_header_magic": "0x010b",
            "pointer_size": 4,
            "section_count": 3,
        },
        "decoded_tables": {
            "usage": [
                {"ordinal": index, "value": index + 20}
                for index in range(9)
            ]
        },
        "conclusions": {
            "usage_table_status": usage_status,
            "file_backed_usage_table": file_backed,
        },
    }


def _hybrid(*, status="completed", blockers=None):
    blockers = [] if blockers is None else list(blockers)
    return {
        "format": "SHIFT.SilverstoneRendererHybridProductionRun/1",
        "status": status,
        "ready": status == "completed" and not blockers,
        "summary": {"production_completed": status == "completed"},
        "production": {
            "renderer_frontier": {
                "status": "continue-offline",
                "capture_blockers": [],
            }
        },
        "blocking_reasons": blockers,
    }


def _pe_file(tmp_path: Path) -> Path:
    path = tmp_path / "SHIFT.exe"
    path.write_bytes(b"MZ-static-fixture-bytes")
    return path


def test_static_pe_evidence_is_written_and_passed_to_hybrid(monkeypatch, tmp_path):
    pe_image = _pe_file(tmp_path)
    analyzed = []
    hybrid_calls = []

    def analyze(path):
        analyzed.append(Path(path))
        return _pe_report()

    def run_hybrid(**kwargs):
        hybrid_calls.append(kwargs)
        evidence = json.loads(Path(kwargs["pe_evidence"]).read_text(encoding="utf-8"))
        assert evidence["format"] == "SHIFT.PEImageEvidence/1"
        return _hybrid()

    monkeypatch.setattr(static_pe, "analyze_d3d9_pe_image_file", analyze)
    monkeypatch.setattr(static_pe, "run_hybrid_production", run_hybrid)

    out = tmp_path / "out"
    manifest = static_pe.run_static_pe_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_image=pe_image,
        output_dir=out,
        corpus=[tmp_path / "Silverstone.zip"],
        runtime_shader_targets=tmp_path / "targets.json",
        max_json_bytes=777,
    )

    assert analyzed == [pe_image]
    assert len(hybrid_calls) == 1
    call = hybrid_calls[0]
    assert call["bundles"] == [tmp_path / "out.zip"]
    assert call["capture_jsonl"] == tmp_path / "capture.jsonl"
    assert call["corpus"] == [tmp_path / "Silverstone.zip"]
    assert call["runtime_shader_targets"] == tmp_path / "targets.json"
    assert call["max_json_bytes"] == 777
    assert Path(call["pe_evidence"]).name == "shift_pe_image_evidence.json"
    assert manifest["status"] == "completed"
    assert manifest["ready"] is True
    assert manifest["summary"]["pe_evidence_generated"] is True
    assert manifest["summary"]["pe_usage_table_status"] == "decoded"
    assert manifest["pe_evidence"]["canonical_sha256"] == static_pe._canonical_sha(_pe_report())
    assert (out / "pe" / "shift_pe_image_evidence.json").is_file()
    assert (out / "silverstone_renderer_static_pe_production_run.json").is_file()
    assert manifest["boundary"]["pe_image_is_executed"] is False
    assert manifest["boundary"]["pe_image_is_loaded_as_program"] is False


def test_partial_usage_table_is_still_handed_to_phase631(monkeypatch, tmp_path):
    pe_image = _pe_file(tmp_path)
    hybrid_calls = []
    monkeypatch.setattr(
        static_pe,
        "analyze_d3d9_pe_image_file",
        lambda path: _pe_report(usage_status="partial", file_backed=False),
    )

    def run_hybrid(**kwargs):
        hybrid_calls.append(kwargs)
        return _hybrid(
            status="blocked",
            blockers=["raw:usage_map:usage-map:missing-ordinal:8"],
        )

    monkeypatch.setattr(static_pe, "run_hybrid_production", run_hybrid)
    manifest = static_pe.run_static_pe_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_image=pe_image,
        output_dir=tmp_path / "out",
        corpus=[],
    )

    assert len(hybrid_calls) == 1
    assert manifest["summary"]["pe_usage_table_status"] == "partial"
    assert manifest["summary"]["pe_usage_table_file_backed"] is False
    assert manifest["status"] == "blocked"
    assert "hybrid:raw:usage_map:usage-map:missing-ordinal:8" in manifest["blocking_reasons"]
    assert manifest["boundary"]["partial_usage_table_may_continue_to_phase630_for_fail_closed_reporting"] is True
    assert manifest["boundary"]["usage_values_are_inferred"] is False


def test_pe_parser_failure_blocks_without_starting_hybrid(monkeypatch, tmp_path):
    pe_image = _pe_file(tmp_path)
    hybrid_called = False

    def fail(path):
        raise ValueError("fixture PE parse failure")

    def forbidden(**kwargs):
        nonlocal hybrid_called
        hybrid_called = True
        raise AssertionError("hybrid production must not start")

    monkeypatch.setattr(static_pe, "analyze_d3d9_pe_image_file", fail)
    monkeypatch.setattr(static_pe, "run_hybrid_production", forbidden)
    manifest = static_pe.run_static_pe_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_image=pe_image,
        output_dir=tmp_path / "out",
        corpus=[],
    )

    assert hybrid_called is False
    assert manifest["status"] == "blocked"
    assert manifest["summary"]["pe_evidence_generated"] is False
    assert manifest["summary"]["hybrid_started"] is False
    assert "pe_evidence:ValueError:fixture PE parse failure" in manifest["blocking_reasons"]


def test_missing_pe_image_is_fail_closed(monkeypatch, tmp_path):
    analyze_called = False
    hybrid_called = False

    def analyze(path):
        nonlocal analyze_called
        analyze_called = True
        raise AssertionError("missing PE must not be parsed")

    def hybrid(**kwargs):
        nonlocal hybrid_called
        hybrid_called = True
        raise AssertionError("hybrid must not start")

    monkeypatch.setattr(static_pe, "analyze_d3d9_pe_image_file", analyze)
    monkeypatch.setattr(static_pe, "run_hybrid_production", hybrid)
    manifest = static_pe.run_static_pe_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_image=tmp_path / "missing.exe",
        output_dir=tmp_path / "out",
        corpus=[],
    )

    assert analyze_called is False
    assert hybrid_called is False
    assert manifest["status"] == "blocked"
    assert "pe_image:file-not-found" in manifest["blocking_reasons"]


def test_wrong_derived_pe_format_is_rejected(monkeypatch, tmp_path):
    pe_image = _pe_file(tmp_path)
    hybrid_called = False
    monkeypatch.setattr(
        static_pe,
        "analyze_d3d9_pe_image_file",
        lambda path: {"format": "wrong"},
    )

    def forbidden(**kwargs):
        nonlocal hybrid_called
        hybrid_called = True
        raise AssertionError("hybrid must not start")

    monkeypatch.setattr(static_pe, "run_hybrid_production", forbidden)
    manifest = static_pe.run_static_pe_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_image=pe_image,
        output_dir=tmp_path / "out",
        corpus=[],
    )

    assert hybrid_called is False
    assert manifest["status"] == "blocked"
    assert any(
        "PE evidence format mismatch" in reason
        for reason in manifest["blocking_reasons"]
    )
