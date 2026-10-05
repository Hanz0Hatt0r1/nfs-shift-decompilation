from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "run_bmw_sdf_vehicle_assembly_receiver_proof.py"
SPEC = importlib.util.spec_from_file_location("run_bmw_sdf_receiver_proof_tested", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _report(ready: bool = True) -> dict:
    return {
        "format": MODULE._receiver.FORMAT,
        "ready": ready,
        "handoff": {
            "SDF_loader_owner_receiver_continuity_ready": ready,
            "SDF_loader_receiver_equals_HighDetailVehicle_Init_entry_ECX": ready,
            "SDF_model_to_VHF_vehicle_root_frame_relation_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
    }


def _install_success(monkeypatch, report: dict):
    calls = []

    def fake_run(command, *, env, check):
        calls.append({"command": list(command), "env": dict(env), "check": check})
        output = Path(command[-3])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('{"format":"SHIFT.GhidraFunctionInstructions/2"}\n', encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    analysis_calls = []

    def fake_analyze(ghidra_export, instruction_export):
        analysis_calls.append((ghidra_export, instruction_export))
        return report

    monkeypatch.setattr(
        MODULE._receiver,
        "analyze_bmw_sdf_vehicle_assembly_receiver_provenance",
        fake_analyze,
    )
    return calls, analysis_calls


def test_runner_exports_exact_two_functions_and_emits_positive_handoff(tmp_path, monkeypatch):
    calls, analysis_calls = _install_success(monkeypatch, _report(True))
    out = tmp_path / "proof"
    bundle = MODULE.run_bmw_sdf_vehicle_assembly_receiver_proof(
        tmp_path / "project",
        "shift",
        tmp_path / "ghidra-export",
        out,
        ghidra_home=tmp_path / "ghidra",
        timeout_seconds=41,
    )

    assert bundle["format"] == MODULE.FORMAT
    assert bundle["completed"] is True
    assert bundle["decision"]["class"] == "high-detail-vehicle-to-sdf-receiver-continuity-ready"
    assert bundle["handoff"]["SDF_loader_owner_receiver_continuity_ready"] is True
    assert bundle["handoff"]["SDF_model_to_VHF_vehicle_root_frame_relation_ready"] is False
    assert bundle["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert bundle["scope"]["targeted_functions"] == list(MODULE.TARGETS)
    assert bundle["scope"]["receiver_pointer_promoted_to_frame_identity"] is False

    assert len(calls) == 1
    call = calls[0]
    assert call["command"][-2:] == list(MODULE.TARGETS)
    assert call["command"][-3] == str(out / MODULE.INSTRUCTION_FILE)
    assert call["env"]["GHIDRA_HOME"] == str(tmp_path / "ghidra")
    assert call["env"]["SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS"] == "41"
    assert call["check"] is True
    assert analysis_calls == [(tmp_path / "ghidra-export", out / MODULE.INSTRUCTION_FILE)]
    assert (out / MODULE.PROOF_FILE).is_file()
    persisted = json.loads((out / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert persisted["completed"] is True


def test_blocked_receiver_proof_stays_fail_closed(tmp_path, monkeypatch):
    _install_success(monkeypatch, _report(False))
    bundle = MODULE.run_bmw_sdf_vehicle_assembly_receiver_proof(
        tmp_path / "project",
        "shift",
        tmp_path / "db",
        tmp_path / "out",
        ghidra_home=tmp_path / "ghidra",
    )
    assert bundle["completed"] is True
    assert bundle["decision"]["class"] == "receiver-continuity-blocked"
    assert bundle["handoff"]["SDF_loader_owner_receiver_continuity_ready"] is False
    assert bundle["handoff"]["BODY0_bind_frame_proof_ready"] is False


def test_export_failure_persists_fail_closed_bundle(tmp_path, monkeypatch):
    def fail(command, *, env, check):
        raise subprocess.CalledProcessError(2, command)

    monkeypatch.setattr(MODULE.subprocess, "run", fail)
    out = tmp_path / "out"
    with pytest.raises(subprocess.CalledProcessError):
        MODULE.run_bmw_sdf_vehicle_assembly_receiver_proof(
            tmp_path / "project",
            "shift",
            tmp_path / "db",
            out,
            ghidra_home=tmp_path / "ghidra",
        )
    bundle = json.loads((out / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert bundle["completed"] is False
    assert bundle["failed_stage"] == "instruction_export"
    assert bundle["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert bundle["scope"]["partial_artifacts_preserved"] is True


def test_analysis_failure_preserves_targeted_export(tmp_path, monkeypatch):
    def fake_run(command, *, env, check):
        output = Path(command[-3])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("validated\n", encoding="utf-8")

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)

    def fail(*args):
        raise ValueError("retail drift")

    monkeypatch.setattr(
        MODULE._receiver,
        "analyze_bmw_sdf_vehicle_assembly_receiver_provenance",
        fail,
    )
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="retail drift"):
        MODULE.run_bmw_sdf_vehicle_assembly_receiver_proof(
            tmp_path / "project",
            "shift",
            tmp_path / "db",
            out,
            ghidra_home=tmp_path / "ghidra",
        )
    bundle = json.loads((out / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert bundle["failed_stage"] == "receiver_provenance"
    assert bundle["scope"]["validated_instruction_export_preserved"] is True


def test_requires_exact_program_home_and_positive_timeout(tmp_path, monkeypatch):
    monkeypatch.delenv("GHIDRA_HOME", raising=False)
    with pytest.raises(ValueError, match="GHIDRA_HOME is required"):
        MODULE.run_bmw_sdf_vehicle_assembly_receiver_proof(
            tmp_path / "project", "shift", tmp_path / "db", tmp_path / "out"
        )
    with pytest.raises(ValueError, match="program_name must be exact retail"):
        MODULE.run_bmw_sdf_vehicle_assembly_receiver_proof(
            tmp_path / "project",
            "shift",
            tmp_path / "db",
            tmp_path / "out2",
            program_name="OTHER.exe",
            ghidra_home=tmp_path / "ghidra",
        )
    with pytest.raises(ValueError, match="timeout_seconds must be >= 1"):
        MODULE.run_bmw_sdf_vehicle_assembly_receiver_proof(
            tmp_path / "project",
            "shift",
            tmp_path / "db",
            tmp_path / "out3",
            ghidra_home=tmp_path / "ghidra",
            timeout_seconds=0,
        )
