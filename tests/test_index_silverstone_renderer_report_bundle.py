import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import index_silverstone_renderer_report_bundle as indexer


CORE = {
    "base.json": {"format": "SHIFT.D3D9RendererRequirementAudit/1", "requirements": []},
    "ambiguity.json": {"format": "SHIFT.IMBDrawLocalAmbiguityAudit/1", "ambiguous_draws": []},
    "draw.json": {"format": "SHIFT.D3D9TargetDrawLocalEvidence/1", "draws": []},
    "pipeline.json": {"format": "SHIFT.IMBRuntimeCapturePipeline/1", "pipeline_ready": True},
}


def _bundle(path: Path, entries, *, raw_entries=None):
    raw_entries = raw_entries or {}
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in entries.items():
            archive.writestr(name, json.dumps(value))
        for name, payload in raw_entries.items():
            archive.writestr(name, payload)
    return path


def _by_key(manifest):
    return {row["key"]: row for row in manifest["reports"]}


def test_unique_core_reports_are_materialized_by_embedded_format(tmp_path):
    bundle = _bundle(
        tmp_path / "out.zip",
        {
            **CORE,
            "nested/targets-whatever-name.json": {
                "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
                "binding_targets": [],
            },
            "nested/object.json": {
                "format": "SHIFT.SGBRuntimeObjectCandidateJoin/1",
                "ready": True,
            },
            "ignored.json": {"format": "SHIFT.Unrelated/1"},
        },
    )
    out = tmp_path / "normalized"
    manifest = indexer.index_report_bundles([bundle], output_dir=out)

    assert manifest["format"] == indexer.FORMAT
    assert manifest["status"] == "ready"
    assert manifest["ready"] is True
    assert manifest["blocking_reasons"] == []
    assert manifest["summary"]["resolved_report_count"] == 6
    assert manifest["summary"]["missing_required_report_count"] == 0
    rows = _by_key(manifest)
    assert rows["base_audit"]["status"] == "exact-single-occurrence"
    assert rows["runtime_shader_targets"]["status"] == "exact-single-occurrence"
    assert Path(manifest["normalized_outputs"]["base_audit"]).is_file()
    assert Path(manifest["normalized_outputs"]["capture_pipeline"]).is_file()
    assert manifest["production_runner_arguments"]["draw_local"] == manifest["normalized_outputs"]["draw_local"]
    assert (out / "silverstone_renderer_report_bundle_index.json").is_file()


def test_content_equivalent_duplicate_occurrences_retain_all_provenance(tmp_path):
    first = tmp_path / "a.zip"
    second = tmp_path / "b.zip"
    base = CORE["base.json"]
    _bundle(first, CORE)
    with zipfile.ZipFile(second, "w") as archive:
        archive.writestr("copy/base-pretty.json", json.dumps(base, indent=4, sort_keys=False))

    manifest = indexer.index_report_bundles([first, second], output_dir=tmp_path / "out")
    row = _by_key(manifest)["base_audit"]
    assert manifest["ready"] is True
    assert row["status"] == "content-equivalent-multiple-occurrences"
    assert row["occurrence_count"] == 2
    assert row["distinct_canonical_payload_count"] == 1
    assert len(row["occurrences"]) == 2
    assert row["occurrences"][0]["raw_sha256"] != row["occurrences"][1]["raw_sha256"]
    assert row["occurrences"][0]["canonical_sha256"] == row["occurrences"][1]["canonical_sha256"]


def test_distinct_payloads_for_same_format_are_ambiguous_not_selected(tmp_path):
    entries = dict(CORE)
    entries["second-base.json"] = {
        "format": "SHIFT.D3D9RendererRequirementAudit/1",
        "requirements": [{"requirement_id": "different"}],
    }
    bundle = _bundle(tmp_path / "out.zip", entries)
    out = tmp_path / "normalized"
    manifest = indexer.index_report_bundles([bundle], output_dir=out)
    row = _by_key(manifest)["base_audit"]

    assert manifest["status"] == "blocked"
    assert row["status"] == "ambiguous-distinct-payloads"
    assert row["distinct_canonical_payload_count"] == 2
    assert row["output"] is None
    assert "base_audit" not in manifest["normalized_outputs"]
    assert any("ambiguous-distinct-canonical-payloads:2" in reason for reason in manifest["blocking_reasons"])
    assert manifest["boundary"]["filename_used_for_selection"] is False
    assert manifest["boundary"]["archive_order_used_for_selection"] is False


def test_missing_optional_reports_do_not_block_core_handoff(tmp_path):
    bundle = _bundle(tmp_path / "out.zip", CORE)
    manifest = indexer.index_report_bundles([bundle], output_dir=tmp_path / "normalized")
    rows = _by_key(manifest)

    assert manifest["ready"] is True
    assert rows["object_candidate_join"]["status"] == "missing"
    assert rows["runtime_shader_targets"]["status"] == "missing"
    assert manifest["production_runner_arguments"]["object_candidate_join"] is None
    assert manifest["production_runner_arguments"]["runtime_shader_targets"] is None


def test_missing_required_report_is_explicit_blocker(tmp_path):
    entries = dict(CORE)
    entries.pop("pipeline.json")
    bundle = _bundle(tmp_path / "out.zip", entries)
    manifest = indexer.index_report_bundles([bundle], output_dir=tmp_path / "normalized")
    row = _by_key(manifest)["capture_pipeline"]

    assert manifest["ready"] is False
    assert row["status"] == "missing"
    assert manifest["summary"]["missing_required_report_count"] == 1
    assert "report:capture_pipeline:missing-from-bundles" in manifest["blocking_reasons"]


def test_large_json_entry_is_skipped_before_decode(tmp_path):
    entries = dict(CORE)
    entries.pop("draw.json")
    raw = json.dumps({"format": "SHIFT.D3D9TargetDrawLocalEvidence/1", "payload": "x" * 256})
    bundle = _bundle(tmp_path / "out.zip", entries, raw_entries={"huge.json": raw})
    manifest = indexer.index_report_bundles(
        [bundle],
        output_dir=tmp_path / "normalized",
        max_json_bytes=64,
    )

    assert manifest["ready"] is False
    assert manifest["summary"]["skipped_json_entry_count"] >= 1
    assert any(row["entry"] == "huge.json" and row["reason"] == "json-entry-too-large" for row in manifest["skipped_entries"])
    assert "report:draw_local:missing-from-bundles" in manifest["blocking_reasons"]


def test_invalid_zip_is_fail_closed_and_manifest_is_still_written(tmp_path):
    bundle = tmp_path / "bad.zip"
    bundle.write_bytes(b"not-a-zip")
    out = tmp_path / "normalized"
    manifest = indexer.index_report_bundles([bundle], output_dir=out)

    assert manifest["ready"] is False
    assert any("zip-open-failed" in reason for reason in manifest["blocking_reasons"])
    assert (out / "silverstone_renderer_report_bundle_index.json").is_file()
