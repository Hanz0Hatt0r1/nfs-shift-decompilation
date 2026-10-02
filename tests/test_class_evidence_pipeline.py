import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "shift_live_dump"
    sys.path.insert(0, str(tool_dir))
    try:
        path = tool_dir / "build_class_evidence_pipeline.py"
        spec = importlib.util.spec_from_file_location("build_class_evidence_pipeline", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def test_pipeline_writes_joined_artifacts(tmp_path, monkeypatch):
    module = _load_module()

    monkeypatch.setattr(
        module,
        "build_manifest",
        lambda source, exe, ghidra: {
            "format": "SHIFT-CLASS-MANIFEST/1",
            "source_sha256": "source-sha",
            "exe_sha256": "exe-sha",
            "class_count": 315,
            "reflected_class_count": 245,
            "unique_vtable_count": 267,
            "ghidra_registration_checked_count": 315,
            "ghidra_registration_verified_count": 314,
            "ghidra_registration_mismatch_count": 1,
            "classes": [],
        },
    )
    monkeypatch.setattr(
        module,
        "extract_links",
        lambda source, exe, ghidra: {
            "format": "SHIFT-FACTORY-INITIALIZER-LINKS/1",
            "link_count": 42,
            "linked_class_count": 30,
            "ghidra_confirmed_link_count": 40,
            "ghidra_mismatch_link_count": 2,
            "links": [],
        },
    )

    def fake_audit(source, exe, initializer_links):
        payload = json.loads(initializer_links.read_text(encoding="utf-8"))
        assert payload["link_count"] == 42
        return {
            "format": "SHIFT-CLASS-DECOMPILATION-CANDIDATES/1",
            "source_sha256": "source-sha",
            "exe_sha256": "exe-sha",
            "structural_ready_count": 227,
            "candidates": [],
        }

    monkeypatch.setattr(module, "audit_candidates", fake_audit)

    def fake_scorecard(audit_path, manifest_path):
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert audit["structural_ready_count"] == 227
        assert manifest["class_count"] == 315
        return {
            "format": "SHIFT-CLASS-EVIDENCE-SCORECARD/1",
            "tier_counts": {
                "lifecycle-investigation-ready": 18,
                "registration-crosschecked": 100,
            },
            "next_evidence_blocker_counts": {"no_initializer_link": 100},
            "rows": [],
        }

    monkeypatch.setattr(module, "build_scorecard", fake_scorecard)

    out = tmp_path / "out"
    report = module.run_pipeline(
        tmp_path / "SHIFT.exe.c",
        tmp_path / "SHIFT.exe",
        tmp_path / "ghidra",
        out,
    )

    assert report["format"] == "SHIFT-CLASS-EVIDENCE-PIPELINE/1"
    assert report["counts"]["registered_classes"] == 315
    assert report["counts"]["structural_ready_classes"] == 227
    assert report["counts"]["lifecycle_investigation_ready_classes"] == 18
    assert report["counts"]["ghidra_registration_mismatches"] == 1
    assert report["counts"]["initializer_ghidra_mismatch_links"] == 2

    expected = {
        "class_manifest.json",
        "factory_initializer_links.json",
        "class_audit.json",
        "class_evidence_scorecard.json",
        "pipeline_manifest.json",
    }
    assert {path.name for path in out.iterdir()} == expected

    saved = json.loads((out / "pipeline_manifest.json").read_text(encoding="utf-8"))
    assert saved["counts"] == report["counts"]
    assert saved["scope"]["constructor_semantics_proven"] is False
