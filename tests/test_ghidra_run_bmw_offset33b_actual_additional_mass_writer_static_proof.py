from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "run_bmw_offset33b_actual_additional_mass_writer_static_proof.py"
SPEC = importlib.util.spec_from_file_location("actual_additional_mass_writer_runner", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _frontier(*, ready: bool = True, direct_writer: bool = True) -> dict:
    writers = [
        {
            "function": MODULE._writer.ACTUAL_PARTICIPANT,
            "instruction": "0x0072ed30",
            "displacement": 0xBA0,
            "terminal_root_kinds": ["constant"],
            "numeric_value_proven": False,
        }
    ] if direct_writer else []
    forwards = [] if direct_writer else [
        {
            "function": MODULE._writer.VEHICLE_BASE_CTOR,
            "callsite": "0x0079bff6",
            "callee": "0x0074ea70",
            "ECX_origins_before_call": ["entry:ECX"],
            "ECX_is_current_function_entry_receiver": True,
        }
    ]
    return {
        "format": MODULE._writer.FORMAT,
        "version": 1,
        "ready": ready,
        "status": "writer-frontier-ready" if ready else "blocked",
        "analysis": {
            "direct_target_writers": writers,
            "same_receiver_forward_worklist": forwards,
        },
        "handoff": {
            "actual_additional_mass_writer_frontier_ready": ready,
            "actual_additional_mass_direct_writer_found": bool(writers),
            "actual_additional_mass_numeric_value_ready": False,
            "BMW_numeric_offset33b_ready": False,
            "vehicle_world_transform_ready": False,
        },
    }


def _install_success(monkeypatch, report: dict):
    process_calls: list[dict] = []
    analysis_calls: list[tuple[Path, Path]] = []

    def fake_run(command, *, env, check):
        process_calls.append({"command": list(command), "env": dict(env), "check": check})
        output = Path(command[5])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('{"format":"SHIFT.GhidraFunctionInstructions/2"}\n', encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    def fake_analyze(ghidra_export, instruction_export):
        analysis_calls.append((ghidra_export, instruction_export))
        return report

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    monkeypatch.setattr(
        MODULE._writer,
        "analyze_bmw_offset33b_actual_additional_mass_writer_frontier",
        fake_analyze,
    )
    return process_calls, analysis_calls


def test_runner_exports_exact_four_targets_once_and_routes_direct_writer(tmp_path, monkeypatch):
    process_calls, analysis_calls = _install_success(monkeypatch, _frontier())
    out = tmp_path / "proof"
    db = tmp_path / "ghidra-export"

    bundle = MODULE.run_bmw_offset33b_actual_additional_mass_writer_static_proof(
        tmp_path / "project",
        "shift",
        db,
        out,
        ghidra_home=tmp_path / "ghidra",
        timeout_seconds=31,
    )

    assert bundle["format"] == MODULE.FORMAT
    assert bundle["completed"] is True
    assert bundle["decision"]["class"] == "evaluate-direct-writer-value"
    assert bundle["handoff"]["actual_additional_mass_writer_frontier_ready"] is True
    assert bundle["handoff"]["actual_additional_mass_direct_writer_found"] is True
    assert bundle["handoff"]["actual_additional_mass_numeric_value_ready"] is False
    assert bundle["handoff"]["BMW_numeric_offset33b_ready"] is False
    assert bundle["handoff"]["vehicle_world_transform_ready"] is False
    assert bundle["scope"]["manager_record_zero_assumption_reused"] is False
    assert bundle["scope"]["targeted_Ghidra_export_count"] == 1
    assert bundle["scope"]["targeted_function_count"] == 4
    assert bundle["scope"]["targeted_functions"] == list(MODULE.TARGET_NAMES)

    assert len(process_calls) == 1
    call = process_calls[0]
    assert call["command"][:2] == ["bash", str(MODULE.RUNNER)]
    assert call["command"][2:6] == [
        str(tmp_path / "project"),
        "shift",
        MODULE._writer.PROGRAM,
        str(out / MODULE.INSTRUCTION_FILE),
    ]
    assert call["command"][6:] == list(MODULE.TARGET_NAMES)
    assert call["env"]["GHIDRA_HOME"] == str(tmp_path / "ghidra")
    assert call["env"]["SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS"] == "31"
    assert call["check"] is True
    assert analysis_calls == [(db, out / MODULE.INSTRUCTION_FILE)]
    assert (out / MODULE.FRONTIER_FILE).is_file()
    persisted = json.loads((out / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert persisted["decision"]["class"] == "evaluate-direct-writer-value"


def test_ready_frontier_without_writer_routes_same_receiver_callees(tmp_path, monkeypatch):
    _install_success(monkeypatch, _frontier(direct_writer=False))
    bundle = MODULE.run_bmw_offset33b_actual_additional_mass_writer_static_proof(
        tmp_path / "project",
        "shift",
        tmp_path / "db",
        tmp_path / "out",
        ghidra_home=tmp_path / "ghidra",
    )
    assert bundle["decision"]["class"] == "export-same-receiver-forward-callees"
    assert bundle["decision"]["candidate_count"] == 1
    assert bundle["same_receiver_forward_worklist"][0]["callee"] == "0x0074ea70"
    assert bundle["handoff"]["actual_additional_mass_direct_writer_found"] is False


def test_blocked_frontier_routes_receiver_resolution(tmp_path, monkeypatch):
    _install_success(monkeypatch, _frontier(ready=False, direct_writer=False))
    bundle = MODULE.run_bmw_offset33b_actual_additional_mass_writer_static_proof(
        tmp_path / "project",
        "shift",
        tmp_path / "db",
        tmp_path / "out",
        ghidra_home=tmp_path / "ghidra",
    )
    assert bundle["decision"]["class"] == "resolve-constructor-receiver-proof"
    assert bundle["handoff"]["actual_additional_mass_writer_frontier_ready"] is False
    assert bundle["handoff"]["BMW_numeric_offset33b_ready"] is False


def test_instruction_export_failure_persists_fail_closed_bundle(tmp_path, monkeypatch):
    def fail(command, *, env, check):
        raise subprocess.CalledProcessError(7, command)

    monkeypatch.setattr(MODULE.subprocess, "run", fail)
    out = tmp_path / "proof"
    with pytest.raises(subprocess.CalledProcessError):
        MODULE.run_bmw_offset33b_actual_additional_mass_writer_static_proof(
            tmp_path / "project",
            "shift",
            tmp_path / "db",
            out,
            ghidra_home=tmp_path / "ghidra",
        )

    bundle = json.loads((out / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert bundle["completed"] is False
    assert bundle["failed_stage"] == "instruction_export"
    assert bundle["handoff"]["actual_additional_mass_numeric_value_ready"] is False
    assert bundle["handoff"]["vehicle_world_transform_ready"] is False
    assert bundle["scope"]["partial_artifacts_preserved"] is True


def test_writer_frontier_failure_preserves_instruction_export(tmp_path, monkeypatch):
    def fake_run(command, *, env, check):
        output = Path(command[5])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("validated\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    def fail(*args):
        raise ValueError("constructor drift")

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    monkeypatch.setattr(
        MODULE._writer,
        "analyze_bmw_offset33b_actual_additional_mass_writer_frontier",
        fail,
    )
    out = tmp_path / "proof"
    with pytest.raises(ValueError, match="constructor drift"):
        MODULE.run_bmw_offset33b_actual_additional_mass_writer_static_proof(
            tmp_path / "project",
            "shift",
            tmp_path / "db",
            out,
            ghidra_home=tmp_path / "ghidra",
        )

    assert (out / MODULE.INSTRUCTION_FILE).read_text(encoding="utf-8") == "validated\n"
    bundle = json.loads((out / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert bundle["failed_stage"] == "writer_frontier"
    assert bundle["handoff"]["BMW_numeric_offset33b_ready"] is False


def test_requires_exact_program_ghidra_home_and_positive_timeout(tmp_path, monkeypatch):
    monkeypatch.delenv("GHIDRA_HOME", raising=False)
    with pytest.raises(ValueError, match="GHIDRA_HOME is required"):
        MODULE.run_bmw_offset33b_actual_additional_mass_writer_static_proof(
            tmp_path / "project", "shift", tmp_path / "db", tmp_path / "out"
        )
    with pytest.raises(ValueError, match="program_name must be exact retail"):
        MODULE.run_bmw_offset33b_actual_additional_mass_writer_static_proof(
            tmp_path / "project",
            "shift",
            tmp_path / "db",
            tmp_path / "out2",
            program_name="OTHER.exe",
            ghidra_home=tmp_path / "ghidra",
        )
    with pytest.raises(ValueError, match="timeout_seconds must be >= 1"):
        MODULE.run_bmw_offset33b_actual_additional_mass_writer_static_proof(
            tmp_path / "project",
            "shift",
            tmp_path / "db",
            tmp_path / "out3",
            ghidra_home=tmp_path / "ghidra",
            timeout_seconds=0,
        )
