import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = Path(__file__).resolve().parents[1] / "tools" / "shift_live_dump" / "build_class_evidence_scorecard.py"
    spec = importlib.util.spec_from_file_location("build_class_evidence_scorecard", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _audit_rows():
    return [
        {
            "class_name": "LifecycleReady",
            "descriptor": 0x1000,
            "parent_class": "Base",
            "field_count": 8,
            "unique_vtable": 0x2000,
            "structural_ready": True,
            "initializer_linked": True,
            "unambiguous_initializer": "FUN_00110000",
            "initializer_ghidra_confirmed": True,
        },
        {
            "class_name": "InitializerLinked",
            "descriptor": 0x1010,
            "parent_class": "Base",
            "field_count": 6,
            "unique_vtable": 0x2010,
            "structural_ready": True,
            "initializer_linked": True,
            "unambiguous_initializer": "FUN_00110100",
            "initializer_ghidra_confirmed": None,
        },
        {
            "class_name": "RegistrationOnly",
            "descriptor": 0x1020,
            "parent_class": "Base",
            "field_count": 4,
            "unique_vtable": 0x2020,
            "structural_ready": True,
            "initializer_linked": False,
            "unambiguous_initializer": None,
            "initializer_ghidra_confirmed": None,
        },
        {
            "class_name": "RegistrationMismatch",
            "descriptor": 0x1030,
            "parent_class": "Base",
            "field_count": 3,
            "unique_vtable": 0x2030,
            "structural_ready": True,
            "initializer_linked": False,
            "unambiguous_initializer": None,
            "initializer_ghidra_confirmed": None,
        },
        {
            "class_name": "Blocked",
            "descriptor": 0x1040,
            "parent_class": None,
            "field_count": 1,
            "unique_vtable": None,
            "structural_ready": False,
            "initializer_linked": False,
            "unambiguous_initializer": None,
            "initializer_ghidra_confirmed": None,
        },
    ]


def _write_inputs(tmp_path: Path, *, mismatched_sha: bool = False):
    audit = {
        "format": "SHIFT-CLASS-DECOMPILATION-CANDIDATES/1",
        "source": "SHIFT.exe.c",
        "source_sha256": "source-sha",
        "exe": "SHIFT.exe",
        "exe_sha256": "exe-sha",
        "candidates": _audit_rows(),
    }
    manifest_classes = []
    verified = {0x1000: True, 0x1010: True, 0x1020: True, 0x1030: False}
    for descriptor, state in verified.items():
        manifest_classes.append(
            {
                "descriptor": descriptor,
                "ghidra_registration": {
                    "address": f"0x{descriptor:08x}",
                    "mnemonic_sha256": f"fingerprint-{descriptor:x}",
                    "verified": state,
                },
            }
        )
    manifest = {
        "format": "SHIFT-CLASS-MANIFEST/1",
        "source_sha256": "other-source" if mismatched_sha else "source-sha",
        "exe_sha256": "exe-sha",
        "classes": manifest_classes,
    }
    audit_path = tmp_path / "audit.json"
    manifest_path = tmp_path / "manifest.json"
    audit_path.write_text(json.dumps(audit), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return audit_path, manifest_path


def test_scorecard_preserves_independent_evidence_tiers(tmp_path):
    module = _load_module()
    audit_path, manifest_path = _write_inputs(tmp_path)

    report = module.build_scorecard(audit_path, manifest_path)
    rows = {row["class_name"]: row for row in report["rows"]}

    assert rows["LifecycleReady"]["evidence_tier"] == "lifecycle-investigation-ready"
    assert rows["LifecycleReady"]["next_evidence_blockers"] == []
    assert rows["InitializerLinked"]["evidence_tier"] == "initializer-linked"
    assert rows["InitializerLinked"]["next_evidence_blockers"] == [
        "initializer_call_not_checked"
    ]
    assert rows["RegistrationOnly"]["evidence_tier"] == "registration-crosschecked"
    assert rows["RegistrationOnly"]["next_evidence_blockers"] == [
        "no_initializer_link"
    ]
    assert rows["RegistrationMismatch"]["evidence_tier"] == "structural-ready"
    assert "registration_mismatch" in rows["RegistrationMismatch"]["next_evidence_blockers"]
    assert rows["Blocked"]["evidence_tier"] == "structural-blocked"
    assert "structural_not_ready" in rows["Blocked"]["next_evidence_blockers"]

    assert report["registration_joined_count"] == 4
    assert report["registration_verified_count"] == 3
    assert report["registration_mismatch_count"] == 1
    assert report["tier_counts"]["lifecycle-investigation-ready"] == 1
    assert report["scope"]["numeric_confidence_score_used"] is False
    assert report["scope"]["constructor_semantics_proven"] is False


def test_scorecard_without_manifest_keeps_registration_unchecked(tmp_path):
    module = _load_module()
    audit_path, _ = _write_inputs(tmp_path)

    report = module.build_scorecard(audit_path)
    rows = {row["class_name"]: row for row in report["rows"]}

    assert report["registration_joined_count"] == 0
    assert rows["LifecycleReady"]["evidence_tier"] == "structural-ready"
    assert "registration_not_checked" in rows["LifecycleReady"]["next_evidence_blockers"]


def test_scorecard_rejects_mixed_source_identity(tmp_path):
    module = _load_module()
    audit_path, manifest_path = _write_inputs(tmp_path, mismatched_sha=True)

    with pytest.raises(ValueError, match="source_sha256 does not match audit"):
        module.build_scorecard(audit_path, manifest_path)
