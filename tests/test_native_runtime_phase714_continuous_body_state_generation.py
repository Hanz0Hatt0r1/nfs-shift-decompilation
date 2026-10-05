from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_STATE = ROOT / "native_runtime" / "src" / "runtime_state.hpp"
BODY_FEEDBACK = ROOT / "native_runtime" / "src" / "runtime_body_feedback_scheduler.hpp"
CPP_REGRESSION = ROOT / "native_runtime" / "tests" / "runtime_body_feedback_scheduler_check.cpp"


def _scheduler_fixed_step(source: str) -> str:
    marker = "    void fixed_step() {"
    start = source.index(marker)
    end = source.index("\n    }\n};", start)
    return source[start:end]


def _runtime_fixed_step(source: str) -> str:
    marker = "    void fixed_step(const VehicleControlIntent& input) {"
    start = source.index(marker)
    end = source.index("\n    }\n};", start)
    return source[start:end]


def _runtime_boundary(source: str) -> str:
    marker = "    void validate_runtime_boundary("
    start = source.index(marker)
    end = source.index("\n    void fixed_step() {", start)
    return source[start:end]


def test_phase714_scheduler_commits_one_successor_generation_per_step():
    source = BODY_FEEDBACK.read_text(encoding="utf-8")
    body = _scheduler_fixed_step(source)

    assert "const std::uint64_t input_generation = body_state_generation;" in body
    call = body.index("physics::execute_body_state_feedback_step(")
    bodies_arg = body.index("\n            bodies);", call)
    commit = body.index("bodies = result.bodies;", bodies_arg)
    input_commit = body.index(
        "last_input_body_state_generation = input_generation;", commit
    )
    generation_commit = body.index(
        "body_state_generation = input_generation + 1u;", input_commit
    )
    step_commit = body.index("step_count = body_state_generation;", generation_commit)
    assert call < bodies_arg < commit < input_commit < generation_commit < step_commit


def test_phase714_stale_generation_is_rejected_at_pre_mutation_boundary():
    scheduler = BODY_FEEDBACK.read_text(encoding="utf-8")
    boundary = _runtime_boundary(scheduler)
    assert "body_state_generation != step_count" in boundary
    assert '"native BODY feedback persistent state generation is stale"' in boundary
    assert "bodies.size() != body_count" in boundary

    runtime = RUNTIME_STATE.read_text(encoding="utf-8")
    fixed = _runtime_fixed_step(runtime)
    validate = fixed.index("body_feedback.validate_runtime_boundary(")
    camera_snapshot = fixed.index("const CameraBufferRuntime camera_before = camera;")
    begin = fixed.index("begin_camera_update()")
    physics_tick = fixed.index("physics.tick(input)")
    feedback = fixed.index("body_feedback.fixed_step()")
    assert validate < camera_snapshot < begin < physics_tick < feedback


def test_phase714_configure_resets_lineage_to_admitted_seed_generation_zero():
    source = BODY_FEEDBACK.read_text(encoding="utf-8")
    start = source.index("    void configure(")
    end = source.index("\n    void initialize_from_environment() {", start)
    configure = source[start:end]

    assert "bodies = projection.bodies;" in configure
    assert "step_count = 0;" in configure
    assert "body_state_generation = 0;" in configure
    assert "last_input_body_state_generation = 0;" in configure


def test_phase714_cpp_regression_proves_second_tick_consumes_first_commit():
    source = CPP_REGRESSION.read_text(encoding="utf-8")

    assert "state.body_feedback.bodies[0].angular[0] += 9.0;" in source
    assert "const double admitted_seed" in source
    assert "const double first_committed" in source
    assert "state.body_feedback.bodies[0].angular[0] != first_committed" in source
    assert "state.body_feedback.last_input_body_state_generation != 1" in source
    assert "stale.body_feedback.body_state_generation = 1;" in source
    assert "stale.physics.fixed_step != 0" in source
    assert "stale.camera.snapshot_count != 0" in source
    assert '"continuous_body_state_lineage_ready\\":true' in source


def test_phase714_does_not_schedule_retail_outer_update_or_claim_pose_integration():
    runtime = RUNTIME_STATE.read_text(encoding="utf-8")
    fixed = _runtime_fixed_step(runtime)
    scheduler = BODY_FEEDBACK.read_text(encoding="utf-8")

    assert "execute_explicit_outer_update" not in fixed
    assert "outer_update.execute" not in fixed
    assert "body_feedback.fixed_step()" in fixed
    assert "PersistentBodyPoseSnapshot" not in scheduler
    assert "VehicleWorldMatrix" not in scheduler
