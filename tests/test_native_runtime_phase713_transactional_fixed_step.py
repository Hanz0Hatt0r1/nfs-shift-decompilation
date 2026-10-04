from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_STATE = ROOT / "native_runtime" / "src" / "runtime_state.hpp"
BODY_FEEDBACK = ROOT / "native_runtime" / "src" / "runtime_body_feedback_scheduler.hpp"
CPP_REGRESSION = ROOT / "native_runtime" / "tests" / "runtime_body_feedback_scheduler_check.cpp"


def _fixed_step_body(source: str) -> str:
    marker = "    void fixed_step(const VehicleControlIntent& input) {"
    start = source.index(marker)
    end = source.index("\n    }\n};", start)
    return source[start:end]


def _environment_initializer_body(source: str) -> str:
    marker = "    void initialize_from_environment() {"
    start = source.index(marker)
    end = source.index("\n    void validate_runtime_boundary(", start)
    return source[start:end]


def test_phase713_fixed_step_rolls_back_camera_and_physics_on_failure():
    source = RUNTIME_STATE.read_text(encoding="utf-8")
    body = _fixed_step_body(source)

    assert "const CameraBufferRuntime camera_before = camera;" in body
    assert "const PhysicsTickBoundary physics_before = physics;" in body
    assert "catch (...)" in body
    assert "camera = camera_before;" in body
    assert "physics = physics_before;" in body
    assert "throw;" in body

    begin = body.index("begin_camera_update()")
    physics_tick = body.index("physics.tick(input)")
    feedback = body.index("body_feedback.fixed_step()")
    complete = body.index("complete_camera_update()")
    assert begin < physics_tick < feedback < complete


def test_phase713_preserves_explicit_outer_update_scheduling_boundary():
    source = RUNTIME_STATE.read_text(encoding="utf-8")
    body = _fixed_step_body(source)

    assert "execute_explicit_outer_update" not in body
    assert "outer_update.execute" not in body
    assert "physics.tick(input)" in body
    assert "body_feedback.fixed_step()" in body


def test_phase713_failed_environment_admission_remains_retryable():
    source = BODY_FEEDBACK.read_text(encoding="utf-8")
    body = _environment_initializer_body(source)

    raw_enabled = body.index(
        'const char* raw_enabled = std::getenv("SHIFT_NATIVE_BODY_FEEDBACK")'
    )
    disabled_commit = body.index("environment_checked = true;", raw_enabled)
    first_required_path = body.index("required_environment_path(")
    configure = body.index("configure(")

    # Only the explicit disabled path may latch the environment check before
    # source loading. Enabled admission must stay retryable until configure().
    assert raw_enabled < disabled_commit < first_required_path < configure
    prefix = body[:raw_enabled]
    assert "environment_checked = true;" not in prefix
    assert 'std::string(raw_enabled) == "0"' in body

    configure_source = source[source.index("    void configure(") : source.index(
        "    void initialize_from_environment() {"
    )]
    assert "environment_checked = true;" in configure_source
    assert "enabled = true;" in configure_source


def test_phase713_cpp_regression_exercises_post_tick_failure_and_retry_safety():
    source = CPP_REGRESSION.read_text(encoding="utf-8")

    assert "transactional.body_feedback.solver_topology.matrix.clear();" in source
    assert "transactional.physics.fixed_step != 0" in source
    assert "transactional.physics.throttle_steps != 0" in source
    assert "transactional.camera.snapshot_count != 0" in source
    assert "transactional.camera.native_update_count != 0" in source
    assert "retryable.body_feedback.environment_checked" in source
    assert '"transactional_fixed_step\\":true' in source
    assert '"environment_retry_safe\\":true' in source
