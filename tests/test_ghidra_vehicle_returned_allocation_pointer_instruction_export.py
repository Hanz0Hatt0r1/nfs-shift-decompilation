import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "run_vehicle_returned_allocation_pointer_instruction_export.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_returned_pointer_instruction_export", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_boundary(path, module, *, targets=None):
    targets = ["0x00639000", "0x0063a000"] if targets is None else targets
    path.write_text(
        json.dumps(
            {
                "format": module.BOUNDARY_FORMAT,
                "return_origin_targets": list(targets),
                "required_instruction_targets": list(targets),
                "returned_allocation_pointer_role_state": "unknown",
                "returned_allocation_pointer_role_proven": False,
                "vehicle_create_bridges": [
                    {
                        "descriptor": 2,
                        "vehicle_pointer_source_node": "memory-source:0x00715700:0x00715730:ESI:64",
                        "returned_allocation_pointer_role_state": "unknown",
                    }
                ],
                "blockers": [module.EXPECTED_BLOCKER],
            }
        ),
        encoding="utf-8",
    )
    return path


def _fixture(tmp_path):
    module = _load_module()
    boundary = _write_boundary(tmp_path / "boundary.json", module)
    fake_runner = tmp_path / "run_shift_function_instructions.sh"
    fake_runner.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    module.RUNNER = fake_runner
    return module, boundary


def test_dry_run_materializes_exact_command_without_invoking_subprocess(tmp_path, monkeypatch):
    module, boundary = _fixture(tmp_path)
    called = False

    def _unexpected(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("subprocess must not run in dry-run mode")

    monkeypatch.setattr(module.subprocess, "run", _unexpected)
    output = tmp_path / "out" / "instructions.jsonl"
    report = module.run_vehicle_returned_allocation_pointer_instruction_export(
        boundary,
        Path("/projects/shift"),
        "shift",
        "SHIFT.exe",
        output,
        dry_run=True,
    )

    assert called is False
    assert report["status"] == "dry-run"
    assert report["return_code"] is None
    assert report["targets"] == ["0x00639000", "0x0063a000"]
    assert report["command"] == [
        "bash",
        str(module.RUNNER),
        "/projects/shift",
        "shift",
        "SHIFT.exe",
        str(output),
        "0x00639000",
        "0x0063a000",
    ]
    assert report["returned_allocation_pointer_role_proven"] is False
    assert report["scope"]["instruction_export_is_semantic_proof"] is False


def test_successful_run_requires_output_file_and_preserves_context(tmp_path, monkeypatch):
    module, boundary = _fixture(tmp_path)
    output = tmp_path / "out" / "instructions.jsonl"
    seen = []

    def _run(command, check):
        seen.append((command, check))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("{}\n", encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", _run)
    report = module.run_vehicle_returned_allocation_pointer_instruction_export(
        boundary,
        tmp_path / "project",
        "shift",
        "SHIFT.exe",
        output,
    )

    assert len(seen) == 1
    assert seen[0][1] is False
    assert seen[0][0][-2:] == ["0x00639000", "0x0063a000"]
    assert report["status"] == "completed"
    assert report["return_code"] == 0
    assert report["vehicle_create_bridges"][0]["descriptor"] == 2
    assert report["scope"]["original_game_executed"] is False
    assert report["scope"]["new_runtime_capture_required"] is False


def test_nonzero_export_status_is_fail_closed(tmp_path, monkeypatch):
    module, boundary = _fixture(tmp_path)
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda command, check: SimpleNamespace(returncode=7),
    )
    with pytest.raises(RuntimeError, match="status 7"):
        module.run_vehicle_returned_allocation_pointer_instruction_export(
            boundary,
            tmp_path / "project",
            "shift",
            "SHIFT.exe",
            tmp_path / "instructions.jsonl",
        )


def test_success_status_without_output_is_fail_closed(tmp_path, monkeypatch):
    module, boundary = _fixture(tmp_path)
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda command, check: SimpleNamespace(returncode=0),
    )
    with pytest.raises(RuntimeError, match="did not create output"):
        module.run_vehicle_returned_allocation_pointer_instruction_export(
            boundary,
            tmp_path / "project",
            "shift",
            "SHIFT.exe",
            tmp_path / "instructions.jsonl",
        )


def test_boundary_cannot_preclaim_semantics(tmp_path):
    module, boundary = _fixture(tmp_path)
    payload = json.loads(boundary.read_text(encoding="utf-8"))
    payload["returned_allocation_pointer_role_proven"] = True
    payload["returned_allocation_pointer_role_state"] = "verified"
    boundary.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="must remain unresolved"):
        module.run_vehicle_returned_allocation_pointer_instruction_export(
            boundary,
            tmp_path,
            "shift",
            "SHIFT.exe",
            tmp_path / "out.jsonl",
            dry_run=True,
        )


def test_boundary_must_retain_semantic_blocker(tmp_path):
    module, boundary = _fixture(tmp_path)
    payload = json.loads(boundary.read_text(encoding="utf-8"))
    payload["blockers"] = []
    boundary.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="missing the returned allocation-pointer blocker"):
        module.run_vehicle_returned_allocation_pointer_instruction_export(
            boundary,
            tmp_path,
            "shift",
            "SHIFT.exe",
            tmp_path / "out.jsonl",
            dry_run=True,
        )


def test_target_list_must_be_nonempty_unique_sorted_and_from_origin_frontier(tmp_path):
    module, boundary = _fixture(tmp_path)

    payload = json.loads(boundary.read_text(encoding="utf-8"))
    payload["required_instruction_targets"] = []
    boundary.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="no required instruction targets"):
        module._load_boundary(boundary)

    _write_boundary(boundary, module, targets=["0x00639000", "0x00639000"])
    with pytest.raises(ValueError, match="duplicate"):
        module._load_boundary(boundary)

    _write_boundary(boundary, module, targets=["0x0063a000", "0x00639000"])
    with pytest.raises(ValueError, match="must be sorted"):
        module._load_boundary(boundary)

    _write_boundary(boundary, module)
    payload = json.loads(boundary.read_text(encoding="utf-8"))
    payload["required_instruction_targets"] = ["0x0063b000"]
    boundary.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="not in the return-origin frontier"):
        module._load_boundary(boundary)


def test_missing_underlying_runner_fails_closed_even_in_dry_run(tmp_path):
    module, boundary = _fixture(tmp_path)
    module.RUNNER = tmp_path / "missing.sh"
    with pytest.raises(FileNotFoundError, match="missing Ghidra instruction exporter runner"):
        module.run_vehicle_returned_allocation_pointer_instruction_export(
            boundary,
            tmp_path,
            "shift",
            "SHIFT.exe",
            tmp_path / "out.jsonl",
            dry_run=True,
        )


def test_empty_project_or_program_name_is_rejected(tmp_path):
    module, boundary = _fixture(tmp_path)
    with pytest.raises(ValueError, match="project_name"):
        module.run_vehicle_returned_allocation_pointer_instruction_export(
            boundary,
            tmp_path,
            "",
            "SHIFT.exe",
            tmp_path / "out.jsonl",
            dry_run=True,
        )
    with pytest.raises(ValueError, match="program_name"):
        module.run_vehicle_returned_allocation_pointer_instruction_export(
            boundary,
            tmp_path,
            "shift",
            "",
            tmp_path / "out.jsonl",
            dry_run=True,
        )
