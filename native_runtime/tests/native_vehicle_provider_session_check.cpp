#include "fun_00770e80_outer_update_fixture.hpp"
#include "shift_native_vehicle_provider_session.hpp"

#include <cstddef>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
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

NativeVehicleExternalProviderBundle make_bundle(
    std::vector<std::string>& events,
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& reset_state,
    const PreparedBuiltinSolverFrame& solver_topology,
    const PreparedPostSolveBodyProjection& projection,
    const Fun00763570MachineInput& machine_input) {
    NativeVehicleExternalProviderBundle bundle{};
    bundle.contact_factor = [&events](std::size_t pass) {
        events.push_back("contact-factor:" + std::to_string(pass));
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
    bundle.motion_read_effect = [&events](std::size_t pass) {
        events.push_back("motion-effect:" + std::to_string(pass));
        return Fun007682c0AccumulatorEffect{true, -2.5};
    };
    bundle.motion_read_delta_consumer =
        [&events](std::size_t pass, double delta) {
            if (delta != -2.5) {
                throw std::runtime_error("Phase 701 motion delta mismatch");
            }
            events.push_back("motion-delta:" + std::to_string(pass));
        };
    bundle.scalar_provider_factory = [&events](std::size_t pass) {
        events.push_back("scalar-factory:" + std::to_string(pass));
        return [&events, pass](
            std::size_t body_index,
            const ConstraintRefreshFrame3f&,
            const BodyFrameIntegrationVector3d&) {
            if (body_index >= 2u) {
                throw std::runtime_error("Phase 701 scalar BODY index mismatch");
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
         &machine_input](
            std::size_t pass,
            double half_timestep,
            const std::vector<std::uint8_t>&) {
            if (half_timestep != 0.25) {
                throw std::runtime_error("Phase 701 half timestep mismatch");
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

}  // namespace

int main() {
    try {
        constexpr double outer_timestep = 0.5;
        const auto source = make_frame();
        const auto relations = make_relations();
        const auto projection = make_projection(source, relations);
        const auto solver_topology = make_solver_topology(source, relations);
        const auto reset_state = make_reset_state();
        const auto machine_input = make_machine_input();
        const auto initial_body_bytes = make_raw_bodies(projection.bodies);

        std::vector<std::string> constructor_events;
        auto incomplete = make_bundle(
            constructor_events,
            source,
            relations,
            reset_state,
            solver_topology,
            projection,
            machine_input);
        incomplete.contact_response = {};
        bool incomplete_rejected = false;
        try {
            NativeVehicleProviderSession bad(std::move(incomplete));
            (void)bad;
        } catch (const std::invalid_argument&) {
            incomplete_rejected = true;
        }
        require(incomplete_rejected && constructor_events.empty(),
                "Phase 701 incomplete bundle did not fail before side effects");

        NativeRuntimeState runtime{};
        runtime.physics.workspace.configure(2u, 1u, 1u);
        runtime.physics.participant_contract_ready = true;
        runtime.physics.participant_registry_ready = true;
        runtime.physics.selector_context_separate = true;
        runtime.physics.participant_ready = true;
        runtime.physics.participant_identity_join_proven = true;
        runtime.initialize_explicit_outer_update_body_state(initial_body_bytes);

        std::vector<std::string> events;
        NativeVehicleProviderSession session(make_bundle(
            events,
            source,
            relations,
            reset_state,
            solver_topology,
            projection,
            machine_input));

        const auto first = session.execute_explicit_step(runtime, outer_timestep);
        require(first.session_step_count == 1u && session.step_count() == 1u,
                "Phase 701 first session step count mismatch");
        require(runtime.outer_update.explicit_update_count == 1u,
                "Phase 701 first explicit update did not commit");
        require(first.telemetry.contact_factor_call_count == 2u &&
                first.telemetry.wheel_update_call_count == 2u &&
                first.telemetry.contact_response_call_count == 2u &&
                first.telemetry.contact_outer_input_call_count == 2u &&
                first.telemetry.motion_read_effect_call_count == 2u &&
                first.telemetry.motion_read_delta_consumer_call_count == 2u &&
                first.telemetry.scalar_provider_factory_call_count == 2u &&
                first.telemetry.half_step_refresh_call_count == 2u &&
                first.telemetry.post_half_step_call_count == 2u,
                "Phase 701 first nine-boundary telemetry mismatch");
        require(first.joined.joined.joined.scalar_provider_call_count == 4u &&
                first.joined.joined.contact_outer_native_call_count == 2u &&
                first.joined.motion_read_effect_provider_call_count == 2u,
                "Phase 701 nested Phase 697 telemetry mismatch");

        const auto first_body_bytes = runtime.outer_update.body_bytes;
        require(first_body_bytes != initial_body_bytes,
                "Phase 701 first step did not change persistent BODY bytes");

        events.clear();
        const auto second = session.execute_explicit_step(runtime, outer_timestep);
        require(second.session_step_count == 2u && session.step_count() == 2u,
                "Phase 701 second session step count mismatch");
        require(runtime.outer_update.explicit_update_count == 2u &&
                runtime.outer_update.body_pose_snapshot_generation == 2u,
                "Phase 701 second persistent update did not commit");
        require(runtime.outer_update.body_bytes != first_body_bytes,
                "Phase 701 second step did not reuse/evolve persistent BODY state");
        require(second.telemetry.contact_factor_call_count == 2u &&
                second.telemetry.scalar_provider_factory_call_count == 2u &&
                second.telemetry.half_step_refresh_call_count == 2u &&
                second.telemetry.post_half_step_call_count == 2u,
                "Phase 701 second telemetry mismatch");

        const auto committed_body_bytes = runtime.outer_update.body_bytes;
        const auto committed_generation =
            runtime.outer_update.body_pose_snapshot_generation;
        const auto committed_session_telemetry = session.last_telemetry();
        runtime.physics.participant_ready = false;
        events.clear();
        bool participant_rejected = false;
        try {
            (void)session.execute_explicit_step(runtime, outer_timestep);
        } catch (const std::runtime_error&) {
            participant_rejected = true;
        }
        runtime.physics.participant_ready = true;
        require(participant_rejected && events.empty(),
                "Phase 701 participant gate allowed provider side effects");
        require(session.step_count() == 2u &&
                runtime.outer_update.explicit_update_count == 2u &&
                runtime.outer_update.body_pose_snapshot_generation == committed_generation &&
                runtime.outer_update.body_bytes == committed_body_bytes &&
                session.last_telemetry().half_step_refresh_call_count ==
                    committed_session_telemetry.half_step_refresh_call_count,
                "Phase 701 failed step committed session/runtime state");

        require(runtime.physics.fixed_step == 0u,
                "Phase 701 leaked deep outer update into fixed_step scheduling");

        std::cout
            << "{\"format\":\"" << kNativeVehicleProviderSessionFormat << "\","
            << "\"ready\":true,"
            << "\"phase697_persistent_outer_path_reused\":true,"
            << "\"phase699_external_provider_count\":9,"
            << "\"session_step_count\":" << session.step_count() << ","
            << "\"persistent_body_state_reused\":true,"
            << "\"provider_admission_before_execution\":true,"
            << "\"participant_gate_before_provider_side_effects\":true,"
            << "\"provider_semantics_promoted\":false,"
            << "\"vehicle_body_identity_proven\":false,"
            << "\"vehicle_world_transform_proven\":false,"
            << "\"fixed_step_auto_schedule\":false,"
            << "\"deep_outer_update_executable_schedule_enabled\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
