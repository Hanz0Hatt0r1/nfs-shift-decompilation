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

    def fake_create(source, initializer_links, ghidra_export):
        payload = json.loads(initializer_links.read_text(encoding="utf-8"))
        assert payload["link_count"] == 42
        assert ghidra_export == tmp_path / "ghidra"
        return {
            "format": "SHIFT-CLASS-CREATE-WRAPPER-EVIDENCE/1",
            "source": str(source),
            "link_count": 42,
            "source_create_wrapper_shape_count": 28,
            "create_wrapper_shape_count": 26,
            "distinct_preinitializer_helper_count": 7,
            "helpers": [],
            "links": [],
        }

    monkeypatch.setattr(module, "extract_create_wrappers", fake_create)

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
            "source_sha256": "source-sha",
            "exe_sha256": "exe-sha",
            "tier_counts": {
                "lifecycle-investigation-ready": 18,
                "registration-crosschecked": 100,
            },
            "next_evidence_blocker_counts": {"no_initializer_link": 100},
            "rows": [],
        }

    monkeypatch.setattr(module, "build_scorecard", fake_scorecard)

    def fake_source_lifecycle(source, manifest_path, scorecard_path, ghidra_export):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
        assert manifest["class_count"] == 315
        assert scorecard["tier_counts"]["lifecycle-investigation-ready"] == 18
        assert ghidra_export == tmp_path / "ghidra"
        return {
            "format": "SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1",
            "source": str(source),
            "source_sha256": "source-sha",
            "target_count": 18,
            "complete_target_count": 16,
            "base_initializer_link_count": 11,
            "teardown_transition_candidate_count": 9,
            "targets": [],
        }

    monkeypatch.setattr(module, "extract_lifecycle_evidence", fake_source_lifecycle)

    def fake_deleting(source, lifecycle_path, ghidra_export):
        lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))
        assert lifecycle["target_count"] == 18
        assert ghidra_export == tmp_path / "ghidra"
        return {
            "format": "SHIFT-CLASS-DELETING-WRAPPER-EVIDENCE/1",
            "source": str(source),
            "source_sha256": "source-sha",
            "wrapper_candidate_count": 8,
            "deleting_wrapper_shape_count": 6,
            "ghidra_confirmed_shape_count": 5,
            "wrappers": [],
        }

    monkeypatch.setattr(module, "extract_deleting_wrappers", fake_deleting)

    def fake_pairs(create_path, deleting_path, lifecycle_path):
        create = json.loads(create_path.read_text(encoding="utf-8"))
        deleting = json.loads(deleting_path.read_text(encoding="utf-8"))
        lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))
        assert create["create_wrapper_shape_count"] == 26
        assert deleting["deleting_wrapper_shape_count"] == 6
        assert lifecycle["target_count"] == 18
        return {
            "format": "SHIFT-CLASS-LIFETIME-PAIR-EVIDENCE/1",
            "paired_lifetime_shape_count": 5,
            "ghidra_paired_lifetime_shape_count": 4,
            "unambiguous_helper_pair_count": 3,
            "classes": [],
        }

    monkeypatch.setattr(module, "build_lifetime_pairs", fake_pairs)

    def fake_helper_families(pair_path, ghidra_export):
        pair = json.loads(pair_path.read_text(encoding="utf-8"))
        assert pair["paired_lifetime_shape_count"] == 5
        assert ghidra_export == tmp_path / "ghidra"
        return {
            "format": "SHIFT-CLASS-LIFETIME-HELPER-FAMILIES/1",
            "helper_family_count": 3,
            "recurrent_helper_pair_count": 2,
            "crosschecked_recurrent_helper_family_candidate_count": 1,
            "families": [],
        }

    monkeypatch.setattr(
        module,
        "_build_lifetime_helper_families",
        fake_helper_families,
    )

    def fake_memory_semantics(families_path, ghidra_export):
        families = json.loads(families_path.read_text(encoding="utf-8"))
        assert families["helper_family_count"] == 3
        assert ghidra_export == tmp_path / "ghidra"
        return {
            "format": "SHIFT-MEMORY-HELPER-SEMANTICS/1",
            "family_count": 3,
            "allocation_path_family_count": 2,
            "free_path_family_count": 1,
            "diagnostic_backed_pool_lifetime_family_count": 1,
            "families": [],
        }

    monkeypatch.setattr(
        module,
        "_build_memory_helper_semantics",
        fake_memory_semantics,
    )

    def fake_lifecycle(scorecard_path, ghidra_export):
        payload = json.loads(scorecard_path.read_text(encoding="utf-8"))
        assert payload["tier_counts"]["lifecycle-investigation-ready"] == 18
        assert ghidra_export == tmp_path / "ghidra"
        return {
            "format": "SHIFT.LifecycleInvestigationTargets/1",
            "target_count": 18,
            "complete_slice_count": 17,
            "incomplete_slice_count": 1,
            "targets": [],
        }

    monkeypatch.setattr(module, "_build_lifecycle_targets", fake_lifecycle)

    out = tmp_path / "out"
    report = module.run_pipeline(
        tmp_path / "SHIFT.exe.c",
        tmp_path / "SHIFT.exe",
        tmp_path / "ghidra",
        out,
    )

    assert report["format"] == "SHIFT-CLASS-EVIDENCE-PIPELINE/1"
    assert report["counts"]["registered_classes"] == 315
    assert report["counts"]["factory_initializer_links"] == 42
    assert report["counts"]["create_wrapper_links"] == 42
    assert report["counts"]["source_create_wrapper_shapes"] == 28
    assert report["counts"]["create_wrapper_shapes"] == 26
    assert report["counts"]["distinct_preinitializer_helpers"] == 7
    assert report["counts"]["structural_ready_classes"] == 227
    assert report["counts"]["lifecycle_investigation_ready_classes"] == 18
    assert report["counts"]["lifecycle_source_targets"] == 18
    assert report["counts"]["lifecycle_source_complete_targets"] == 16
    assert report["counts"]["lifecycle_source_base_initializer_links"] == 11
    assert report["counts"]["lifecycle_source_teardown_candidates"] == 9
    assert report["counts"]["deleting_wrapper_candidates"] == 8
    assert report["counts"]["deleting_wrapper_shapes"] == 6
    assert report["counts"]["deleting_wrapper_ghidra_confirmed_shapes"] == 5
    assert report["counts"]["paired_lifetime_classes"] == 5
    assert report["counts"]["ghidra_paired_lifetime_classes"] == 4
    assert report["counts"]["unambiguous_lifetime_helper_pairs"] == 3
    assert report["counts"]["lifetime_helper_families"] == 3
    assert report["counts"]["recurrent_lifetime_helper_pairs"] == 2
    assert report["counts"]["crosschecked_recurrent_helper_family_candidates"] == 1
    assert report["counts"]["pool_allocation_path_families"] == 2
    assert report["counts"]["pool_free_path_families"] == 1
    assert report["counts"]["diagnostic_backed_pool_lifetime_families"] == 1
    assert report["counts"]["lifecycle_target_slices"] == 18
    assert report["counts"]["lifecycle_complete_slices"] == 17
    assert report["counts"]["lifecycle_incomplete_slices"] == 1
    assert report["counts"]["ghidra_registration_mismatches"] == 1
    assert report["counts"]["initializer_ghidra_mismatch_links"] == 2

    expected = {
        "class_manifest.json",
        "factory_initializer_links.json",
        "create_wrapper_evidence.json",
        "class_audit.json",
        "class_evidence_scorecard.json",
        "class_lifecycle_source_evidence.json",
        "deleting_wrapper_evidence.json",
        "class_lifetime_pair_evidence.json",
        "lifetime_helper_families.json",
        "memory_helper_semantics.json",
        "lifecycle_investigation_targets.json",
        "pipeline_manifest.json",
    }
    assert {path.name for path in out.iterdir()} == expected

    saved = json.loads((out / "pipeline_manifest.json").read_text(encoding="utf-8"))
    assert saved["counts"] == report["counts"]
    assert saved["scope"]["pool_memory_path_diagnostics_used"] is True
    assert saved["scope"]["allocation_helper_semantics_proven"] is False
    assert saved["scope"]["shared_allocator_family_proven"] is False
    assert saved["scope"]["allocator_abi_proven"] is False
    assert saved["scope"]["constructor_semantics_proven"] is False
    assert saved["scope"]["destructor_semantics_proven"] is False
    assert saved["scope"]["deleting_destructor_semantics_proven"] is False
    assert saved["scope"]["ownership_semantics_proven"] is False
