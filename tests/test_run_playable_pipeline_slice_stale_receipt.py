from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "run_playable_pipeline_slice.py"
SPEC = importlib.util.spec_from_file_location(
    "run_playable_pipeline_slice_stale_receipt",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_stale_receipt_is_removed_before_bootstrap_failure(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    receipt = out / "execution_result.json"
    receipt.write_text('{"ready": true}\n', encoding="utf-8")
    calls = {"bootstrap": 0}

    def fake_bootstrap(args):
        calls["bootstrap"] += 1
        assert not receipt.exists()
        return 2

    monkeypatch.setattr(MODULE.bootstrap, "main", fake_bootstrap)
    with pytest.raises(MODULE.ExecutionError, match="bootstrap failed"):
        MODULE.execute_playable_pipeline_slice(
            ["input.bff", "--output", str(out)],
            runner=lambda *args, **kwargs: pytest.fail("runtime must not run"),
        )
    assert calls["bootstrap"] == 1
    assert not receipt.exists()


def test_stale_receipt_removal_is_recorded_on_success(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    receipt = out / "execution_result.json"
    receipt.write_text('{"status": "old"}\n', encoding="utf-8")
    runtime = out / "shift_runtime"
    runtime.write_bytes(b"runtime")
    runtime.chmod(0o755)
    plan_path = out / "launch_plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "format": "SHIFT.NativeVerticalSliceLaunchPlan/1",
                "ready": True,
                "argv": [str(runtime.resolve())],
                "environment": {},
            }
        ),
        encoding="utf-8",
    )
    report_path = out / "playable_pipeline_bootstrap.json"
    report_path.write_text(
        json.dumps(
            {
                "format": "SHIFT.PlayableResourcePipelineBootstrap/1",
                "ready": True,
                "launch_plan_ready": True,
                "track": "Track",
                "vehicle": "Vehicle",
                "artifacts": {"launch_plan": str(plan_path.resolve())},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(MODULE.bootstrap, "main", lambda args: 0)
    result = MODULE.execute_playable_pipeline_slice(
        ["input.bff", "-o", str(out)],
        runner=lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )
    assert result["ready"] is True
    assert result["stale_execution_receipt_removed"] is True
    assert result["boundary"]["stale_execution_receipt_cleared_before_attempt"] is True
    stored = json.loads(receipt.read_text(encoding="utf-8"))
    assert stored["status"] == "completed"
    assert stored["stale_execution_receipt_removed"] is True


def test_receipt_directory_blocks_attempt_before_bootstrap(tmp_path, monkeypatch):
    out = tmp_path / "out"
    receipt = out / "execution_result.json"
    receipt.mkdir(parents=True)
    calls = {"bootstrap": 0}

    def fake_bootstrap(args):
        calls["bootstrap"] += 1
        return 0

    monkeypatch.setattr(MODULE.bootstrap, "main", fake_bootstrap)
    with pytest.raises(MODULE.ExecutionError, match="receipt path is a directory"):
        MODULE.execute_playable_pipeline_slice(
            ["input.bff", "--output", str(out)],
            runner=lambda *args, **kwargs: pytest.fail("runtime must not run"),
        )
    assert calls["bootstrap"] == 0
