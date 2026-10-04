from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "run_bmw_offset33b_static_proof.py"
SPEC = importlib.util.spec_from_file_location("run_bmw_offset33b_static_proof_tested", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _frontier(*, ready: bool = True, kinds: list[str] | None = None) -> dict:
    terminal = ["external-or-memory-varnode"] if kinds is None else kinds
    return {
        "format": "SHIFT.BMWOffset33bStoreProvenance/1",
        "ready": ready,
        "analysis": {
            "store_candidates": [
                {
                    "terminal_root_kinds": terminal,
                    "recent_direct_calls_before_store": [
                        {"direct_targets": ["0x007a6be0"]}
                    ],
                }
            ]
            if ready
            else [],
        },
        "handoff": {
            "offset33b_store_provenance_ready": ready,
            "offset33b_value_root_frontier_ready": ready,
            "BMW_numeric_offset33b_ready": False,
            "vehicle_world_transform_ready": False,
        },
    }


def _install_success(monkeypatch, tmp_path: Path, report: dict):
    calls: list[dict] = []

    def fake_run(command, *, env, check):
        calls.append({"command": list(command), "env": dict(env), "check": check})
        output = Path(command[-2])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('{"format":"SHIFT.GhidraFunctionInstructions/2"}\n', encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)

    analysis_calls: list[tuple[Path, Path, Path]] = []

    def fake_analyze(ghidra_export, instruction_export, relation_path):
        analysis_calls.append((ghidra_export, instruction_export, relation_path))
        return report

    monkeypatch.setattr(MODULE._stores, "analyze_bmw_offset33b_store_provenance", fake_analyze)
    return calls, analysis_calls


def test_runner_exports_one_target_and_builds_resource_join_decision(tmp_path, monkeypatch):
    calls, analysis_calls = _install_success(monkeypatch, tmp_path, _frontier())
    out = tmp_path / "proof"
    relation = tmp_path / "relation.json"

    bundle = MODULE.run_bmw_offset33b_static_proof(
        tmp_path / "project",
        "shift",
        tmp_path / "ghidra-export",
        out,
        relation_path=relation,
        ghidra_home=tmp_path / "ghidra",
        timeout_seconds=47,
    )

    assert bundle["format"] == MODULE.FORMAT
    assert bundle["completed"] is True
    assert bundle["decision"]["class"] == "resource-or-init-memory-join"
    assert bundle["handoff"]["offset33b_store_provenance_ready"] is True
    assert bundle["handoff"]["BMW_numeric_offset33b_ready"] is False
    assert bundle["handoff"]["vehicle_world_transform_ready"] is False
    assert bundle["scope"]["targeted_function_count"] == 1
    assert bundle["scope"]["targeted_function"] == MODULE.TARGET
    assert bundle["scope"]["ghidra_project_opened_read_only"] is True
    assert bundle["scope"]["ghidra_autoanalysis_requested"] is False

    assert len(calls) == 1
    call = calls[0]
    assert call["command"][-1] == MODULE.TARGET
    assert call["command"][-2] == str(out / MODULE.INSTRUCTION_FILE)
    assert call["env"]["GHIDRA_HOME"] == str(tmp_path / "ghidra")
    assert call["env"]["SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS"] == "47"
    assert call["check"] is True
    assert analysis_calls == [
        (
            tmp_path / "ghidra-export",
            out / MODULE.INSTRUCTION_FILE,
            relation,
        )
    ]
    assert (out / MODULE.PROVENANCE_FILE).is_file()
    persisted = json.loads((out / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert persisted["completed"] is True


def test_constant_roots_route_to_exact_pcode_evaluation(tmp_path, monkeypatch):
    _install_success(
        monkeypatch,
        tmp_path,
        _frontier(kinds=["constant", "address-space-selector"]),
    )
    bundle = MODULE.run_bmw_offset33b_static_proof(
        tmp_path / "project",
        "shift",
        tmp_path / "ghidra-export",
        tmp_path / "out",
        ghidra_home=tmp_path / "ghidra",
    )
    assert bundle["decision"]["class"] == "constant-root-evaluation"
    assert bundle["handoff"]["BMW_numeric_offset33b_ready"] is False


def test_register_roots_keep_nearby_helper_targets_finite(tmp_path, monkeypatch):
    _install_success(
        monkeypatch,
        tmp_path,
        _frontier(kinds=["floating-register"]),
    )
    bundle = MODULE.run_bmw_offset33b_static_proof(
        tmp_path / "project",
        "shift",
        tmp_path / "ghidra-export",
        tmp_path / "out",
        ghidra_home=tmp_path / "ghidra",
    )
    assert bundle["decision"]["class"] == "register-or-helper-return-provenance"
    assert bundle["decision"]["nearby_direct_targets"] == ["0x007a6be0"]


def test_blocked_store_frontier_is_a_completed_fail_closed_bundle(tmp_path, monkeypatch):
    _install_success(monkeypatch, tmp_path, _frontier(ready=False))
    bundle = MODULE.run_bmw_offset33b_static_proof(
        tmp_path / "project",
        "shift",
        tmp_path / "ghidra-export",
        tmp_path / "out",
        ghidra_home=tmp_path / "ghidra",
    )
    assert bundle["completed"] is True
    assert bundle["decision"]["class"] == "store-frontier-incomplete"
    assert bundle["handoff"]["offset33b_store_provenance_ready"] is False
    assert bundle["handoff"]["BMW_numeric_offset33b_ready"] is False


def test_export_failure_persists_failure_bundle(tmp_path, monkeypatch):
    def fail(command, *, env, check):
        raise subprocess.CalledProcessError(3, command)

    monkeypatch.setattr(MODULE.subprocess, "run", fail)
    out = tmp_path / "proof"
    with pytest.raises(subprocess.CalledProcessError):
        MODULE.run_bmw_offset33b_static_proof(
            tmp_path / "project",
            "shift",
            tmp_path / "ghidra-export",
            out,
            ghidra_home=tmp_path / "ghidra",
        )

    bundle = json.loads((out / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert bundle["completed"] is False
    assert bundle["failed_stage"] == "instruction_export"
    assert bundle["handoff"]["BMW_numeric_offset33b_ready"] is False
    assert bundle["scope"]["partial_artifacts_preserved"] is True


def test_analysis_failure_preserves_validated_instruction_export(tmp_path, monkeypatch):
    def fake_run(command, *, env, check):
        output = Path(command[-2])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("validated\n", encoding="utf-8")

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)

    def fail(*args):
        raise ValueError("retail drift")

    monkeypatch.setattr(MODULE._stores, "analyze_bmw_offset33b_store_provenance", fail)
    out = tmp_path / "proof"
    with pytest.raises(ValueError, match="retail drift"):
        MODULE.run_bmw_offset33b_static_proof(
            tmp_path / "project",
            "shift",
            tmp_path / "ghidra-export",
            out,
            ghidra_home=tmp_path / "ghidra",
        )

    bundle = json.loads((out / MODULE.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert bundle["completed"] is False
    assert bundle["failed_stage"] == "store_provenance"
    assert bundle["scope"]["validated_instruction_export_preserved"] is True
    assert (out / MODULE.INSTRUCTION_FILE).read_text(encoding="utf-8") == "validated\n"


def test_requires_exact_program_ghidra_home_and_positive_timeout(tmp_path, monkeypatch):
    monkeypatch.delenv("GHIDRA_HOME", raising=False)
    with pytest.raises(ValueError, match="GHIDRA_HOME is required"):
        MODULE.run_bmw_offset33b_static_proof(
            tmp_path / "project", "shift", tmp_path / "db", tmp_path / "out"
        )
    with pytest.raises(ValueError, match="program_name must be exact retail"):
        MODULE.run_bmw_offset33b_static_proof(
            tmp_path / "project",
            "shift",
            tmp_path / "db",
            tmp_path / "out2",
            program_name="OTHER.exe",
            ghidra_home=tmp_path / "ghidra",
        )
    with pytest.raises(ValueError, match="timeout_seconds must be >= 1"):
        MODULE.run_bmw_offset33b_static_proof(
            tmp_path / "project",
            "shift",
            tmp_path / "db",
            tmp_path / "out3",
            ghidra_home=tmp_path / "ghidra",
            timeout_seconds=0,
        )
