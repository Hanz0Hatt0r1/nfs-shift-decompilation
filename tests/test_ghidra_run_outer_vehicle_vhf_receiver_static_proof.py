from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "run_outer_vehicle_vhf_receiver_static_proof.py"
SPEC = importlib.util.spec_from_file_location("outer_vehicle_vhf_runner", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _frontier_report() -> dict:
    return {
        "format": MODULE._frontier.FORMAT,
        "ready": True,
        "status": "frontier-ready",
        "handoff": {
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
        },
    }


def _receiver_report(*, ambiguous: bool = False) -> dict:
    return {
        "format": MODULE._receivers.FORMAT,
        "ready": True,
        "status": "receiver-frontier-ambiguous" if ambiguous else "receiver-frontier-ready",
        "next_owner_candidates": [
            {
                "callsite": "0x00792828",
                "callee": "0x007afb60",
                "callee_name": "FUN_007afb60",
                "ECX_origins_before_call": ["memory:[esi+0x20]"],
                "ECX_origin_deterministic": not ambiguous,
                "same_ECX_origin_expression_set_as_HDVehicle_sink": True,
            },
            {
                "callsite": "0x0079280e",
                "callee": "0x007876e0",
                "callee_name": "FUN_007876e0",
                "ECX_origins_before_call": ["entry:ECX"],
                "ECX_origin_deterministic": True,
                "same_ECX_origin_expression_set_as_HDVehicle_sink": False,
            },
        ],
        "handoff": {
            "outer_setter_sink_ECX_provenance_evaluated": True,
            "outer_setter_sink_ECX_provenance_unambiguous": not ambiguous,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
        },
    }


def _install_success(monkeypatch, receiver: dict):
    monkeypatch.setattr(
        MODULE._frontier,
        "build_outer_vehicle_vhf_root_relation_frontier",
        lambda *args: _frontier_report(),
    )

    calls: list[dict] = []

    def fake_run(command, *, env, check):
        calls.append({"command": list(command), "env": dict(env), "check": check})
        output = Path(command[-2])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('{"format":"SHIFT.GhidraFunctionInstructions/2"}\n', encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)

    analysis_calls: list[tuple[Path, Path]] = []

    def fake_analyze(frontier_path, instruction_path):
        analysis_calls.append((frontier_path, instruction_path))
        return receiver

    monkeypatch.setattr(
        MODULE._receivers,
        "analyze_outer_vehicle_transform_sink_receiver_provenance",
        fake_analyze,
    )
    return calls, analysis_calls


def test_runner_builds_deterministic_owner_domain_partition(tmp_path, monkeypatch):
    calls, analysis_calls = _install_success(monkeypatch, _receiver_report())
    out = tmp_path / "proof"
    bundle = MODULE.run_outer_vehicle_vhf_receiver_static_proof(
        tmp_path / "project",
        "shift",
        tmp_path / "ghidra-export",
        tmp_path / "symbolic.json",
        out,
        ghidra_home=tmp_path / "ghidra",
        timeout_seconds=41,
    )

    assert bundle["format"] == MODULE.FORMAT
    assert bundle["completed"] is True
    assert bundle["decision"]["class"] == "deterministic-owner-domain-partition"
    assert len(bundle["decision"]["shared_HDVehicle_origin_expression_candidates"]) == 1
    assert len(bundle["decision"]["distinct_origin_expression_candidates"]) == 1
    assert bundle["handoff"]["outer_setter_sink_ECX_provenance_unambiguous"] is True
    assert bundle["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert bundle["handoff"]["vehicle_world_transform_ready"] is False
    assert bundle["scope"]["targeted_function_count"] == 1
    assert bundle["scope"]["targeted_function"] == MODULE.TARGET
    assert bundle["scope"]["receiver_partition_promoted_to_pointer_equality"] is False
    assert bundle["scope"]["stack_transform_values_evaluated"] is False

    assert len(calls) == 1
    assert calls[0]["command"][-1] == MODULE.TARGET
    assert calls[0]["command"][-2] == str(out / MODULE.INSTRUCTION_FILE)
    assert calls[0]["env"]["GHIDRA_HOME"] == str(tmp_path / "ghidra")
    assert calls[0]["env"]["SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS"] == "41"
    assert analysis_calls == [(out / MODULE.FRONTIER_FILE, out / MODULE.INSTRUCTION_FILE)]
    assert (out / MODULE.FRONTIER_FILE).is_file()
    assert (out / MODULE.RECEIVER_FILE).is_file()
    persisted = json.loads((out / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert persisted["completed"] is True


def test_ambiguous_receiver_report_routes_to_resolution(tmp_path, monkeypatch):
    _install_success(monkeypatch, _receiver_report(ambiguous=True))
    bundle = MODULE.run_outer_vehicle_vhf_receiver_static_proof(
        tmp_path / "project",
        "shift",
        tmp_path / "db",
        tmp_path / "symbolic.json",
        tmp_path / "out",
        ghidra_home=tmp_path / "ghidra",
    )
    assert bundle["decision"]["class"] == "resolve-receiver-ambiguity"
    assert len(bundle["decision"]["ambiguous_candidates"]) == 1
    assert bundle["handoff"]["outer_setter_sink_ECX_provenance_unambiguous"] is False


def test_frontier_failure_persists_failure_bundle(tmp_path, monkeypatch):
    def fail(*args):
        raise ValueError("retail drift")

    monkeypatch.setattr(
        MODULE._frontier,
        "build_outer_vehicle_vhf_root_relation_frontier",
        fail,
    )
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="retail drift"):
        MODULE.run_outer_vehicle_vhf_receiver_static_proof(
            tmp_path / "project",
            "shift",
            tmp_path / "db",
            tmp_path / "symbolic.json",
            out,
            ghidra_home=tmp_path / "ghidra",
        )
    bundle = json.loads((out / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert bundle["completed"] is False
    assert bundle["failed_stage"] == "frontier"
    assert bundle["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False


def test_instruction_export_failure_preserves_frontier(tmp_path, monkeypatch):
    monkeypatch.setattr(
        MODULE._frontier,
        "build_outer_vehicle_vhf_root_relation_frontier",
        lambda *args: _frontier_report(),
    )

    def fail(command, *, env, check):
        raise subprocess.CalledProcessError(7, command)

    monkeypatch.setattr(MODULE.subprocess, "run", fail)
    out = tmp_path / "out"
    with pytest.raises(subprocess.CalledProcessError):
        MODULE.run_outer_vehicle_vhf_receiver_static_proof(
            tmp_path / "project",
            "shift",
            tmp_path / "db",
            tmp_path / "symbolic.json",
            out,
            ghidra_home=tmp_path / "ghidra",
        )
    assert (out / MODULE.FRONTIER_FILE).is_file()
    bundle = json.loads((out / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert bundle["failed_stage"] == "instruction_export"
    assert bundle["scope"]["partial_artifacts_preserved"] is True


def test_receiver_analysis_failure_preserves_instruction_export(tmp_path, monkeypatch):
    _install_success(monkeypatch, _receiver_report())

    def fail(*args):
        raise ValueError("receiver drift")

    monkeypatch.setattr(
        MODULE._receivers,
        "analyze_outer_vehicle_transform_sink_receiver_provenance",
        fail,
    )
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="receiver drift"):
        MODULE.run_outer_vehicle_vhf_receiver_static_proof(
            tmp_path / "project",
            "shift",
            tmp_path / "db",
            tmp_path / "symbolic.json",
            out,
            ghidra_home=tmp_path / "ghidra",
        )
    assert (out / MODULE.INSTRUCTION_FILE).is_file()
    bundle = json.loads((out / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert bundle["failed_stage"] == "receiver_provenance"


def test_requires_exact_program_ghidra_home_and_positive_timeout(tmp_path, monkeypatch):
    monkeypatch.delenv("GHIDRA_HOME", raising=False)
    with pytest.raises(ValueError, match="GHIDRA_HOME is required"):
        MODULE.run_outer_vehicle_vhf_receiver_static_proof(
            tmp_path / "project", "shift", tmp_path / "db", tmp_path / "s.json", tmp_path / "out"
        )
    with pytest.raises(ValueError, match="program_name must be exact retail"):
        MODULE.run_outer_vehicle_vhf_receiver_static_proof(
            tmp_path / "project", "shift", tmp_path / "db", tmp_path / "s.json", tmp_path / "out2",
            program_name="OTHER.exe", ghidra_home=tmp_path / "ghidra"
        )
    with pytest.raises(ValueError, match="timeout_seconds must be >= 1"):
        MODULE.run_outer_vehicle_vhf_receiver_static_proof(
            tmp_path / "project", "shift", tmp_path / "db", tmp_path / "s.json", tmp_path / "out3",
            ghidra_home=tmp_path / "ghidra", timeout_seconds=0
        )
