import copy
import json

import pytest

from tools import compare_runtime_telemetry as runtime


def _frame(step: int) -> dict:
    return {
        "format": runtime.TRACE_FORMAT,
        "step": step,
        "throttle": 0.75,
        "brake": 0.0,
        "steer": 0.1,
        "gear": 3,
        "position": [float(step), 0.25 * step, -0.1 * step],
        "speed": 20.0 + step,
        "orientation_degrees": [0.0, 5.0 * step, 0.0],
        "wheel_loads": [3200.0 + step, 3210.0 + step, 3000.0 + step, 3010.0 + step],
        "tire_temperatures": [82.0 + step, 83.0 + step, 80.0 + step, 81.0 + step],
    }


def _trace(count: int = 4) -> list[dict]:
    return [_frame(step) for step in range(count)]


def test_exact_runtime_telemetry_match_is_ready():
    retail = _trace()
    result = runtime.compare_traces(retail, copy.deepcopy(retail))

    assert result["format"] == "SHIFT.RuntimeTelemetryComparison/1"
    assert result["frame_count"] == 4
    assert result["controls_match"] is True
    assert result["blocking_reasons"] == []
    assert result["ready"] is True
    assert all(metric["normalized_rmse"] == 0.0 for metric in result["metrics"].values())
    assert result["policy"]["threshold_kind"] == "acceptance-policy-not-retail-evidence"


def test_small_state_drift_can_pass_configured_one_percent_policy():
    retail = _trace()
    native = copy.deepcopy(retail)
    for frame in native:
        frame["speed"] *= 1.005
        frame["wheel_loads"] = [value * 1.005 for value in frame["wheel_loads"]]
        frame["tire_temperatures"] = [value * 1.005 for value in frame["tire_temperatures"]]

    result = runtime.compare_traces(retail, native, max_normalized_rmse=0.01)

    assert result["ready"] is True
    assert 0.0 < result["metrics"]["speed"]["normalized_rmse"] < 0.01
    assert 0.0 < result["metrics"]["wheel_loads"]["normalized_rmse"] < 0.01


def test_state_drift_above_policy_fails_closed():
    retail = _trace()
    native = copy.deepcopy(retail)
    for frame in native:
        frame["speed"] *= 1.05

    result = runtime.compare_traces(retail, native, max_normalized_rmse=0.01)

    assert result["ready"] is False
    assert "telemetry:speed:normalized-rmse-exceeded" in result["blocking_reasons"]


def test_control_mismatch_blocks_equivalence_even_when_state_matches():
    retail = _trace()
    native = copy.deepcopy(retail)
    native[2]["steer"] = 0.2

    result = runtime.compare_traces(retail, native)

    assert result["ready"] is False
    assert result["controls_match"] is False
    assert result["control_mismatches"] == [{"step": 2, "fields": ["steer"]}]
    assert "telemetry:input-controls-mismatch" in result["blocking_reasons"]


def test_orientation_error_wraps_across_180_degrees():
    retail = _trace(1)
    native = copy.deepcopy(retail)
    retail[0]["orientation_degrees"] = [0.0, 179.0, 0.0]
    native[0]["orientation_degrees"] = [0.0, -179.0, 0.0]

    result = runtime.compare_traces(retail, native, max_normalized_rmse=0.02)

    # One axis differs by 2 degrees, the other two by zero. This must not be
    # interpreted as a 358-degree discontinuity.
    assert result["metrics"]["orientation_degrees"]["max_abs_error"] == pytest.approx(2.0)
    assert result["ready"] is True


def test_frame_count_mismatch_is_rejected_before_comparison():
    with pytest.raises(ValueError, match="frame count mismatch"):
        runtime.compare_traces(_trace(2), _trace(3))


def test_non_contiguous_steps_are_rejected():
    retail = _trace(2)
    native = copy.deepcopy(retail)
    native[1]["step"] = 3

    with pytest.raises(ValueError, match="contiguous from zero"):
        runtime.compare_traces(retail, native)


def test_non_finite_state_is_rejected():
    retail = _trace(1)
    native = copy.deepcopy(retail)
    native[0]["speed"] = float("nan")

    with pytest.raises(ValueError, match="speed must be finite"):
        runtime.compare_traces(retail, native)


def test_load_trace_reads_jsonl_and_comments(tmp_path):
    path = tmp_path / "retail.jsonl"
    frames = _trace(2)
    path.write_text(
        "# capture metadata can be commented\n"
        + "\n".join(json.dumps(frame) for frame in frames)
        + "\n",
        encoding="utf-8",
    )

    loaded = runtime.load_trace(path)

    assert loaded == frames


def test_cli_returns_two_for_policy_failure(tmp_path, capsys):
    retail = _trace(2)
    native = copy.deepcopy(retail)
    native[1]["speed"] *= 1.2
    retail_path = tmp_path / "retail.jsonl"
    native_path = tmp_path / "native.jsonl"
    output_path = tmp_path / "comparison.json"
    retail_path.write_text("\n".join(json.dumps(frame) for frame in retail) + "\n", encoding="utf-8")
    native_path.write_text("\n".join(json.dumps(frame) for frame in native) + "\n", encoding="utf-8")

    code = runtime.main([str(retail_path), str(native_path), "-o", str(output_path)])

    assert code == 2
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["ready"] is False
    assert "telemetry:speed:normalized-rmse-exceeded" in payload["blocking_reasons"]
    assert '"ready": false' in capsys.readouterr().out
