from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from index_silverstone_renderer_report_bundle import index_report_bundles
from resolve_playable_renderer_pe_evidence import (
    resolve_renderer_pe_evidence_from_bundles,
)


def _pe(tag: str = "retail") -> dict:
    return {
        "format": "SHIFT.PEImageEvidence/1",
        "version": 1,
        "tag": tag,
        "image": {"sha256": tag * 8 if len(tag) == 8 else None},
    }


def _bundle(path: Path, entries: list[tuple[str, dict]]) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, value in entries:
            archive.writestr(name, json.dumps(value, sort_keys=True))
    return path


def _playable_module():
    path = TOOLS / "bootstrap_playable_linux_slice.py"
    spec = importlib.util.spec_from_file_location(
        "bootstrap_playable_linux_slice_phase654_tested",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bundle_index_recognizes_pe_evidence_by_embedded_format_not_filename(tmp_path):
    bundle = _bundle(
        tmp_path / "out.zip",
        [("totally/unrelated/name.json", _pe("retail-a"))],
    )
    report = index_report_bundles([bundle], output_dir=tmp_path / "indexed")
    row = next(row for row in report["reports"] if row["key"] == "pe_evidence")

    assert row["status"] == "exact-single-occurrence"
    assert row["occurrence_count"] == 1
    assert row["canonical_sha256"]
    assert report["normalized_outputs"]["pe_evidence"].endswith(
        "d3d9_pe_evidence.json"
    )
    assert report["boundary"]["filename_used_for_selection"] is False
    assert report["boundary"]["archive_order_used_for_selection"] is False


def test_bundle_pe_resolver_accepts_content_equivalent_duplicate_occurrences(tmp_path):
    value = _pe("retail-b")
    bundle = _bundle(
        tmp_path / "out.zip",
        [
            ("a.json", value),
            ("nested/b.json", value),
        ],
    )
    result = resolve_renderer_pe_evidence_from_bundles(
        [bundle],
        output_dir=tmp_path / "resolved",
    )

    assert result["ready"] is True
    assert result["resolution_status"] == "content-equivalent-multiple-occurrences"
    assert result["occurrence_count"] == 2
    assert Path(result["path"]).is_file()
    assert result["boundary"]["filename_used_for_selection"] is False
    assert result["boundary"]["frequency_used_for_selection"] is False


def test_bundle_pe_resolver_rejects_distinct_payloads_even_when_both_are_valid_format(tmp_path):
    bundle = _bundle(
        tmp_path / "out.zip",
        [
            ("first.json", _pe("retail-c")),
            ("second.json", _pe("retail-d")),
        ],
    )

    with pytest.raises(ValueError, match="ambiguous distinct PE evidence"):
        resolve_renderer_pe_evidence_from_bundles(
            [bundle],
            output_dir=tmp_path / "resolved",
        )

    indexed = json.loads(
        (tmp_path / "resolved" / "silverstone_renderer_report_bundle_index.json")
        .read_text(encoding="utf-8")
    )
    row = next(row for row in indexed["reports"] if row["key"] == "pe_evidence")
    assert row["status"] == "ambiguous-distinct-payloads"
    assert "pe_evidence" not in indexed["normalized_outputs"]
    assert not any(
        reason.startswith("report:pe_evidence:")
        for reason in indexed["blocking_reasons"]
    )


def test_playable_bootstrap_injects_exact_bundle_pe_before_lower_level_validation(
    monkeypatch,
    tmp_path,
):
    mod = _playable_module()
    calls: list[list[str]] = []

    monkeypatch.setattr(
        mod,
        "resolve_renderer_pe_evidence_from_bundles",
        lambda *args, **kwargs: {
            "ready": True,
            "path": str(tmp_path / "normalized-pe.json"),
            "bundle_index": str(tmp_path / "index.json"),
            "canonical_sha256": "1" * 64,
        },
    )

    class StopAfterBase(RuntimeError):
        pass

    def stop(argv):
        calls.append(list(argv))
        raise StopAfterBase

    monkeypatch.setattr(mod, "base_main", stop)

    with pytest.raises(StopAfterBase):
        mod.main([
            "Vehicles.zip",
            "Silverstone_Era3_.zip",
            "-o",
            str(tmp_path / "out"),
            "--track",
            "Silverstone_Era3_GrandPrix",
            "--vehicle",
            "BMW_M3_E36",
            "--workspace-root",
            str(tmp_path),
            "--renderer-capture-jsonl",
            "shift_d3d9_capture.jsonl",
            "--renderer-bundle",
            "out.zip",
            "--keyboard",
        ])

    assert len(calls) == 1
    argv = calls[0]
    index = argv.index("--renderer-pe-evidence")
    assert argv[index + 1] == str(tmp_path / "normalized-pe.json")


def test_playable_bootstrap_preserves_explicit_pe_selector(monkeypatch, tmp_path):
    mod = _playable_module()
    calls: list[list[str]] = []

    def must_not_resolve(*args, **kwargs):
        raise AssertionError("bundle PE resolution must not override explicit PE")

    monkeypatch.setattr(
        mod,
        "resolve_renderer_pe_evidence_from_bundles",
        must_not_resolve,
    )

    class StopAfterBase(RuntimeError):
        pass

    def stop(argv):
        calls.append(list(argv))
        raise StopAfterBase

    monkeypatch.setattr(mod, "base_main", stop)

    with pytest.raises(StopAfterBase):
        mod.main([
            "Vehicles.zip",
            "Silverstone_Era3_.zip",
            "-o",
            str(tmp_path / "out"),
            "--track",
            "Silverstone_Era3_GrandPrix",
            "--vehicle",
            "BMW_M3_E36",
            "--workspace-root",
            str(tmp_path),
            "--renderer-capture-jsonl",
            "shift_d3d9_capture.jsonl",
            "--renderer-bundle",
            "out.zip",
            "--renderer-pe-evidence",
            "explicit-pe.json",
            "--keyboard",
        ])

    assert calls
    argv = calls[0]
    assert argv.count("--renderer-pe-evidence") == 1
    index = argv.index("--renderer-pe-evidence")
    assert argv[index + 1] == "explicit-pe.json"
