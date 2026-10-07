#include "shift_native_vehicle_provider_session.hpp"

#include "runtime_loop_policy.hpp"
#include "runtime_motion_read_machine_input_state.hpp"
#include "runtime_state.hpp"
#include "shift_fun_007594e0_machine_angle.hpp"
#include "shift_fun_00765c40_selected_bmw_world_position.hpp"

#include <cmath>
#include <cstdint>
#include <cstring>
#include <memory>
#include <stdexcept>
#include <utility>

namespace shift::runtime {
namespace {

constexpr std::size_t kBody0VelocityX = 0x78u;
constexpr std::size_t kBody0VelocityZ = 0x88u;

struct Fun00765c40PassLoadState {
    physics::Fun00765c40LoadTerms terms{};
    bool ready = false;
};

struct Fun00765c40PassWorldPositionState {
    physics::CollisionQueryVector3d world_position{};
    physics::BodyAccumulatorVector3d primary_application_point{};
    bool selected_bmw_domain = false;
    bool ready = false;
};

struct Fun00766510PassInputState {
    physics::Fun00766510ExternalPassInput input{};
    bool ready = false;
};

void require_complete_bundle(
    const NativeVehicleExternalProviderBundle& providers) {
    if (!providers.fun_00765c40 ||
        !providers.wheel_update ||
        !providers.contact_response ||
        !providers.contact_outer_input ||
        !providers.scalar_provider_factory ||
        !providers.half_step_refresh ||
        !providers.post_half_step) {
        throw std::invalid_argument(
            "native vehicle provider session requires all seven active external provider boundaries");
    }
}

std::uint64_t read_u64_le(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset) {
    if (offset > bytes.size() || bytes.size() - offset < sizeof(std::uint64_t)) {
        throw std::runtime_error(
            "native vehicle provider session BODY0 velocity read out of range");
    }
    std::uint64_t value = 0u;
    for (std::size_t byte = 0u; byte < sizeof(value); ++byte) {
        value |= static_cast<std::uint64_t>(bytes[offset + byte]) << (byte * 8u);
    }
    return value;
}

double read_f64_le(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset) {
    const std::uint64_t bits = read_u64_le(bytes, offset);
    double value = 0.0;
    std::memcpy(&value, &bits, sizeof(value));
    if (!std::isfinite(value)) {
        throw std::runtime_error(
            "native vehicle provider session BODY0 velocity is non-finite");
    }
    return value;
}

}  // namespace

NativeVehicleProviderSession::NativeVehicleProviderSession(
    NativeVehicleExternalProviderBundle providers)
    : providers_(std::move(providers)) {
    require_complete_bundle(providers_);
    if (providers_.contact_outer_distance_setup.ready) {
        physics::validate_fun_007675f0_distance_state_setup(
            providers_.contact_outer_distance_setup);
        contact_outer_distance_state_ =
            providers_.contact_outer_distance_setup.previous_distance_state;
    }
    if (providers_.contact_outer_filter_cap_setup.ready) {
        physics::validate_fun_007675f0_distance_filter_cap_setup(
            providers_.contact_outer_filter_cap_setup);
    }
}

NativeVehicleProviderSessionResult
NativeVehicleProviderSession::execute_explicit_step(
    NativeRuntimeState& runtime,
    double outer_timestep) {
    require_complete_bundle(providers_);
    if (!std::isfinite(outer_timestep) || outer_timestep <= 0.0) {
        throw std::invalid_argument(
            "native vehicle provider session requires positive finite outer timestep");
    }

    runtime.outer_update.validate_runtime_boundary(
        runtime.physics.workspace.body_count,
        runtime.physics.workspace.ready,
        runtime.physics.participant_ready,
        runtime.physics.participant_identity_join_proven);

    const ExplicitOuterUpdateRuntimeState outer_update_before = runtime.outer_update;
    const auto distance_setup_before = providers_.contact_outer_distance_setup;
    const auto filter_cap_setup_before = providers_.contact_outer_filter_cap_setup;
    const double distance_state_before = contact_outer_distance_state_;
    const auto query_cache_before = fun_00765c40_query_cache_handle_;
    const double velocity_x_before =
        read_f64_le(outer_update_before.body_bytes, kBody0VelocityX);
    const double velocity_z_before =
        read_f64_le(outer_update_before.body_bytes, kBody0VelocityZ);

    const auto machine_angle = physics::execute_fun_007594e0_machine_angle(
        outer_update_before.body_bytes);
    const float steering = machine_angle.steering;

    NativeVehicleProviderSessionTelemetry telemetry{};
    std::array<physics::Fun00765c40QueryInputBoundary, kNativeVehiclePhysicsPassCount>
        query_inputs{};
    std::array<bool, kNativeVehiclePhysicsPassCount> query_input_present{};
    std::array<std::optional<std::uint64_t>, kNativeVehiclePhysicsPassCount>
        returned_cache_handles{};

    physics::Fun0076d100MotionReadMachineInputProvider pass_provider =
        [this,
         &telemetry,
         steering,
         &query_inputs,
         &query_input_present,
         &returned_cache_handles](std::size_t pass_index) {
            if (pass_index >= kNativeVehiclePhysicsPassCount) {
                throw std::logic_error(
                    "native vehicle provider session pass index exceeds recovered two-pass contract");
            }

            physics::Fun0076d100MotionReadMachineInputProviderCallbacks callbacks{};
            auto load_state = std::make_shared<Fun00765c40PassLoadState>();
            auto world_position_state =
                std::make_shared<Fun00765c40PassWorldPositionState>();
            auto contact_response_state =
                std::make_shared<Fun00766510PassInputState>();

            callbacks.current_body_observer =
                [world_position_state, contact_response_state](
                    const std::vector<std::uint8_t>& current_body_bytes) {
                    world_position_state->selected_bmw_domain =
                        physics::fun_00765c40_selected_bmw_body_domain(
                            current_body_bytes);
                    world_position_state->ready = false;
                    contact_response_state->ready = false;
                    contact_response_state->input = {};
                    if (!world_position_state->selected_bmw_domain) {
                        return;
                    }
                    const auto composed =
                        physics::execute_fun_00765c40_selected_bmw_world_position(
                            current_body_bytes);
                    world_position_state->world_position =
                        composed.world_transform.world_position;
                    world_position_state->primary_application_point =
                        physics::fun_00766510_selected_bmw_primary_application_point(
                            composed);
                    world_position_state->ready = true;
                };

            callbacks.contact_factor =
                [this,
                 &telemetry,
                 pass_index,
                 load_state,
                 world_position_state,
                 contact_response_state,
                 &query_inputs,
                 &query_input_present,
                 &returned_cache_handles] {
                    physics::Fun00765c40ExternalPassInput external_input{};
                    external_input.cached_handle = fun_00765c40_query_cache_handle_;
                    if (world_position_state->selected_bmw_domain) {
                        if (!world_position_state->ready) {
                            throw std::logic_error(
                                "FUN_00765c40 selected BMW provider invoked before world-position ownership bridge");
                        }
                        external_input.world_position =
                            world_position_state->world_position;
                    }

                    ++telemetry.fun_00765c40_call_count;
                    const auto result =
                        providers_.fun_00765c40(pass_index, external_input);
                    physics::validate_fun_00765c40_external_pass_result(
                        external_input,
                        result);

                    query_inputs[pass_index] = result.query_input;
                    query_input_present[pass_index] = true;
                    ++telemetry.fun_00765c40_query_input_capture_count;

                    // Retail FUN_00765c40 writes FUN_007b0710's returned pointer
                    // to HDVehicle+0x38dc immediately after the query. Commit it
                    // before any later pass anchor so pass 1 sees pass 0's value.
                    fun_00765c40_query_cache_handle_ =
                        result.returned_cache_handle;
                    returned_cache_handles[pass_index] =
                        result.returned_cache_handle;
                    ++telemetry.fun_00765c40_cache_commit_count;

                    // Phase745 prepares, but does not execute, the still-external
                    // FUN_00766510 remainder at the source-visible boundary.
                    contact_response_state->input = {};
                    if (world_position_state->selected_bmw_domain) {
                        if (!result.query_output.has_value()) {
                            throw std::logic_error(
                                "selected BMW FUN_00766510 handoff missing FUN_007b0710 output");
                        }
                        contact_response_state->input =
                            physics::build_fun_00766510_selected_bmw_external_pass_input(
                                result.query_input,
                                *result.query_output,
                                world_position_state->primary_application_point);
                    }
                    physics::validate_fun_00766510_external_pass_input(
                        contact_response_state->input);
                    contact_response_state->ready = true;

                    load_state->terms = result.load_terms;
                    load_state->ready = true;
                };
            callbacks.wheel_update = [this, &telemetry, pass_index] {
                ++telemetry.wheel_update_call_count;
                providers_.wheel_update(pass_index);
            };
            callbacks.contact_response =
                [this, &telemetry, pass_index, contact_response_state] {
                    if (!contact_response_state->ready) {
                        throw std::logic_error(
                            "FUN_00766510 residual provider invoked before typed Phase745 handoff");
                    }
                    physics::validate_fun_00766510_external_pass_input(
                        contact_response_state->input);
                    ++telemetry.contact_response_call_count;
                    providers_.contact_response(
                        pass_index,
                        contact_response_state->input);
                };
            callbacks.contact_outer_input_provider =
                [this, &telemetry, pass_index, load_state] {
                    if (!load_state->ready) {
                        throw std::logic_error(
                            "FUN_007675f0 param_3 requested before FUN_00765c40 load terms");
                    }
                    ++telemetry.contact_outer_input_call_count;
                    const auto session_input = providers_.contact_outer_input(pass_index);

                    if (!providers_.contact_outer_distance_setup.ready) {
                        if (!session_input.compatibility_previous_distance_seed_present) {
                            throw std::logic_error(
                                "FUN_007675f0 distance state used before explicit setup seed");
                        }
                        providers_.contact_outer_distance_setup.ready = true;
                        providers_.contact_outer_distance_setup.previous_distance_state =
                            session_input.compatibility_previous_distance_seed;
                        physics::validate_fun_007675f0_distance_state_setup(
                            providers_.contact_outer_distance_setup);
                        contact_outer_distance_state_ =
                            providers_.contact_outer_distance_setup.previous_distance_state;
                    }

                    if (!providers_.contact_outer_filter_cap_setup.ready) {
                        if (!session_input.compatibility_distance_filter_cap_seed_present) {
                            throw std::logic_error(
                                "FUN_007675f0 distance filter cap used before explicit setup seed");
                        }
                        providers_.contact_outer_filter_cap_setup.ready = true;
                        providers_.contact_outer_filter_cap_setup.distance_filter_cap =
                            session_input.compatibility_distance_filter_cap_seed;
                        physics::validate_fun_007675f0_distance_filter_cap_setup(
                            providers_.contact_outer_filter_cap_setup);
                    }

                    auto external = physics::compose_fun_007675f0_external_input(
                        session_input,
                        contact_outer_distance_state_,
                        providers_.contact_outer_filter_cap_setup.distance_filter_cap);
                    external.fun_00769ef0_param_3_load_terms = load_state->terms;
                    external.fun_00769ef0_param_3_load_terms_present = true;
                    return external;
                };
            callbacks.contact_outer_distance_state_commit =
                [this, &telemetry](double next_state) {
                    if (!std::isfinite(next_state)) {
                        throw std::invalid_argument(
                            "FUN_007675f0 distance state commit must be finite");
                    }
                    contact_outer_distance_state_ = next_state;
                    ++telemetry.contact_outer_distance_state_commit_count;
                };
            callbacks.motion_read_input_provider =
                [this, steering, load_state] {
                    if (!load_state->ready) {
                        throw std::logic_error(
                            "FUN_007682c0 machine input consumed before FUN_00765c40 load terms");
                    }
                    return physics::compose_fun_007682c0_machine_input(
                        providers_.motion_read_setup,
                        steering,
                        load_state->terms,
                        motion_read_projection_state_);
                };
            return callbacks;
        };

    physics::Fun00765470MachineScalarHalfStepProvider half_step_provider =
        [this, &telemetry](
            std::size_t pass_index,
            double half_timestep,
            const std::vector<std::uint8_t>& current_body_bytes) {
            ++telemetry.half_step_refresh_call_count;
            auto refresh = providers_.half_step_refresh(
                pass_index,
                half_timestep,
                current_body_bytes);

            ++telemetry.scalar_provider_factory_call_count;
            auto scalar_provider = providers_.scalar_provider_factory(pass_index);
            if (!scalar_provider) {
                throw std::invalid_argument(
                    "native vehicle provider session scalar provider factory returned an empty provider");
            }

            physics::Fun00765470MachineScalarHalfStepInput input{};
            input.machine = std::move(refresh.machine);
            input.source = std::move(refresh.source);
            input.relations = std::move(refresh.relations);
            input.reset_state = std::move(refresh.reset_state);
            input.solver_topology = std::move(refresh.solver_topology);
            input.projection = std::move(refresh.projection);
            input.scalar_provider = std::move(scalar_provider);
            input.tolerance = refresh.tolerance;
            return input;
        };

    physics::Fun007b8810PostHalfStepCallback post_half_step =
        [this, &telemetry](std::size_t pass_index) {
            ++telemetry.post_half_step_call_count;
            providers_.post_half_step(pass_index);
        };

    physics::Fun00770e80MotionReadMachineInputProviderChainResult joined{};
    try {
        joined = execute_explicit_motion_read_machine_input_update(
            runtime.outer_update,
            runtime.physics.workspace.body_count,
            runtime.physics.workspace.ready,
            runtime.physics.participant_ready,
            runtime.physics.participant_identity_join_proven,
            outer_timestep,
            pass_provider,
            half_step_provider,
            post_half_step);
    } catch (...) {
        providers_.contact_outer_distance_setup = distance_setup_before;
        providers_.contact_outer_filter_cap_setup = filter_cap_setup_before;
        contact_outer_distance_state_ = distance_state_before;
        fun_00765c40_query_cache_handle_ = query_cache_before;
        throw;
    }

    physics::Fun007682c0DerivedProjectionState next_projection{};
    try {
        const double velocity_x_after =
            read_f64_le(runtime.outer_update.body_bytes, kBody0VelocityX);
        const double velocity_z_after =
            read_f64_le(runtime.outer_update.body_bytes, kBody0VelocityZ);
        next_projection = physics::derive_fun_007682c0_projection_state(
            velocity_x_before,
            velocity_z_before,
            velocity_x_after,
            velocity_z_after,
            outer_timestep);
    } catch (...) {
        runtime.outer_update = outer_update_before;
        providers_.contact_outer_distance_setup = distance_setup_before;
        providers_.contact_outer_filter_cap_setup = filter_cap_setup_before;
        contact_outer_distance_state_ = distance_state_before;
        fun_00765c40_query_cache_handle_ = query_cache_before;
        throw;
    }

    telemetry.motion_read_native_effect_call_count =
        joined.motion_read_native_effect_call_count;
    telemetry.motion_read_delta_application_call_count =
        joined.motion_read_delta_application_call_count;

    motion_read_projection_state_ = next_projection;
    ++step_count_;
    last_telemetry_ = telemetry;

    NativeVehicleProviderSessionResult result{};
    result.joined = std::move(joined);
    result.fun_00765c40_query_inputs = query_inputs;
    result.fun_00765c40_query_input_present = query_input_present;
    result.fun_00765c40_returned_cache_handles = returned_cache_handles;
    result.session_step_count = step_count_;
    result.telemetry = last_telemetry_;
    return result;
}

NativeVehicleRetailInnerBatchResult
NativeVehicleProviderSession::execute_ready_retail_inner_batch(
    NativeRuntimeState& runtime,
    RetailOuterSchedulerContract& scheduler) {
    require_complete_bundle(providers_);

    const std::size_t recovered_substep_count =
        scheduler.ready_inner_substep_count();
    const double inner_substep_seconds = scheduler.inner_substep_seconds();

    NativeVehicleRetailInnerBatchResult result{};
    result.recovered_substep_count = recovered_substep_count;
    result.inner_substep_seconds = inner_substep_seconds;
    result.session_step_count_before = step_count_;
    result.explicit_update_count_before = runtime.outer_update.explicit_update_count;

    const RetailOuterSchedulerContract scheduler_before = scheduler;
    const ExplicitOuterUpdateRuntimeState outer_update_before = runtime.outer_update;
    const physics::Fun007682c0DerivedProjectionState projection_before =
        motion_read_projection_state_;
    const auto distance_setup_before = providers_.contact_outer_distance_setup;
    const auto filter_cap_setup_before = providers_.contact_outer_filter_cap_setup;
    const double distance_state_before = contact_outer_distance_state_;
    const auto query_cache_before = fun_00765c40_query_cache_handle_;
    const std::uint64_t step_count_before = step_count_;
    const NativeVehicleProviderSessionTelemetry telemetry_before = last_telemetry_;

    try {
        for (std::size_t index = 0u; index < recovered_substep_count; ++index) {
            (void)index;
            (void)execute_explicit_step(runtime, inner_substep_seconds);
        }
        scheduler.commit_ready_inner_substeps(recovered_substep_count);
    } catch (...) {
        scheduler = scheduler_before;
        runtime.outer_update = outer_update_before;
        motion_read_projection_state_ = projection_before;
        providers_.contact_outer_distance_setup = distance_setup_before;
        providers_.contact_outer_filter_cap_setup = filter_cap_setup_before;
        contact_outer_distance_state_ = distance_state_before;
        fun_00765c40_query_cache_handle_ = query_cache_before;
        step_count_ = step_count_before;
        last_telemetry_ = telemetry_before;
        throw;
    }

    result.session_step_count_after = step_count_;
    result.explicit_update_count_after = runtime.outer_update.explicit_update_count;
    result.scheduler_accumulator_committed = true;
    return result;
}

NativeVehicleRetailInnerBatchResult
NativeVehicleProviderSession::execute_retail_outer_dispatch(
    NativeRuntimeState& runtime,
    RetailOuterSchedulerContract& scheduler) {
    require_complete_bundle(providers_);

    const RetailOuterSchedulerContract scheduler_before_dispatch = scheduler;
    try {
        scheduler.admit_outer_dispatch();
        return execute_ready_retail_inner_batch(runtime, scheduler);
    } catch (...) {
        scheduler = scheduler_before_dispatch;
        throw;
    }
}

}  // namespace shift::runtime
