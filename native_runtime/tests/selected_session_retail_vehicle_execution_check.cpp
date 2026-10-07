#include "fun_00770e80_outer_update_fixture.hpp"
#include "runtime_state.hpp"
#include "selected_session_retail_vehicle_execution.hpp"

#include <cmath>
#include <cstddef>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using namespace shift::runtime;
using namespace shift::runtime::physics;
using namespace shift::runtime::test_fixture;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

Fun00765c40QueryInputBoundary make_query_input(std::size_t pass) {
    Fun00765c40QueryInputBoundary input{};
    input.world_position = {
        100.0 + static_cast<double>(pass),
        200.0 + static_cast<double>(pass),
        300.0 + static_cast<double>(pass)};
    input.cached_handle = 4000u + static_cast<std::uint64_t>(pass);
    input.miss_fallback = 9.0 + static_cast<double>(pass);
    return input;
}

NativeVehicleExternalProviderBundle make_bundle(
    std::vector<std::string>& events,
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& reset_state,
    const PreparedBuiltinSolverFrame& solver_topology,
    const PreparedPostSolveBodyProjection& projection,
    const Fun00763570MachineInput& machine_input,
    double expected_half_timestep) {
    NativeVehicleExternalProviderBundle bundle{};
    bundle.fun_00765c40 = [&events](std::size_t pass) {
        events.push_back("fun-00765c40:" + std::to_string(pass));
        return Fun00765c40ExternalPassResult{
            Fun00765c40LoadTerms{3000.0, 3000.0, 3000.0, 3000.0},
            make_query_input(pass)};
    };
    bundle.wheel_update = [&events](std::size_t pass) {
        events.push_back("wheel-update:" + std::to_string(pass));
    };
    bundle.contact_response = [&events](std::size_t pass) {
        events.push_back("contact-response:" + std::to_string(pass));
    };
    bundle.contact_outer_input = [&events](std::size_t pass) {
        events.push_back("contact-input:" + std::to_string(pass));
        return make_contact_outer_input();
    };
    bundle.motion_read_setup.caller_gate_open = true;
    bundle.scalar_provider_factory = [&events](std::size_t pass) {
        events.push_back("scalar-factory:" + std::to_string(pass));
        return [&events, pass](
            std::size_t body_index,
            const ConstraintRefreshFrame3f&,
            const BodyFrameIntegrationVector3d&) {
            if (body_index >= 2u) {
                throw std::runtime_error("selected-session scalar BODY index mismatch");
            }
            events.push_back(
                "scalar:" + std::to_string(pass) + ":" +
                std::to_string(body_index));
            Fun007afdd0ScalarBoundary scalars{};
            scalars.squared_magnitude_test = 0.0f;
            scalars.sqrt_magnitude = 0.0f;
            scalars.sine = 0.0f;
            scalars.cosine = 1.0f;
            return scalars;
        };
    };
    bundle.half_step_refresh =
        [&events,
         &source,
         &relations,
         &reset_state,
         &solver_topology,
         &projection,
         &machine_input,
         expected_half_timestep](
            std::size_t pass,
            double half_timestep,
            const std::vector<std::uint8_t>&) {
            if (std::abs(half_timestep - expected_half_timestep) > 1e-15) {
                throw std::runtime_error(
                    "selected-session half timestep mismatch");
            }
            events.push_back("half-refresh:" + std::to_string(pass));
            NativeVehicleHalfStepRefreshInput input{};
            input.machine = machine_input;
            input.source = source;
            input.relations = relations;
            input.reset_state = reset_state;
            input.solver_topology = solver_topology;
            input.projection = projection;
            return input;
        };
    bundle.post_half_step = [&events](std::size_t pass) {
        events.push_back("post-half:" + std::to_string(pass));
    };
    return bundle;
}

void configure_runtime(
    NativeRuntimeState& runtime,
    const std::vector<std::uint8_t>& initial_body_bytes) {
    runtime.physics.workspace.configure(2u, 1u, 1u);
    runtime.physics.participant_contract_ready = true;
    runtime.physics.participant_registry_ready = true;
    runtime.physics.selector_context_separate = true;
    runtime.physics.participant_ready = true;
    runtime.physics.participant_identity_join_proven = true;
    runtime.initialize_explicit_outer_update_body_state(initial_body_bytes);
}

}  // namespace

int main() {
    try {
        const auto source = make_frame();
        const auto relations = make_relations();
        const auto projection = make_projection(source, relations);
        const auto solver_topology = make_solver_topology(source, relations);
        const auto reset_state = make_reset_state();
        const auto machine_input = make_machine_input();
        auto initial_body_bytes = make_raw_bodies(projection.bodies);
        put_f64(initial_body_bytes, 0x120u, 1000.0);

        SelectedSessionRetailVehicleExecution execution{};
        require(execution.scheduler().uses_admitted_retail_outer_scheduler(),
                "selected-session execution did not own RetailEvidence scheduler");
        require(execution.scheduler().inner_rate_ready(),
                "selected-session execution did not admit materialized inner rate");
        require(execution.scheduler().loaded_inner_rate_hz == 180.0,
                "selected-session execution rate drift");
        require(
            std::abs(execution.scheduler().inner_substep_seconds() - (1.0 / 180.0)) < 1e-15,
            "selected-session execution reciprocal drift");
        require(execution.scheduler().pending_accumulator_seconds == 0.0,
                "selected-session scheduler did not start with an empty accumulator");
        require(selected_bmw_native_session_player_difficulty() == 1,
                "selected-session Player Difficulty drift");

        NativeRuntimeState runtime{};
        configure_runtime(runtime, initial_body_bytes);
        std::vector<std::string> events;
        NativeVehicleProviderSession session(make_bundle(
            events,
            source,
            relations,
            reset_state,
            solver_topology,
            projection,
            machine_input,
            (1.0 / 180.0) * 0.5));

        const auto first = execution.execute_outer_dispatch(session, runtime);
        require(first.recovered_substep_count == 6u,
                "selected-session first retail dispatch did not recover six substeps");
        require(std::abs(first.inner_substep_seconds - (1.0 / 180.0)) < 1e-15,
                "selected-session first retail dispatch used wrong inner dt");
        require(first.session_step_count_before == 0u &&
                    first.session_step_count_after == 6u &&
                    first.explicit_update_count_before == 0u &&
                    first.explicit_update_count_after == 6u &&
                    first.scheduler_accumulator_committed,
                "selected-session first retail dispatch did not commit six persistent BODY steps");
        require(session.step_count() == 6u &&
                    runtime.outer_update.explicit_update_count == 6u &&
                    runtime.outer_update.body_pose_snapshot_generation == 6u &&
                    runtime.outer_update.body_bytes != initial_body_bytes,
                "selected-session first retail dispatch did not persist BODY state");
        require(session.last_telemetry().motion_read_native_effect_call_count == 2u,
                "selected-session active motion-read telemetry mismatch");
        require(session.last_telemetry().fun_00765c40_call_count == 2u &&
                    session.last_telemetry().fun_00765c40_query_input_capture_count == 2u,
                "selected-session FUN_00765c40 query-input telemetry mismatch");
        require(first.recovered_substep_count > 0u,
                "selected-session load-term path was not exercised");

        const double expected_first_residual =
            kRetailNormalOuterIncrementSeconds - 6.0 / 180.0;
        require(
            std::abs(
                execution.scheduler().pending_accumulator_seconds -
                expected_first_residual) < 1e-15,
            "selected-session first dispatch accumulator residual mismatch");

        const auto first_body_bytes = runtime.outer_update.body_bytes;
        events.clear();
        const auto second = execution.execute_outer_dispatch(session, runtime);
        require(second.recovered_substep_count == 6u &&
                    second.session_step_count_before == 6u &&
                    second.session_step_count_after == 12u &&
                    second.explicit_update_count_before == 6u &&
                    second.explicit_update_count_after == 12u,
                "selected-session second retail dispatch did not preserve scheduler/session continuity");
        require(session.step_count() == 12u &&
                    runtime.outer_update.explicit_update_count == 12u &&
                    runtime.outer_update.body_pose_snapshot_generation == 12u &&
                    runtime.outer_update.body_bytes != first_body_bytes,
                "selected-session second retail dispatch did not evolve persistent BODY state");
        require(session.last_telemetry().fun_00765c40_query_input_capture_count == 2u,
                "selected-session second dispatch lost per-step query snapshots");

        const double expected_second_residual =
            2.0 * kRetailNormalOuterIncrementSeconds - 12.0 / 180.0;
        require(
            std::abs(
                execution.scheduler().pending_accumulator_seconds -
                expected_second_residual) < 1e-15,
            "selected-session second dispatch accumulator residual mismatch");

        std::cout
            << "{\"format\":\"" << kSelectedSessionRetailVehicleExecutionFormat << "\","
            << "\"ready\":true,"
            << "\"selected_session_rate_hz\":180,"
            << "\"selected_player_difficulty\":"
            << kBmwNativeSilverstonePlayerDifficulty << ","
            << "\"inner_substep_seconds\":" << (1.0 / 180.0) << ","
            << "\"normal_outer_substeps\":6,"
            << "\"two_dispatch_persistent_steps\":12,"
            << "\"fun_007560c0_gate_setup_owned\":true,"
            << "\"fun_00765c40_load_terms_typed\":true,"
            << "\"fun_00765c40_external_pass_result_typed\":true,"
            << "\"fun_00765c40_query_input_captured\":true,"
            << "\"fun_00765c40_world_position_producer_internalized\":false,"
            << "\"fun_00765c40_collision_provider_internalized\":false,"
            << "\"motion_read_raw_input_provider\":false,"
            << "\"motion_read_effect_arithmetic_internal\":true,"
            << "\"retail_inner_substep_execution_admitted\":true,"
            << "\"provider_semantics_promoted\":false,"
            << "\"render_frame_equivalence_claimed\":false,"
            << "\"host_1_60_used_as_retail_timing\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
