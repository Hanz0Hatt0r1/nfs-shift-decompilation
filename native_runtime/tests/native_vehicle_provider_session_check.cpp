#include "fun_00770e80_outer_update_fixture.hpp"
#include "runtime_loop_policy.hpp"
#include "shift_native_vehicle_provider_session.hpp"

#include <cmath>
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
    const Fun00763570MachineInput& machine_input,
    double expected_half_timestep) {
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
         &machine_input,
         expected_half_timestep](
            std::size_t pass,
            double half_timestep,
            const std::vector<std::uint8_t>&) {
            if (std::abs(half_timestep - expected_half_timestep) > 1e-15) {
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

RetailOuterSchedulerContract make_retail_scheduler() {
    return make_retail_outer_scheduler_contract(
        true,
        kRetailOuterNominalFrequencyHz,
        kRetailOuterGatePeriodMs,
        kRetailNormalOuterIncrementSeconds,
        kRetailSteadySchedulerInvocationsPerDispatch);
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
            machine_input,
            outer_timestep * 0.5);
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
            outer_timestep * 0.5));

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

        // Retail batch bridge: use an arbitrary explicit rate only as a
        // regression fixture. This is not the selected-session retail rate.
        constexpr double fixture_rate_hz = 60.0;
        constexpr double fixture_inner_dt = 1.0 / fixture_rate_hz;

        NativeRuntimeState retail_runtime{};
        configure_runtime(retail_runtime, initial_body_bytes);
        std::vector<std::string> retail_events;
        NativeVehicleProviderSession retail_session(make_bundle(
            retail_events,
            source,
            relations,
            reset_state,
            solver_topology,
            projection,
            machine_input,
            fixture_inner_dt * 0.5));
        auto retail_scheduler = make_retail_scheduler();

        bool missing_rate_rejected = false;
        try {
            (void)retail_session.execute_ready_retail_inner_batch(
                retail_runtime, retail_scheduler);
        } catch (const std::logic_error&) {
            missing_rate_rejected = true;
        }
        require(missing_rate_rejected && retail_events.empty() &&
                    retail_session.step_count() == 0u &&
                    retail_runtime.outer_update.explicit_update_count == 0u &&
                    retail_runtime.outer_update.body_bytes == initial_body_bytes,
                "retail batch bridge executed before loaded-rate admission");

        retail_scheduler.admit_loaded_inner_rate(fixture_rate_hz);
        retail_scheduler.admit_outer_dispatch();
        require(retail_scheduler.ready_inner_substep_count() == 2u,
                "retail batch bridge fixture count mismatch");

        const auto retail_batch =
            retail_session.execute_ready_retail_inner_batch(
                retail_runtime, retail_scheduler);
        require(retail_batch.recovered_substep_count == 2u &&
                    std::abs(retail_batch.inner_substep_seconds - fixture_inner_dt) < 1e-15 &&
                    retail_batch.session_step_count_before == 0u &&
                    retail_batch.session_step_count_after == 2u &&
                    retail_batch.explicit_update_count_before == 0u &&
                    retail_batch.explicit_update_count_after == 2u &&
                    retail_batch.scheduler_accumulator_committed,
                "retail batch bridge result mismatch");
        require(retail_session.step_count() == 2u &&
                    retail_runtime.outer_update.explicit_update_count == 2u &&
                    retail_runtime.outer_update.body_pose_snapshot_generation == 2u &&
                    retail_runtime.outer_update.body_bytes != initial_body_bytes,
                "retail batch bridge did not persist recovered BODY substeps");
        require(
            std::abs(
                retail_scheduler.pending_accumulator_seconds -
                (kRetailNormalOuterIncrementSeconds - 2.0 / fixture_rate_hz)) < 1e-15,
            "retail batch bridge did not commit recovered scheduler duration");

        // A deep provider rejection after one completed substep must restore
        // persistent BODY/session/scheduler state. Provider-side external
        // effects are intentionally not claimed reversible.
        NativeRuntimeState failing_runtime{};
        configure_runtime(failing_runtime, initial_body_bytes);
        std::vector<std::string> failing_events;
        auto failing_bundle = make_bundle(
            failing_events,
            source,
            relations,
            reset_state,
            solver_topology,
            projection,
            machine_input,
            fixture_inner_dt * 0.5);
        std::size_t failing_post_half_step_calls = 0u;
        failing_bundle.post_half_step =
            [&failing_events, &failing_post_half_step_calls](std::size_t pass) {
                failing_events.push_back("post-half:" + std::to_string(pass));
                ++failing_post_half_step_calls;
                if (failing_post_half_step_calls == 3u) {
                    throw std::runtime_error("intentional retail batch rejection");
                }
            };
        NativeVehicleProviderSession failing_session(std::move(failing_bundle));
        auto failing_scheduler = make_retail_scheduler();
        failing_scheduler.admit_loaded_inner_rate(fixture_rate_hz);
        failing_scheduler.admit_outer_dispatch();
        const double failing_accumulator_before =
            failing_scheduler.pending_accumulator_seconds;

        bool deep_batch_rejected = false;
        try {
            (void)failing_session.execute_ready_retail_inner_batch(
                failing_runtime, failing_scheduler);
        } catch (const std::runtime_error&) {
            deep_batch_rejected = true;
        }
        require(deep_batch_rejected && !failing_events.empty(),
                "retail batch bridge did not surface deep provider rejection");
        require(failing_session.step_count() == 0u &&
                    failing_runtime.outer_update.explicit_update_count == 0u &&
                    failing_runtime.outer_update.body_pose_snapshot_generation == 0u &&
                    failing_runtime.outer_update.body_bytes == initial_body_bytes,
                "retail batch bridge retained partial persistent BODY/session state");
        require(
            std::abs(
                failing_scheduler.pending_accumulator_seconds -
                failing_accumulator_before) < 1e-15 &&
                failing_scheduler.ready_inner_substep_count() == 2u,
            "retail batch bridge retained a scheduler commit after rejection");

        // Atomic retail outer-dispatch bridge. Missing-rate rejection must also
        // roll back the normal outer accumulator contribution, not merely avoid
        // BODY execution.
        NativeRuntimeState missing_dispatch_runtime{};
        configure_runtime(missing_dispatch_runtime, initial_body_bytes);
        std::vector<std::string> missing_dispatch_events;
        NativeVehicleProviderSession missing_dispatch_session(make_bundle(
            missing_dispatch_events,
            source,
            relations,
            reset_state,
            solver_topology,
            projection,
            machine_input,
            fixture_inner_dt * 0.5));
        auto missing_dispatch_scheduler = make_retail_scheduler();
        const double missing_dispatch_accumulator_before =
            missing_dispatch_scheduler.pending_accumulator_seconds;
        bool missing_dispatch_rate_rejected = false;
        try {
            (void)missing_dispatch_session.execute_retail_outer_dispatch(
                missing_dispatch_runtime, missing_dispatch_scheduler);
        } catch (const std::logic_error&) {
            missing_dispatch_rate_rejected = true;
        }
        require(
            missing_dispatch_rate_rejected &&
                missing_dispatch_events.empty() &&
                missing_dispatch_session.step_count() == 0u &&
                missing_dispatch_runtime.outer_update.explicit_update_count == 0u &&
                missing_dispatch_runtime.outer_update.body_bytes == initial_body_bytes &&
                std::abs(
                    missing_dispatch_scheduler.pending_accumulator_seconds -
                    missing_dispatch_accumulator_before) < 1e-15,
            "retail outer dispatch retained state after missing-rate rejection");

        // With an explicitly admitted fixture rate the wrapper owns the outer
        // accumulator contribution and then delegates the exact recovered batch.
        NativeRuntimeState dispatch_runtime{};
        configure_runtime(dispatch_runtime, initial_body_bytes);
        std::vector<std::string> dispatch_events;
        NativeVehicleProviderSession dispatch_session(make_bundle(
            dispatch_events,
            source,
            relations,
            reset_state,
            solver_topology,
            projection,
            machine_input,
            fixture_inner_dt * 0.5));
        auto dispatch_scheduler = make_retail_scheduler();
        dispatch_scheduler.admit_loaded_inner_rate(fixture_rate_hz);
        const auto dispatch_batch = dispatch_session.execute_retail_outer_dispatch(
            dispatch_runtime, dispatch_scheduler);
        require(
            dispatch_batch.recovered_substep_count == 2u &&
                std::abs(dispatch_batch.inner_substep_seconds - fixture_inner_dt) < 1e-15 &&
                dispatch_batch.session_step_count_before == 0u &&
                dispatch_batch.session_step_count_after == 2u &&
                dispatch_batch.explicit_update_count_before == 0u &&
                dispatch_batch.explicit_update_count_after == 2u &&
                dispatch_batch.scheduler_accumulator_committed &&
                dispatch_session.step_count() == 2u &&
                dispatch_runtime.outer_update.explicit_update_count == 2u &&
                dispatch_runtime.outer_update.body_pose_snapshot_generation == 2u &&
                dispatch_runtime.outer_update.body_bytes != initial_body_bytes &&
                std::abs(
                    dispatch_scheduler.pending_accumulator_seconds -
                    (kRetailNormalOuterIncrementSeconds -
                     2.0 / fixture_rate_hz)) < 1e-15,
            "retail outer dispatch did not execute/commit exact recovered batch");

        // A deep provider rejection through the wrapper restores the scheduler
        // to the state before the outer contribution was admitted.
        NativeRuntimeState failing_dispatch_runtime{};
        configure_runtime(failing_dispatch_runtime, initial_body_bytes);
        std::vector<std::string> failing_dispatch_events;
        auto failing_dispatch_bundle = make_bundle(
            failing_dispatch_events,
            source,
            relations,
            reset_state,
            solver_topology,
            projection,
            machine_input,
            fixture_inner_dt * 0.5);
        std::size_t failing_dispatch_post_half_step_calls = 0u;
        failing_dispatch_bundle.post_half_step =
            [&failing_dispatch_events,
             &failing_dispatch_post_half_step_calls](std::size_t pass) {
                failing_dispatch_events.push_back(
                    "post-half:" + std::to_string(pass));
                ++failing_dispatch_post_half_step_calls;
                if (failing_dispatch_post_half_step_calls == 3u) {
                    throw std::runtime_error(
                        "intentional retail outer dispatch rejection");
                }
            };
        NativeVehicleProviderSession failing_dispatch_session(
            std::move(failing_dispatch_bundle));
        auto failing_dispatch_scheduler = make_retail_scheduler();
        failing_dispatch_scheduler.admit_loaded_inner_rate(fixture_rate_hz);
        const double failing_dispatch_accumulator_before =
            failing_dispatch_scheduler.pending_accumulator_seconds;

        bool deep_dispatch_rejected = false;
        try {
            (void)failing_dispatch_session.execute_retail_outer_dispatch(
                failing_dispatch_runtime, failing_dispatch_scheduler);
        } catch (const std::runtime_error&) {
            deep_dispatch_rejected = true;
        }
        require(deep_dispatch_rejected && !failing_dispatch_events.empty(),
                "retail outer dispatch did not surface deep provider rejection");
        require(
            failing_dispatch_session.step_count() == 0u &&
                failing_dispatch_runtime.outer_update.explicit_update_count == 0u &&
                failing_dispatch_runtime.outer_update.body_pose_snapshot_generation == 0u &&
                failing_dispatch_runtime.outer_update.body_bytes == initial_body_bytes &&
                std::abs(
                    failing_dispatch_scheduler.pending_accumulator_seconds -
                    failing_dispatch_accumulator_before) < 1e-15,
            "retail outer dispatch retained partial scheduler/BODY/session state");

        std::cout
            << "{\"format\":\"" << kNativeVehicleProviderSessionFormat << "\","
            << "\"ready\":true,"
            << "\"phase697_persistent_outer_path_reused\":true,"
            << "\"phase699_external_provider_count\":9,"
            << "\"session_step_count\":" << session.step_count() << ","
            << "\"persistent_body_state_reused\":true,"
            << "\"provider_admission_before_execution\":true,"
            << "\"participant_gate_before_provider_side_effects\":true,"
            << "\"retail_inner_batch_bridge_ready\":true,"
            << "\"retail_inner_batch_uses_scheduler_dt\":true,"
            << "\"retail_inner_batch_internal_rollback\":true,"
            << "\"retail_outer_dispatch_transaction_ready\":true,"
            << "\"retail_outer_dispatch_full_rollback\":true,"
            << "\"selected_session_rate_promoted\":false,"
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
