#include "shift_native_vehicle_provider_session.hpp"

#include "runtime_loop_policy.hpp"
#include "runtime_state.hpp"

#include <stdexcept>
#include <utility>

namespace shift::runtime {
namespace {

void require_complete_bundle(
    const NativeVehicleExternalProviderBundle& providers) {
    if (!providers.contact_factor ||
        !providers.wheel_update ||
        !providers.contact_response ||
        !providers.contact_outer_input ||
        !providers.motion_read_effect ||
        !providers.motion_read_delta_consumer ||
        !providers.scalar_provider_factory ||
        !providers.half_step_refresh ||
        !providers.post_half_step) {
        throw std::invalid_argument(
            "native vehicle provider session requires all nine Phase 699 provider boundaries");
    }
}

}  // namespace

NativeVehicleProviderSession::NativeVehicleProviderSession(
    NativeVehicleExternalProviderBundle providers)
    : providers_(std::move(providers)) {
    require_complete_bundle(providers_);
}

NativeVehicleProviderSessionResult
NativeVehicleProviderSession::execute_explicit_step(
    NativeRuntimeState& runtime,
    double outer_timestep) {
    require_complete_bundle(providers_);

    NativeVehicleProviderSessionTelemetry telemetry{};

    physics::Fun0076d100MotionReadEffectProvider pass_provider =
        [this, &telemetry](std::size_t pass_index) {
            physics::Fun0076d100MotionReadEffectProviderCallbacks callbacks{};
            callbacks.contact_factor = [this, &telemetry, pass_index] {
                ++telemetry.contact_factor_call_count;
                providers_.contact_factor(pass_index);
            };
            callbacks.wheel_update = [this, &telemetry, pass_index] {
                ++telemetry.wheel_update_call_count;
                providers_.wheel_update(pass_index);
            };
            callbacks.contact_response = [this, &telemetry, pass_index] {
                ++telemetry.contact_response_call_count;
                providers_.contact_response(pass_index);
            };
            callbacks.contact_outer_input_provider =
                [this, &telemetry, pass_index] {
                    ++telemetry.contact_outer_input_call_count;
                    return providers_.contact_outer_input(pass_index);
                };
            callbacks.motion_read_effect_provider =
                [this, &telemetry, pass_index] {
                    ++telemetry.motion_read_effect_call_count;
                    return providers_.motion_read_effect(pass_index);
                };
            callbacks.motion_read_delta_consumer =
                [this, &telemetry, pass_index](double delta) {
                    ++telemetry.motion_read_delta_consumer_call_count;
                    providers_.motion_read_delta_consumer(pass_index, delta);
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

    auto joined =
        runtime.execute_explicit_outer_update_with_fun_007682c0_motion_read_effect_provider(
            outer_timestep,
            pass_provider,
            half_step_provider,
            post_half_step);

    ++step_count_;
    last_telemetry_ = telemetry;

    NativeVehicleProviderSessionResult result{};
    result.joined = std::move(joined);
    result.session_step_count = step_count_;
    result.telemetry = last_telemetry_;
    return result;
}

NativeVehicleRetailInnerBatchResult
NativeVehicleProviderSession::execute_ready_retail_inner_batch(
    NativeRuntimeState& runtime,
    RetailOuterSchedulerContract& scheduler) {
    require_complete_bundle(providers_);

    // Both calls fail closed until the selected-session PhysicsTweaker rate has
    // been admitted. No constructor/default rate or host 1/60 fallback exists
    // on this path.
    const std::size_t recovered_substep_count =
        scheduler.ready_inner_substep_count();
    const double inner_substep_seconds = scheduler.inner_substep_seconds();

    NativeVehicleRetailInnerBatchResult result{};
    result.recovered_substep_count = recovered_substep_count;
    result.inner_substep_seconds = inner_substep_seconds;
    result.session_step_count_before = step_count_;
    result.explicit_update_count_before = runtime.outer_update.explicit_update_count;

    // Keep persistent BODY/session/scheduler state coherent if any deep provider
    // rejects during the recovered batch. External provider side effects are not
    // reversible; a throwing provider still aborts the batch and no scheduler
    // accumulator commit is retained.
    const RetailOuterSchedulerContract scheduler_before = scheduler;
    const ExplicitOuterUpdateRuntimeState outer_update_before = runtime.outer_update;
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
        step_count_ = step_count_before;
        last_telemetry_ = telemetry_before;
        throw;
    }

    result.session_step_count_after = step_count_;
    result.explicit_update_count_after = runtime.outer_update.explicit_update_count;
    result.scheduler_accumulator_committed = true;
    return result;
}

}  // namespace shift::runtime
