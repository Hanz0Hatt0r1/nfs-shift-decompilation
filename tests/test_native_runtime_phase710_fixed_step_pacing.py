from pathlib import Path


def test_phase710_continuous_loop_uses_existing_native_fixed_dt() -> None:
    policy = Path("native_runtime/src/runtime_loop_policy.hpp").read_text(
        encoding="utf-8"
    )
    runtime = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )

    assert "kNativeContinuousFixedDt = 1.0 / 60.0" in policy
    assert "constexpr double kFixedDt = 1.0 / 60.0;" in runtime
    assert "continuous_wall_clock_pacing" in policy
    assert "std::chrono::steady_clock" in policy
    assert "std::this_thread::sleep_until(next_tick)" in policy
    assert "next_tick += tick" in policy


def test_phase710_keeps_bounded_and_script_modes_unpaced() -> None:
    policy = Path("native_runtime/src/runtime_loop_policy.hpp").read_text(
        encoding="utf-8"
    )

    assert "--continuous cannot be combined with --input-script" in policy
    assert "return RuntimeLoopPolicy{false, true, script_frames};" in policy
    assert "policy.continuous_wall_clock_pacing = true" in policy
    assert "return RuntimeLoopPolicy{false, true, requested_frames};" in policy


def test_phase710_does_not_claim_retail_schedule() -> None:
    runtime = Path("native_runtime/src/shift_runtime.cpp").read_text(
        encoding="utf-8"
    )
    docs = Path("docs/PHASE710_NATIVE_FIXED_STEP_PACING.md").read_text(
        encoding="utf-8"
    )

    assert "one-native-fixed-step-per-render-frame-non-retail" in runtime
    assert "native-fixed-step-non-retail-timing" in runtime
    assert "native `fixed_step` equals retail outer update" in docs
    assert "implement_now = 0" in docs
