from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "run_bmw_offset33b_reduced_static_proof.py"
SPEC = importlib.util.spec_from_file_location("bmw_offset33b_reduced_static_runner", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _args(tmp_path: Path) -> tuple:
    return (
        tmp_path / "project",
        "shift",
        tmp_path / "ghidra-export",
        tmp_path / "out",
    )


def _install_base(monkeypatch, tmp_path: Path, *, store_ready: bool = True):
    out = tmp_path / "out"

    def fake_base(*args, **kwargs):
        out.mkdir(parents=True, exist_ok=True)
        (out / MODULE._base.INSTRUCTION_FILE).write_text("fixture\n", encoding="utf-8")
        (out / MODULE._base.PROVENANCE_FILE).write_text("{}\n", encoding="utf-8")
        bundle = {
            "format": MODULE._base.FORMAT,
            "completed": True,
            "handoff": {
                "offset33b_store_provenance_ready": store_ready,
                "offset33b_value_root_frontier_ready": store_ready,
                "BMW_numeric_offset33b_ready": False,
            },
        }
        (out / MODULE._base.BUNDLE_FILE).write_text(json.dumps(bundle), encoding="utf-8")
        return bundle

    monkeypatch.setattr(MODULE._base, "run_bmw_offset33b_static_proof", fake_base)


def _mass_report() -> dict:
    return {
        "format": MODULE._mass.FORMAT,
        "ready": True,
        "handoff": {
            "offset33b_actual_additional_mass_bootstrap_zero_ready": True,
            "offset33b_additional_mass_term_can_be_elided_for_first_bootstrap": True,
            "BMW_numeric_offset33b_ready": False,
        },
        "scope": {"retracted_manager_record_zero_claim_reused": False},
    }


def _reference_y_report() -> dict:
    return {
        "format": MODULE._reference_y.FORMAT,
        "ready": True,
        "handoff": {
            "offset33b_vehicle_reference_y_bootstrap_zero_ready": True,
            "offset33b_reference_y_reduced_to_negative_graphical_offset": True,
            "BMW_numeric_offset33b_ready": False,
        },
    }


def _load_report(*, exact: bool = True) -> dict:
    worklist = [
        {
            "base_origin_expression_set": ["memory:[esi+0x20]"],
            "displacement": 48,
            "displacement_hex": "0x30",
            "load_width": 4,
            "feeds_offset33b_fields": ["offset33b.x"],
            "semantic_join_ready": False,
        }
    ]
    return {
        "format": MODULE._loads.FORMAT,
        "ready": True,
        "analysis": {"exact_object_field_worklist": worklist if exact else []},
        "handoff": {
            "offset33b_memory_LOAD_frontier_ready": True,
            "offset33b_exact_memory_field_worklist_ready": exact,
            "offset33b_additional_mass_machine_LOAD_join_ready": False,
            "BMW_numeric_offset33b_ready": False,
        },
    }


def _install_metadata_reductions(monkeypatch):
    monkeypatch.setattr(MODULE._mass, "analyze", lambda root: _mass_report())
    monkeypatch.setattr(MODULE._reference_y, "analyze", lambda root: _reference_y_report())


def test_one_command_chain_reuses_single_export_and_emits_current_reductions(
    tmp_path,
    monkeypatch,
):
    _install_base(monkeypatch, tmp_path)
    _install_metadata_reductions(monkeypatch)
    observed: list[tuple[Path, Path, Path]] = []

    def fake_load(store_path, instruction_path, mass_path):
        observed.append((store_path, instruction_path, mass_path))
        return _load_report()

    monkeypatch.setattr(
        MODULE._loads,
        "analyze_bmw_offset33b_memory_load_provenance",
        fake_load,
    )

    report = MODULE.run_bmw_offset33b_reduced_static_proof(
        *_args(tmp_path), ghidra_home=tmp_path / "ghidra"
    )

    out = tmp_path / "out"
    assert report["format"] == MODULE.FORMAT
    assert report["completed"] is True
    assert report["status"] == "semantic-resource-field-join"
    assert report["exact_object_field_worklist"][0]["displacement"] == 48
    assert observed == [
        (
            out / MODULE._base.PROVENANCE_FILE,
            out / MODULE._base.INSTRUCTION_FILE,
            out / MODULE.MASS_FILE,
        )
    ]
    reductions = report["known_semantic_reductions"]
    assert reductions["actual_additional_mass_first_bootstrap_zero"] is True
    assert reductions["additional_mass_term_elidable_for_first_bootstrap"] is True
    assert reductions["vehicle_reference_y_first_bootstrap_zero"] is True
    assert reductions["reference_y_reduced_to_negative_graphical_offset"] is True
    assert reductions["additional_mass_machine_LOAD_join_ready"] is False
    assert report["handoff"]["offset33b_exact_memory_field_worklist_ready"] is True
    assert report["handoff"]["BMW_numeric_offset33b_ready"] is False
    assert report["scope"]["targeted_Ghidra_export_count"] == 1
    assert report["scope"]["additional_Ghidra_export_requested"] is False
    assert report["scope"]["retracted_manager_record_zero_claim_reused"] is False
    assert (out / MODULE.MASS_FILE).is_file()
    assert (out / MODULE.REFERENCE_Y_FILE).is_file()
    assert (out / MODULE.LOAD_FILE).is_file()
    assert (out / MODULE.BUNDLE_FILE).is_file()


def test_incomplete_store_frontier_still_proves_metadata_reductions_but_skips_load(
    tmp_path,
    monkeypatch,
):
    _install_base(monkeypatch, tmp_path, store_ready=False)
    _install_metadata_reductions(monkeypatch)

    def forbidden(*args, **kwargs):
        raise AssertionError("memory load stage must not run before STORE frontier is ready")

    monkeypatch.setattr(
        MODULE._loads,
        "analyze_bmw_offset33b_memory_load_provenance",
        forbidden,
    )

    report = MODULE.run_bmw_offset33b_reduced_static_proof(
        *_args(tmp_path), ghidra_home=tmp_path / "ghidra"
    )

    assert report["status"] == "store-frontier-incomplete"
    reductions = report["known_semantic_reductions"]
    assert reductions["actual_additional_mass_first_bootstrap_zero"] is True
    assert reductions["vehicle_reference_y_first_bootstrap_zero"] is True
    assert report["stages"]["memory_load_provenance"]["state"] == "blocked_by_upstream_gate"
    assert report["handoff"]["offset33b_store_provenance_ready"] is False
    assert report["handoff"]["BMW_numeric_offset33b_ready"] is False


def test_nonexact_load_frontier_routes_to_base_or_helper_resolution(tmp_path, monkeypatch):
    _install_base(monkeypatch, tmp_path)
    _install_metadata_reductions(monkeypatch)
    monkeypatch.setattr(
        MODULE._loads,
        "analyze_bmw_offset33b_memory_load_provenance",
        lambda *args: _load_report(exact=False),
    )

    report = MODULE.run_bmw_offset33b_reduced_static_proof(
        *_args(tmp_path), ghidra_home=tmp_path / "ghidra"
    )
    assert report["decision"]["class"] == "resolve-load-base-or-helper-frontier"
    assert report["handoff"]["offset33b_memory_LOAD_frontier_ready"] is True
    assert report["handoff"]["offset33b_exact_memory_field_worklist_ready"] is False


def test_actual_mass_failure_preserves_base_artifacts_and_failure_bundle(tmp_path, monkeypatch):
    _install_base(monkeypatch, tmp_path)

    def fail(root):
        raise ValueError("actual mass proof drift")

    monkeypatch.setattr(MODULE._mass, "analyze", fail)

    with pytest.raises(ValueError, match="actual mass proof drift"):
        MODULE.run_bmw_offset33b_reduced_static_proof(
            *_args(tmp_path), ghidra_home=tmp_path / "ghidra"
        )

    out = tmp_path / "out"
    bundle = json.loads((out / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert bundle["failed_stage"] == "actual_additional_mass_bootstrap_zero"
    assert "base_bundle" in bundle["artifacts"]
    assert bundle["handoff"]["BMW_numeric_offset33b_ready"] is False
    assert bundle["scope"]["retracted_manager_record_zero_claim_reused"] is False


def test_reference_y_failure_preserves_actual_mass_artifact(tmp_path, monkeypatch):
    _install_base(monkeypatch, tmp_path)
    monkeypatch.setattr(MODULE._mass, "analyze", lambda root: _mass_report())

    def fail(root):
        raise ValueError("reference y proof drift")

    monkeypatch.setattr(MODULE._reference_y, "analyze", fail)

    with pytest.raises(ValueError, match="reference y proof drift"):
        MODULE.run_bmw_offset33b_reduced_static_proof(
            *_args(tmp_path), ghidra_home=tmp_path / "ghidra"
        )

    out = tmp_path / "out"
    bundle = json.loads((out / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert bundle["failed_stage"] == "vehicle_reference_y_bootstrap_zero"
    assert (out / MODULE.MASS_FILE).is_file()
    assert bundle["handoff"]["vehicle_world_transform_ready"] is False


def test_memory_load_failure_preserves_both_reduction_artifacts(tmp_path, monkeypatch):
    _install_base(monkeypatch, tmp_path)
    _install_metadata_reductions(monkeypatch)

    def fail(*args):
        raise ValueError("load provenance drift")

    monkeypatch.setattr(
        MODULE._loads,
        "analyze_bmw_offset33b_memory_load_provenance",
        fail,
    )

    with pytest.raises(ValueError, match="load provenance drift"):
        MODULE.run_bmw_offset33b_reduced_static_proof(
            *_args(tmp_path), ghidra_home=tmp_path / "ghidra"
        )

    out = tmp_path / "out"
    bundle = json.loads((out / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert bundle["failed_stage"] == "memory_load_provenance"
    assert (out / MODULE.MASS_FILE).is_file()
    assert (out / MODULE.REFERENCE_Y_FILE).is_file()
    assert bundle["handoff"]["vehicle_world_transform_ready"] is False


def test_program_and_timeout_validation_fail_before_runner(tmp_path):
    with pytest.raises(ValueError, match="program_name must be exact retail"):
        MODULE.run_bmw_offset33b_reduced_static_proof(
            *_args(tmp_path),
            program_name="OTHER.exe",
            ghidra_home=tmp_path / "ghidra",
        )
    with pytest.raises(ValueError, match="timeout_seconds must be >= 1"):
        MODULE.run_bmw_offset33b_reduced_static_proof(
            *_args(tmp_path),
            timeout_seconds=0,
            ghidra_home=tmp_path / "ghidra",
        )
