from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPLITTER = ROOT / "tools/ghidra/split_s5_retail_instruction_bundle.py"
RUNNER = ROOT / "tools/ghidra/run_s5_retail_instruction_bundle.sh"
SPEC = importlib.util.spec_from_file_location("split_s5_retail_instruction_bundle", SPLITTER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _row(name: str) -> dict:
    address = "0x" + name.removeprefix("FUN_")
    return {
        "format": "SHIFT.GhidraFunctionInstructions/2",
        "requested": name,
        "found": True,
        "function": {"address": address, "name": name},
        "instruction_count": 1,
        "instructions": [
            {
                "address": address,
                "mnemonic": "RET",
                "operands": [],
                "pcode": [{"opcode": "RETURN", "output": None, "inputs": []}],
            }
        ],
    }


def _write(path: Path, names) -> None:
    path.write_text(
        "".join(json.dumps(_row(name)) + "\n" for name in names),
        encoding="utf-8",
    )


def test_exact_union_splits_back_to_corrected_analyzer_surfaces(tmp_path):
    bundle = tmp_path / "bundle.jsonl"
    _write(bundle, MODULE.BUNDLE_TARGETS)

    report = MODULE.split(bundle, tmp_path / "out")

    assert report["format"] == "SHIFT.S5RetailInstructionExecutionBundle/1"
    assert report["ready"] is True
    assert report["bundle"]["target_count"] == 15
    assert report["bundle"]["targets"] == list(MODULE.BUNDLE_TARGETS)
    assert report["subsets"]["scheduler"]["targets"] == list(MODULE.SCHEDULER)
    assert report["subsets"]["rate_accessor"]["targets"] == list(MODULE.RATE_ACCESSOR)
    assert report["subsets"]["bmanager"]["targets"] == list(MODULE.BMANAGER)
    assert report["subsets"]["scheduler"]["target_count"] == 3
    assert report["subsets"]["rate_accessor"]["target_count"] == 5
    assert report["subsets"]["bmanager"]["target_count"] == 9
    assert report["corrections"]["bmanager_subset_uses_correct_default_dispatcher_FUN_00647d80"] is True
    assert report["corrections"]["FUN_00647da0_plus_0x18_assumption_retired"] is True
    assert report["corrections"]["FUN_0070fe90_return_as_FUN_006485b0_stack_argument_retired"] is True
    assert report["proof_scope"]["retail_machine_semantics_promoted"] is False
    assert report["proof_scope"]["retail_cadence_admitted"] is False
    assert report["proof_scope"]["host_fixed_step_substitution_allowed"] is False

    for key, targets in MODULE.SUBSETS.items():
        output = tmp_path / "out" / MODULE.OUTPUTS[key]
        rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
        assert [row["function"]["name"] for row in rows] == list(targets)


def test_missing_target_is_rejected(tmp_path):
    bundle = tmp_path / "bundle.jsonl"
    _write(bundle, MODULE.BUNDLE_TARGETS[:-1])
    with pytest.raises(ValueError, match="target mismatch"):
        MODULE.split(bundle, tmp_path / "out")


def test_extra_target_is_rejected(tmp_path):
    bundle = tmp_path / "bundle.jsonl"
    _write(bundle, (*MODULE.BUNDLE_TARGETS, "FUN_00400000"))
    with pytest.raises(ValueError, match="target mismatch"):
        MODULE.split(bundle, tmp_path / "out")


def test_duplicate_target_is_rejected(tmp_path):
    bundle = tmp_path / "bundle.jsonl"
    _write(bundle, (*MODULE.BUNDLE_TARGETS, MODULE.BUNDLE_TARGETS[0]))
    with pytest.raises(ValueError, match="duplicate function row"):
        MODULE.split(bundle, tmp_path / "out")


def test_runner_exports_union_once_and_reuses_exact_subsets():
    source = RUNNER.read_text(encoding="utf-8")

    assert source.count("run_shift_function_instructions.sh") == 1
    assert "split_s5_retail_instruction_bundle.py" in source
    assert "analyze_s5_scheduler_accumulator_slice.py" in source
    assert "analyze_s5_scheduler_accumulator_value_provenance.py" in source
    assert "analyze_s5_scheduler_push_producer.py" in source
    assert "analyze_s5_physics_manager_rate_accessor.py" in source
    assert "analyze_s5_bmanager_dispatch_slice.py" in source

    for target in MODULE.BUNDLE_TARGETS:
        assert source.count(target) == 1

    for retired in (
        "FUN_00647b70",
        "FUN_00647c60",
        "FUN_00647cf0",
        "FUN_00647da0",
        "FUN_0065bb50",
    ):
        assert retired not in source

    assert "shift_d3d9_capture" not in source.lower()
    assert "wine" not in source.lower()
    assert "original-game" not in source.lower()
    assert "does not execute the retail game" in source.lower()
