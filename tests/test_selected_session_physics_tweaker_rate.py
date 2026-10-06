from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/build_selected_session_physics_tweaker_rate.py"
SPEC = importlib.util.spec_from_file_location("build_selected_session_physics_tweaker_rate", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _snapshot(*, self_test: bool = False, loaded: int = 240, current: int = 240) -> dict:
    equal = current == loaded
    return {
        "format": MODULE.SNAPSHOT_FORMAT,
        "ready": True,
        "admission_eligible": True,
        "self_test": self_test,
        "retail_identity": {
            "pe_headers_match": True,
            "physics_tweaker_load_anchor_matches": True,
            "loaded_rate_apply_anchor_matches": True,
            "identity_ready": True,
            "cryptographic_hash_recomputed_at_runtime": False,
            "pinned_pe_sha256": MODULE.RETAIL_EXE_SHA256,
        },
        "anchors": dict(MODULE.EXPECTED_ANCHORS),
        "selected_session": {
            "loaded_tick_rate_hz": loaded,
            "post_load_flag": 1,
            "source_backed_manager_vtable_matches": True,
            "stable_sample_count": 5,
            "stable_loaded_rate": True,
        },
        "current_manager": {
            "rate_hz": current,
            "relationships_valid": True,
            "equals_loaded_tick_rate": equal,
        },
        "adjudication": {
            "physics_tweaker_xml_load_completed_before_observation": True,
            "loaded_global_applied_to_cphysics_manager": equal,
            "selected_session_loaded_rate_observed_after_PhysicsTweaker_load": equal,
            "constructor_default_180_used_as_admission_basis": False,
            "current_manager_rate_is_assumed_constant": False,
            "retail_inner_substep_execution_admitted": False,
        },
    }


def _cadence() -> dict:
    return {
        "format": MODULE.CADENCE_FORMAT,
        "ready": True,
        "provenance": {
            "retail_pe_md5": MODULE.RETAIL_EXE_MD5,
            "retail_pe_sha256": MODULE.RETAIL_EXE_SHA256,
        },
        "physics_rate_field": {
            "runtime_rate_global": "DAT_00c130d2",
            "rate_offset": "0x388",
            "final_numeric_rate_not_frozen": True,
        },
    }


def _fixture(tmp_path: Path, *, loaded: int = 240, current: int = 240):
    snapshot = _write_json(
        tmp_path / "snapshot.json",
        _snapshot(loaded=loaded, current=current),
    )
    cadence = _write_json(tmp_path / "cadence.json", _cadence())
    binary = tmp_path / "SHIFT.exe"
    binary.write_bytes(b"synthetic-retail-binary-for-unit-test")
    data = binary.read_bytes()
    return (
        snapshot,
        binary,
        cadence,
        len(data),
        hashlib.md5(data, usedforsecurity=False).hexdigest(),
        hashlib.sha256(data).hexdigest(),
    )


def test_positive_snapshot_promotes_only_loaded_session_rate(tmp_path):
    snapshot, binary, cadence, size, md5, sha256 = _fixture(tmp_path)
    report = MODULE.build(
        snapshot,
        binary,
        cadence,
        expected_size=size,
        expected_md5=md5,
        expected_sha256=sha256,
    )

    assert report["format"] == "SHIFT.SelectedSessionPhysicsTweakerRate/1"
    assert report["ready"] is True
    assert report["selected_session"]["loaded_tick_rate_hz"] == 240
    assert report["selected_session"]["applied_to_current_manager"] is True
    assert report["retail_identity"]["exact_match"] is True
    assert report["retail_identity"]["runtime_pe_and_machine_anchors_match"] is True
    assert report["adjudication"]["selected_session_loaded_rate_admitted"] is True
    assert report["adjudication"]["dynamic_manager_rate_policy_proven"] is False
    assert report["adjudication"]["retail_inner_substep_execution_admitted"] is False
    assert report["next_blocker"] == "inner-substep-runtime-consumption"


def test_manager_divergence_fails_closed(tmp_path):
    snapshot, binary, cadence, size, md5, sha256 = _fixture(tmp_path, current=210)
    with pytest.raises(ValueError, match="applied exactly"):
        MODULE.build(
            snapshot,
            binary,
            cadence,
            expected_size=size,
            expected_md5=md5,
            expected_sha256=sha256,
        )


def test_runtime_identity_must_be_positive(tmp_path):
    snapshot, binary, cadence, size, md5, sha256 = _fixture(tmp_path)
    value = json.loads(snapshot.read_text(encoding="utf-8"))
    value["retail_identity"]["loaded_rate_apply_anchor_matches"] = False
    value["retail_identity"]["identity_ready"] = False
    snapshot.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="runtime retail identity"):
        MODULE.build(
            snapshot,
            binary,
            cadence,
            expected_size=size,
            expected_md5=md5,
            expected_sha256=sha256,
        )


def test_self_test_snapshot_cannot_be_promoted(tmp_path):
    snapshot, binary, cadence, size, md5, sha256 = _fixture(tmp_path)
    value = json.loads(snapshot.read_text(encoding="utf-8"))
    value["self_test"] = True
    snapshot.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="non-self-test"):
        MODULE.build(
            snapshot,
            binary,
            cadence,
            expected_size=size,
            expected_md5=md5,
            expected_sha256=sha256,
        )


def test_binary_identity_mismatch_fails_closed(tmp_path):
    snapshot, binary, cadence, size, md5, sha256 = _fixture(tmp_path)
    with pytest.raises(ValueError, match="MD5 mismatch"):
        MODULE.build(
            snapshot,
            binary,
            cadence,
            expected_size=size,
            expected_md5="0" * 32,
            expected_sha256=sha256,
        )


def test_observed_post_load_180_is_valid_but_not_static_default_evidence(tmp_path):
    snapshot, binary, cadence, size, md5, sha256 = _fixture(
        tmp_path,
        loaded=180,
        current=180,
    )
    report = MODULE.build(
        snapshot,
        binary,
        cadence,
        expected_size=size,
        expected_md5=md5,
        expected_sha256=sha256,
    )
    assert report["ready"] is True
    assert report["selected_session"]["loaded_tick_rate_hz"] == 180
    assert report["selected_session"]["constructor_default_180_is_not_admission_basis"] is True


def test_constructor_default_claim_is_rejected(tmp_path):
    snapshot, binary, cadence, size, md5, sha256 = _fixture(tmp_path)
    value = json.loads(snapshot.read_text(encoding="utf-8"))
    value["adjudication"]["constructor_default_180_used_as_admission_basis"] = True
    snapshot.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="constructor default"):
        MODULE.build(
            snapshot,
            binary,
            cadence,
            expected_size=size,
            expected_md5=md5,
            expected_sha256=sha256,
        )
