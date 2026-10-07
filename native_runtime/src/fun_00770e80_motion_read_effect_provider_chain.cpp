#include "shift_fun_00770e80_motion_read_effect_provider_chain.hpp"

#include "shift_body_record_adapter.hpp"

#include <cmath>
#include <memory>
#include <stdexcept>
#include <utility>

namespace shift::runtime::physics {
namespace {

struct MotionReadPassState {
    std::size_t effect_provider_call_count = 0u;
    std::size_t delta_application_call_count = 0u;
    std::size_t delta_consumer_call_count = 0u;
    bool effect_present = false;
    Fun007682c0AccumulatorEffect effect{};
};

void require_complete_pass_callbacks(
    const Fun0076d100MotionReadEffectProviderCallbacks& callbacks) {
    if (!callbacks.contact_factor ||
        !callbacks.wheel_update ||
        !callbacks.contact_response ||
        !callbacks.contact_outer_input_provider ||
        !callbacks.motion_read_effect_provider) {
        throw std::invalid_argument(
            "FUN_00770e80 motion-read effect chain requires all active physics-pass providers");
    }
}

void validate_effect(const Fun007682c0AccumulatorEffect& effect) {
    if (!std::isfinite(effect.accumulator_y_delta)) {
        throw std::invalid_argument(
            "FUN_007682c0 typed effect contains non-finite accumulator delta");
    }
    if (!effect.gate_open && effect.accumulator_y_delta != 0.0) {
        throw std::invalid_argument(
            "FUN_007682c0 closed gate cannot carry accumulator delta");
    }
}

}  // namespace

Fun00770e80MotionReadEffectProviderChainResult
execute_fun_00770e80_motion_read_effect_provider_chain(
    double outer_timestep,
    const std::vector<std::uint8_t>& initial_body_bytes,
    const Fun0076d100MotionReadEffectProvider& physics_pass_provider,
    const Fun00765470MachineScalarHalfStepProvider& half_step_provider,
    const Fun007b8810PostHalfStepCallback& post_half_step) {
    if (!physics_pass_provider) {
        throw std::invalid_argument(
            "FUN_00770e80 motion-read effect chain requires physics-pass provider");
    }

    Fun00770e80MotionReadEffectProviderChainResult result{};
    std::array<std::shared_ptr<MotionReadPassState>, kFun00770e80PassCount> states{};

    result.joined = execute_fun_00770e80_contact_outer_provider_chain(
        outer_timestep,
        initial_body_bytes,
        [&](std::size_t pass_index) {
            if (pass_index >= kFun00770e80PassCount) {
                throw std::logic_error(
                    "FUN_00770e80 motion-read pass index exceeds proven domain");
            }
            if (states[pass_index]) {
                throw std::logic_error(
                    "FUN_00770e80 motion-read provider invoked twice for one pass");
            }

            auto typed = physics_pass_provider(pass_index);
            require_complete_pass_callbacks(typed);

            auto state = std::make_shared<MotionReadPassState>();
            states[pass_index] = state;

            Fun0076d100ContactOuterProviderCallbacks adapted{};
            adapted.contact_factor = std::move(typed.contact_factor);
            adapted.wheel_update = std::move(typed.wheel_update);
            adapted.contact_response = std::move(typed.contact_response);
            adapted.contact_outer_input_provider =
                std::move(typed.contact_outer_input_provider);

            auto effect_provider = std::move(typed.motion_read_effect_provider);
            auto delta_consumer = std::move(typed.motion_read_delta_consumer);
            adapted.motion_read_gate =
                [state, effect_provider = std::move(effect_provider)]() mutable {
                    ++state->effect_provider_call_count;
                    const Fun007682c0AccumulatorEffect effect = effect_provider();
                    validate_effect(effect);
                    state->effect = effect;
                    state->effect_present = true;
                };
            adapted.post_pass_body_mutator =
                [state, delta_consumer = std::move(delta_consumer)](
                    std::vector<std::uint8_t>& current_body_bytes) mutable {
                    if (!state->effect_present) {
                        throw std::logic_error(
                            "FUN_007682c0 BODY mutation executed before typed effect");
                    }
                    if (!state->effect.gate_open) {
                        return;
                    }

                    // PC retail source: receiver is HDVehicle, destination is
                    // *(HDVehicle+0x33a0)+0x50. The already-proven BMW identity
                    // join maps HDVehicle+0x33a0 to the chassis BODY/BODY0.
                    apply_fun_007682c0_body0_accumulator_y_delta(
                        current_body_bytes,
                        state->effect.accumulator_y_delta);
                    ++state->delta_application_call_count;

                    // Legacy observer only; correctness no longer depends on an
                    // external consumer applying the retail BODY write.
                    if (delta_consumer) {
                        delta_consumer(state->effect.accumulator_y_delta);
                        ++state->delta_consumer_call_count;
                    }
                };
            return adapted;
        },
        half_step_provider,
        post_half_step);

    for (std::size_t pass_index = 0u;
         pass_index < kFun00770e80PassCount;
         ++pass_index) {
        const auto& state = states[pass_index];
        if (!state ||
            state->effect_provider_call_count != 1u ||
            !state->effect_present) {
            throw std::logic_error(
                "FUN_007682c0 typed effect provider cardinality mismatch");
        }
        const std::size_t expected_applications =
            state->effect.gate_open ? 1u : 0u;
        if (state->delta_application_call_count != expected_applications) {
            throw std::logic_error(
                "FUN_007682c0 internal BODY0 delta application cardinality mismatch");
        }
        if (state->delta_consumer_call_count > expected_applications) {
            throw std::logic_error(
                "FUN_007682c0 compatibility observer cardinality mismatch");
        }

        result.motion_read_effects[pass_index] = state->effect;
        result.motion_read_effect_present[pass_index] = true;
        result.motion_read_effect_provider_call_counts[pass_index] =
            state->effect_provider_call_count;
        result.motion_read_delta_application_call_counts[pass_index] =
            state->delta_application_call_count;
        result.motion_read_delta_consumer_call_counts[pass_index] =
            state->delta_consumer_call_count;
        result.motion_read_effect_provider_call_count +=
            state->effect_provider_call_count;
        result.motion_read_delta_application_call_count +=
            state->delta_application_call_count;
        result.motion_read_delta_consumer_call_count +=
            state->delta_consumer_call_count;
        if (state->effect.gate_open) {
            ++result.motion_read_gate_open_count;
        }
    }

    return result;
}

}  // namespace shift::runtime::physics
