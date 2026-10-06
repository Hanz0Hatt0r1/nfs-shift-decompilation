from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools/ghidra/run_s5_scheduler_accumulator_slice.sh"


def test_runner_builds_value_provenance_without_expanding_target_set():
    source = RUNNER.read_text(encoding="utf-8")

    assert "analyze_s5_scheduler_accumulator_value_provenance.py" in source
    assert "s5_scheduler_accumulator_value_provenance.json" in source
    assert source.count("FUN_007155e9") == 1
    assert source.count("FUN_00715380") == 1
    assert source.count("FUN_00713050") == 1
    assert "shift_d3d9_capture" not in source.lower()
    assert "wine" not in source.lower()
    assert "runtime execution" in source.lower()
